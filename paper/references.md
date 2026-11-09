# PixelGuard: Reference Verification and Claim Audit (Ticket C1, second pass)

Checked: Nov 8–9, 2026. Pass 2 read the full text of every paper our claims depend on and checked every sentence in `research-plan.md` and `evaluation-and-proposal.md` that cites or leans on prior work.

**Read depth.** Full text: RIO-Bench, Balakrishnan, Pictionary, Repeat-After-Me, Lee (AIGI), Liu ECCV, Devil in the Lens, Nagaraja, Cheng (TypoD), DE-FIVE, Athalye. Abstract plus key sections: Liu 2611, Dyslexify, Qraitem, Chang, MIRAGE, Guo. Checked by hand (Ali): Azuma venue, Goh DOI.

Verdicts: ✅ supported · ⚠️ partly or loosely supported, needs rewording · ❌ unsupported or contradicted by the source · 🧪 our hypothesis, fine if labelled as one

---

## 1. Reference table

| Key | arXiv | Authors | Venue | What it actually does (one line) |
|---|---|---|---|---|
| `waseda2025rio` | 2512.11899 | Waseda, Yamabe, Shiono, Sasaki, Takahashi | arXiv 2025 | Same-scene read/ignore benchmark built on TextVQA images. Attacks are misleading **class labels** (object questions) and LLM-written contradicting phrases (text questions). No instruction-style text. Tests CoT prompting and two fine-tuning defences, not image preprocessing |
| `balakrishnan2026reading` | 2604.12371 v2 | Balakrishnan, Mendapara, Garg (Cisco) | arXiv 2026 | **Jailbreak** study: 1,000 SALAD-Bench harmful prompts rendered as black text on a white 1024×1024 canvas, user turn says "follow the instructions in the image". GPT-4o, Claude Sonnet 4.5, Mistral-Large-3, Qwen3-VL-4B. Font 6–28 px, 10 transforms incl. blur σ=2/5. No JPEG, no OCR |
| `zhang2026render` | 2609.36121 | J. Zhang, Baroian, van Rijn, Shafran, Tramèr | arXiv 2026 | Instructions are followed 2×–300× less when given as an image than as text (six VLMs, conflicting instruction pairs). Turns this into a defence. States that untrusted content which is already an image is out of scope |
| `chen2026repeat` | 2609.04533 | S. Chen, Tsai, Evtimov, Chaudhuri, Popa, Wagner, Zharmagambetov | AISec '26 | Black-box adaptive visual injection on DocVQA with a real user question. ≥82% ASR on open 27–38B models, ≥47% on frontier models. Ablates position, font size, contrast. Tests JPEG, down-up, OCR defences **non-adaptively** |
| `lee2026aigi` | 2609.39662 | E. Lee, J. Kim, J.-S. Lee (Yonsei) | arXiv 2026 | AIGI detection. Attacks: random text (control), class label ("REAL"), instruction ("Answer: REAL"), file path, logo. Robustness to JPEG Q∈{75,50,25} and downsampling s∈{0.9,0.75,0.5}, averaged over two detection models only |
| `liu2026labelfree` | 2611.01513 | B. Liu, Ye, Xiong, He, Sinha, A. Zhang | arXiv 2026 | Head-level circuit suppression in CLIP. Up to 46.9% improvement, ≤1% clean loss, 5 CLIPs × 4 benchmarks |
| `liu2026towards` | 2607.02494 | same six | ECCV 2026 | Training-free circuit intervention in CLIP. Zero-ablation in LVLM vision encoders (**white-box**) gives **small** RIO-Bench gains: +0.97 pts avg on Qwen3-VL-4B (62.95→63.92), +0.01 to +1.73 elsewhere |
| `hufe2026dyslexify` | 2508.20570 v2 | Hufe, Venhoff, Purelku, Dreyer, Lapuschkin, Samek | ICLR 2026 | CLIP head ablation, up to +22.06% on typographic ImageNet-100, <1% clean loss |
| `cheng2024unveiling` | 2402.19150 | H. Cheng, Xiao, Gu, Yang, Duan, J. Zhang, Cao, K. Xu, R. Xu | ECCV 2024, pp. 179–196 | TypoD: misleading **answer labels** on images, multiple-choice VQA. LLaVA-1.5/1.6, InstructBLIP, MiniGPT4-v2. Varies size (3–15 px), opacity, colour, position. Mitigation is **prompt-based** (gap 42.3→13.9 pts) |
| `qraitem2024selfgen` | 2402.00626 v3 | Qraitem, Tasnim, Teterwak, Saenko, Plummer | arXiv | Self-generated label attacks. "Reasoned" attacks (class plus description, i.e. longer text) beat single-class attacks on LVLMs, up to 60% drop |
| `nagaraja2025ipi` | 2603.03637 | Nagaraja, L. Zhang, Z. Wang, B. Zhang, Patil | FLLM 2025, pp. 916–922 | COCO + GPT-4-turbo, **image only, no user text**. Visible prompts reach 73–100%. 64% is the best *stealthy* setting (low-contrast region-averaged colour plus an object-aware "Ignore …" prefix) |
| `li2026devil` | 2607.10269 | Y. Li, H. Wang, Y. Shao, S. Zhang, Y. Long | arXiv 2026 | Physical injections via smart glasses, 12 VLMs, up to 96% (digital) / 60% (physical). TaCo-Guard defence = **EasyOCR → LLM taint score → Gaussian-blur risky boxes** |
| `zhong2026defive` | 2606.22779 | Zhong, Sharma, Fok, Thing | arXiv 2026 | Detector combining black-box Fourier features and a **white-box** embedding score. Evaluated on **perturbation-based** meta-instruction and jailbreak images, not on rendered text |
| `chang2026sign` | 2604.19844 | Chang, Xue, Sun, Pang, Kanhere, Pearce | arXiv 2026 | Embodied agents. Helpful vs misleading visual signs, 7 LVLM agents, multi-agent defence |
| `dai2026mirage` | 2606.20717 | Dai, J. Ma, B. Ma, Yan, Y. Yang, Y. Zhang | Findings EMNLP 2026 | Stealthy visual injection in a constrained web region (ad slot) against web agents |
| `guo2018countering` | 1711.00117 | Guo, Rana, Cissé, van der Maaten | ICLR 2018 | Input transforms (bit-depth, JPEG, TV-min, quilting) against perturbation attacks. Precedent for two of our six defences |
| `athalye2018obfuscated` | 1802.00420 | Athalye, Carlini, Wagner | ICML 2018 | Broke Guo et al.'s JPEG and bit-depth defences with BPDA (white-box, gradient). Different threat model from our rendering search |
| `azuma2023defense` | 2304.04512 | Azuma, Matsui | ICCV 2023 Workshops (AROW) | Learned defence prefix for CLIP. ✅ venue checked by hand |
| `goh2021multimodal` | n/a | Goh et al. | Distill 2021 | Original CLIP typographic attack. ✅ DOI checked by hand |

