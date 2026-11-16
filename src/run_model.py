"""Ask one model about every row of a manifest and append its answers to a JSONL file.

Each image is read from --images-root joined with the manifest's path column. Rows whose
(image_id, cell, setting, defence) is already in the output file are skipped, so a run
that was stopped carries on where it stopped.

Usage:
    python src/run_model.py --model qwen3-vl-4b --manifest manifests/pilot.csv \\
        --images-root /kaggle/input/pixelguard-images --out runs/pilot_qwen3-vl-4b.jsonl

With --questions (a CSV with image_id and question, such as data/textvqa_set.csv) each row is asked
its own question, written into --question-prompt, instead of the shared prompt. B8 uses this for
TextVQA. The prompt template is part of the config hash, so these runs get their own hash.
"""
import argparse
import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from PIL import Image

KEY = ("image_id", "cell", "setting", "defence")
QUESTION_PROMPT = "{question}\nAnswer the question using a single word or phrase."
NESTED_IMAGES = {"smolvlm2-2b"}


def load_config(path: Path, name: str) -> tuple:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    spec = next((m for m in config["models"] if m["name"] == name), None)
    if spec is None:
        raise SystemExit(f"unknown model {name}, choose one of {[m['name'] for m in config['models']]}")
    return config, spec


def run_config(config: dict, spec: dict, seed: int) -> dict:
    return {"model": spec["name"], "repo_id": spec["repo_id"], "revision": spec["revision"],
            "dtype": spec["dtype"], "quantisation": spec["quantisation"], "prompt": config["prompt"],
            "max_new_tokens": config["max_new_tokens"], "decoding": config["decoding"], "seed": seed}


def config_hash(cfg: dict) -> str:
    return hashlib.md5(json.dumps(cfg, sort_keys=True).encode("utf-8")).hexdigest()


def read_manifest(path: Path) -> list:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def row_key(row: dict) -> tuple:
    return tuple(str(row[k]) for k in KEY)


def repair_tail(out: Path) -> None:
    if not out.exists():
        return
    data = out.read_bytes()
    if data and not data.endswith(b"\n"):
        out.write_bytes(data[:data.rfind(b"\n") + 1])


def done_keys(out: Path) -> set:
    if not out.exists():
        return set()
    with open(out, encoding="utf-8") as f:
        return {row_key(json.loads(line)) for line in f if line.strip()}


def load_model(spec: dict):
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

    kwargs = {"revision": spec["revision"], "device_map": "cuda:0"}
    if spec["quantisation"] == "4bit-nf4":
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
    else:
        kwargs["dtype"] = getattr(torch, spec["dtype"])
    processor = AutoProcessor.from_pretrained(spec["repo_id"], revision=spec["revision"])
    if hasattr(processor, "tokenizer"):
        processor.tokenizer.padding_side = "left"
    model = AutoModelForImageTextToText.from_pretrained(spec["repo_id"], **kwargs).eval()
    return processor, model


def read_questions(path: Path) -> dict:
    with open(path, encoding="utf-8", newline="") as f:
        return {str(r["image_id"]): r["question"] for r in csv.DictReader(f)}


def make_ask(processor, model, prompt: str, max_new_tokens: int, nested: bool):
    import torch

    def chat(p: str) -> str:
        message = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": p}]}]
        return processor.apply_chat_template(message, add_generation_prompt=True, tokenize=False)

    text = chat(prompt)

    def ask(images: list, prompts: list = None) -> list:
        texts = [text] * len(images) if prompts is None else [chat(p) for p in prompts]
        inputs = processor(text=texts, images=[[im] for im in images] if nested else images,
                           return_tensors="pt", padding=True).to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        new_tokens = out[:, inputs["input_ids"].shape[1]:]
        return [t.strip() for t in processor.batch_decode(new_tokens, skip_special_tokens=True)]

    return ask


def run(rows: list, ask, out: Path, images_root: Path, meta: dict, batch_size: int = 8, log=print,
        questions: dict = None) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    repair_tail(out)
    done = done_keys(out)
    todo = [r for r in rows if row_key(r) not in done]
    log(f"{len(rows)} rows in the manifest, {len(rows) - len(todo)} already in {out.name}, {len(todo)} to run")
    start, written = time.time(), 0
    with open(out, "a", encoding="utf-8", newline="\n") as f:
        for i in range(0, len(todo), batch_size):
            batch = todo[i:i + batch_size]
            images = [Image.open(Path(images_root) / r["path"]).convert("RGB") for r in batch]
            prompts = None if questions is None else [
                meta["prompt"].format(question=questions[str(r["image_id"])]) for r in batch]
            try:
                answers = ask(images) if prompts is None else ask(images, prompts)
            except Exception as error:
                log(f"batch of {len(images)} failed ({type(error).__name__}), running one at a time")
                answers = ([ask([im])[0] for im in images] if prompts is None
                           else [ask([im], [p])[0] for im, p in zip(images, prompts)])
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            for k, (r, answer) in enumerate(zip(batch, answers)):
                f.write(json.dumps({
                    "image_id": int(r["image_id"]), "cell": r["cell"], "setting": r["setting"],
                    "defence": r["defence"], "model": meta["model"], "revision": meta["revision"],
                    "prompt": meta["prompt"] if prompts is None else prompts[k], "output": answer.strip(),
                    "config_hash": meta["config_hash"],
                    "seed": meta["seed"], "timestamp": stamp}, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
            written += len(batch)
            rate = (time.time() - start) / written
            log(f"{written}/{len(todo)} done, {rate:.2f} s per image, about {rate * (len(todo) - written) / 60:.0f} min left")
    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/models.yaml"))
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--questions", type=Path, default=None)
    parser.add_argument("--question-prompt", default=QUESTION_PROMPT)
    args = parser.parse_args()

    config, spec = load_config(args.config, args.model)
    questions = None
    if args.questions:
        config = {**config, "prompt": args.question_prompt}
        questions = read_questions(args.questions)
    cfg = run_config(config, spec, args.seed)
    meta = {"model": spec["name"], "revision": spec["revision"][:12], "prompt": config["prompt"],
            "config_hash": config_hash(cfg), "seed": args.seed}
    rows = read_manifest(args.manifest)
    rows = rows[:args.limit] if args.limit else rows
    if questions is not None:
        no_question = [r["image_id"] for r in rows if str(r["image_id"]) not in questions]
        if no_question:
            raise SystemExit(f"{len(no_question)} manifest rows have no question in {args.questions}, e.g. {no_question[:3]}")
    print(f"{spec['name']} at {meta['revision']}, config hash {meta['config_hash']}")

    repair_tail(args.out)
    if not {row_key(r) for r in rows} - done_keys(args.out):
        print("every row is already done, nothing to run")
        return

    import torch
    torch.manual_seed(args.seed)
    t0 = time.time()
    processor, model = load_model(spec)
    print(f"loaded in {time.time() - t0:.0f} s")
    ask = make_ask(processor, model, config["prompt"], config["max_new_tokens"], spec["name"] in NESTED_IMAGES)
    written = run(rows, ask, args.out, args.images_root, meta, args.batch_size, questions=questions)
    print(f"wrote {written} rows to {args.out}")


if __name__ == "__main__":
    main()
