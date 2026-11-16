import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from make_textvqa_set import DEFENCES, is_single, majority, manifest_rows, pick


def q(qid, image, answers):
    return {"question_id": qid, "image_id": image, "question": "?", "answers": answers}


def test_majority_is_the_most_common_answer_with_ties_broken_alphabetically():
    assert majority(["Dakota", "dakota ", "nous"]) == "dakota"
    assert majority(["b", "a", "b", "a"]) == "a"


def test_single_word_or_number():
    assert is_single("dakota") and is_single("12") and is_single("3.5")
    assert not is_single("dakota digital") and not is_single("coleman's") and not is_single("")


def test_pick_keeps_one_question_per_image_and_only_one_word_answers():
    questions = [q(1, "a", ["yes"]), q(2, "a", ["no"]), q(3, "b", ["two words"]), q(4, "c", ["7"]), q(5, "d", ["x"])]
    chosen = pick(questions, 10, 0)
    assert len({c["image_id"] for c in chosen}) == len(chosen) == 3
    assert all(c["question_id"] != 3 for c in chosen)
    assert pick(questions, 10, 0) == chosen


def test_manifest_has_every_defence_for_every_question():
    rows = manifest_rows([q(7, "a", ["yes"])])
    assert [r["defence"] for r in rows] == DEFENCES
    assert rows[0]["path"] == "images/7_textvqa_none.png"
    assert rows[1]["path"] == "images/7_textvqa_none_blur_s1.png"