---

## 2. Every number we plan to quote

| Number | Source and location | What it measures | Safe phrasing |
|---|---|---|---|
| **64%** | Nagaraja, abstract; Table V | GPT-4-turbo, stealth-constrained rendering (low-contrast colour + "Ignore …" prefix), **no user question** | "up to 64% on GPT-4-turbo when the injected text is made inconspicuous" |
| **46.9%** | Liu 2611, abstract | Improvement in CLIP object classification under attack | "improves accuracy under typographic attack by up to 46.9%" (not "recovery") |
| **36% vs 8%** | Balakrishnan, abstract; Table 1 (35.6 vs 7.7) | GPT-4o **jailbreak** compliance, typed text vs rendered image | "GPT-4o complied with 36% of typed jailbreak prompts but 8% of the same prompts as images" |
| **34–96%** | Balakrishnan, abstract finding (4) | **Relative reduction** in jailbreak ASR under heavy blur / triple degradation across 4 models (Qwen −34% … Claude −96%) | "heavy blur cut jailbreak success by 34–96%, depending on the model" |

Watch-outs:
- Balakrishnan's Qwen3-VL-4B baseline at 20 px is 48.2% in Table 1 and 43.4% in Table 5. The inconsistency is theirs. Quote whichever table you use and name it.
- Cheng's abstract says 42.07%, while Table 2 says 42.3 pts. Quote the abstract number with "from 42.07% to 13.90%".
- Repeat-After-Me's v1 abstract says >80%, the AISec version says >82%. Cite AISec.

---

## 3. Claim audit: our two documents vs the papers

### 3.1 Claims about prior work

| # | Our claim (where) | Verdict | What the source actually says | Fix |
|---|---|---|---|---|
| 1 | "A 2026 AIGI paper compares label vs instruction text **with matched length**" (plan, gap row 1) | ❌ | Lee et al. match the *instruction* to the **random-text control** in character count. The label ("REAL") is shorter than the instruction ("Answer: REAL") | "…compares label and instruction overlays against a length-matched random-text control" |
| 2 | Image text acting mostly as context is "already supported by Pictionary and Balakrishnan" (plan, row 2); "which other papers have shown" (proposal, summary) | ❌ overclaim | Pictionary shows image-delivered *instructions* are obeyed less than typed ones. It never tests labels, and it says image-native content is out of scope. Balakrishnan shows the same for GPT-4o and Claude jailbreaks, and **finds no gap for Qwen3-VL-4B** (48.9 vs 48.2) or Mistral. Neither paper shows image text "acts as context" | "Prior work shows typographic labels mislead LVLMs (Cheng; Qraitem; RIO-Bench) and that instructions carry less authority as images than as text for some models (Pictionary; Balakrishnan for GPT-4o and Claude, not Qwen3-VL-4B)" |
| 3 | "Cheap image defences such as blur, JPEG and OCR-guided inpainting have been tested against instruction attacks only" (proposal, problem statement; plan, abstract) | ❌ | Lee et al. applied JPEG and downsampling to **class-label** attacks. They found no reliable mitigation (ASR went *up*) and attributed it to image damage | "…have mostly been tested on instructions. The one study that applied JPEG and downsampling to label attacks (Lee et al., AIGI detection) found they did not help, with the effect confounded by image damage. No study sweeps defence strength for both attack types on the same images with a reading-task cost" |
| 4 | "OCR-guided inpainting" as a tested defence family (proposal, problem statement) | ⚠️ | Nobody we cite inpaints. The closest are TaCo-Guard (OCR → LLM score → **blur**) and Repeat-After-Me's OCR defences (OCR text passed to the model, image unchanged) | Say "OCR-guided masking (TaCo-Guard) and OCR transcription (Repeat-After-Me)". Present inpainting as *our* variant |
| 5 | "Defence costs are rarely reported" (plan + proposal) | ⚠️ | RIO-Bench's whole point is the reading-ability cost of text-ignoring defences (e.g. LLaMA-1.5-13B Text-VQA −76% under IT-RT). Pictionary reports utility. Devil says utility is maintained but gives no number | "…rarely reported for **image-preprocessing** defences against typographic attacks. RIO-Bench shows this cost for model-level defences" |
| 6 | "Context and instruction attacks… use different images, metrics and defences" (plan, problem statement) | ⚠️ | True of most work, but Lee et al. run both on the same images with one ASR metric (in a narrow task) | Add "mostly", and cite Lee as the exception |
| 7 | "Short labels stay legible after blur, compression and inpainting longer than long commands" (plan + proposal) | 🧪 | No paper tests this. The nearest is Qraitem: *longer* descriptive labels are **more** effective on LVLMs before any defence | Label it as the H2 premise. Our C-long cell tests it directly |
| 8 | "Misleading context is the bigger risk" (plan, paper outline → Introduction) | ❌ | No source supports this. Lee et al.'s on-topic instruction ("Answer: REAL") often matches or beats the label | Remove it, or turn it into a question RQ2 answers |
| 9 | Balakrishnan: "font size and degradation for instruction attacks only, on Qwen3-VL-4B among others" | ⚠️ | Jailbreaks, text-only synthetic images, no competing question | "…for rendered jailbreak prompts on text-only images" |
| 10 | "Qwen3-VL-4B, the same model Balakrishnan used" (plan, gap row 11) | ✅ | Also used by Liu ECCV on RIO-Bench (base 62.95% on Obj-Attack MC). A second comparison point | Cite both |
| 11 | "Qwen3-VL-4B may show little gap, as Balakrishnan found no text/image modality gap for it" (plan, H1 note) | ⚠️ reasoning leap | The fact is right. But Balakrishnan's gap is *typed vs rendered*, and H1 compares *label vs command, both rendered*. One doesn't predict the other | Keep the fact, drop the "as" |
| 12 | Pictionary: "image text is followed less than typed text" | ✅ | 2×–300×, six VLMs, under conflict | Add "when the two conflict" |
| 13 | "Our RQ1 replicates this" | ❌ | We have no typed-text condition | "motivates" |
| 14 | Repeat-After-Me: "JPEG and OCR defences against adaptive visual injection on frontier models" | ⚠️ | Attack adaptive, defences tested non-adaptively. Victims also include open 27–38B models | "…evaluated non-adaptively against injections optimised on undefended models" |
| 15 | "We test them … on small open models, with utility cost" | ✅ | Their smallest victim is 27B. No utility numbers for defences | Keep |
| 16 | AIGI paper: "no defence sweep" | ❌ | JPEG at 3 qualities and downsampling at 3 scales | "a small robustness sweep (JPEG, downsampling), no utility cost, no defence-aware attacker" |
| 17 | RIO-Bench: "We add instruction attacks and defences on the same images" | ⚠️ | RIO-Bench already evaluates defences (CoT, IT-RT, RIO-RT) on its images | "We add instruction attacks and **image-preprocessing** defences" |
| 18 | Liu 2607: "circuit defence applied to VLM encoders on RIO-Bench" | ✅ | Gains are 0.0–2.1 pts and it needs white-box access | Don't call it "substantial" (their abstract does) |
| 19 | Nagaraja: "up to 64% success on GPT-4-turbo" | ✅ | Stealth setting, no user question | Add both qualifiers |
| 20 | Devil in the Lens: "mask-based filter defence" | ✅ | OCR + LLM scorer + blur | Name the mechanism |
| 21 | DE-FIVE: "Fourier-feature detector for malicious image prompts" | ⚠️ | Hybrid black-box Fourier + white-box embedding. Tested on **perturbation** images, not typography | "…for perturbation-based malicious images" |
| 22 | Guo / Athalye: "classical input transformations and why adaptive attackers break them" | ✅ | Athalye breaks Guo's JPEG and bit-depth with gradient (BPDA) attacks on classifiers | Note that ours is a black-box rendering search, which is a weaker attacker |
| 23 | 2611.01513 "exists… 46.9% in abstract" (proposal, fix 1) | ✅ | | "improvement", not "recovery" |
| 24 | Dyslexify, Cheng, Qraitem, Chang, MIRAGE, Goh, Azuma role lines | ✅ | | |

### 3.2 Findings in the papers that affect the design, not just the wording

1. **Image-damage confound (Lee et al.).** JPEG and downsampling *raised* label-attack ASR because the object evidence weakened. If our defences damage the object, context ASR can hold up for reasons unrelated to text robustness, and the H2 headline would be an artifact. **Fix (C2, before any run):** report ASR on all images *and* on images the model still classifies correctly when clean under the same defence. H2 must hold on both. Note that Lee et al. already compute ASR only over clean-correct images, so this is established practice.
2. **H1 contrasts two things at once.** C-on vs I-off differs in *role* and *topic*. The clean role contrast is **C-on vs I-on** (same target word). The closest evidence (Lee et al., where "Answer: REAL" is effectively our I-on) has the instruction **matching or beating** the label in most cells. → see Question 1.
3. **Longer labels can be stronger (Qraitem).** C-long may beat C-on *before* any defence. That is fine for separating length from role, but don't predict C-long < C-on.
4. **Font-size prior.** Our default is 16 px on a 512 px short side (3.1%). Lee et al. use 6% of the short side and saw ASR fall sharply at 2%. Repeat-After-Me saw GPT/Claude ASR collapse at small fonts. Cheng's strongest setting was the largest size. → see Question 2.
5. **Pilot-gate priors we can now check against:**
   - RIO-Bench, label attacks, multiple choice: SmolVLM-2B 92.1→51.3%, Qwen3-VL-8B 96.1→72.4%.
   - Liu ECCV: Qwen3-VL-4B 62.95% on RIO Obj-Attack MC.
   - Balakrishnan: Qwen3-VL-4B under blur σ=2 barely moves (43.4→38.3%).

   If our pilot C-on numbers are wildly off these, suspect the pipeline first. The caveat is that ours is open-ended, theirs mostly multiple choice.
6. **Pictionary marks our setting as open.** It says it offers no protection when untrusted content is already an image. Cite this in the Introduction as a stated gap from a strong group.
7. **Nagaraja's success rates aren't comparable to ours.** They have no user question, and Repeat-After-Me shows a real competing question makes injection much harder. Don't put their 73–100% next to our numbers without saying so.
8. **TextVQA overlap.** RIO-Bench is built on TextVQA images, and so is our utility set. That's fine, but mention it so a reviewer doesn't think we missed it.

---

## 4. The closest papers: what they did, what we add (rewritten)

**RIO-Bench.** Same-scene read/ignore counterfactuals with misleading class labels on TextVQA photos. Shows that model-level defences buy robustness by losing reading ability. **We add** instruction-style attacks on the same images and *image-preprocessing* defences, with their reading cost.

**Balakrishnan et al.** Rendered jailbreak prompts on text-only canvases across font sizes and degradations, with no competing question, and embedding distance as a predictor. **We add** natural photos with a benign question, a label-vs-command contrast, and JPEG and OCR-based defences.

**Pictionary.** Instructions carry less authority as images than as text, used as a defence for text channels. Explicitly leaves image-native injection open. **We add** a study of that open case: text already in the image, as label or command, and how defences treat each.

**Repeat-After-Me.** Adaptive black-box injection with a real user question. Preprocessing and OCR defences tested only against injections tuned on undefended models. **We add** context attacks, small open models, defence utility cost, and an attacker that searches against each defence.

**Lee et al. (AIGI).** Label, instruction and file-path overlays on one binary task. JPEG and downsampling fail to mitigate and are confounded with image damage. **We add** general object VQA, strength curves for six defences, the image-damage control, reading-task cost and a defence-aware attacker.

**Devil in the Lens.** Physical injections plus an OCR-guided blur defence (TaCo-Guard). **We add** context attacks, an inpainting variant with no LLM scorer, and RQ3, i.e. how often the model follows text that OCR misses, which bounds every OCR-guided defence including theirs.

**Liu et al. (ECCV).** White-box circuit ablation. Small gains on LVLMs. **We add** black-box, model-agnostic defences. This motivates the scope rather than competing with it.

---

## 5. Open questions for the team (decide before C2 on Nov 10)

1. **H1 contrast.** Keep H1 as C-on vs I-off (role and topic differ), or pre-register the clean role contrast C-on vs I-on as well? Prior evidence suggests I-on may win.
2. **Default font size.** Keep 16 px (3% of the short side) with the pilot fallback to 24 px, or start at 24–32 px (5–6%) to match prior work?
3. **Who fixes the docs.** Items 1–8 and 13–17 in §3.1 change wording in Mehdi's proposal and in Related Work (B11). Agree at kickoff who edits what.
4. **Weekly re-search** (Nov 15): add "typographic defense JPEG" and "OCR inpainting prompt injection" to the queries.
