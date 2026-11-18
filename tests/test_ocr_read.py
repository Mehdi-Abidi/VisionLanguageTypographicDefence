import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from ocr_read import best_match


def word(text, confidence=0.9, kept=True):
    return {"text": text, "confidence": confidence, "kept": kept}


def test_exact_match():
    ocr_read, confidence = best_match([word("cat")], "cat")
    assert ocr_read == 1
    assert confidence == 0.9


def test_case_insensitive():
    ocr_read, _ = best_match([word("CAT")], "cat")
    assert ocr_read == 1


def test_one_edit_away_still_counts():
    ocr_read, _ = best_match([word("cot")], "cat")  # substitution, distance 1
    assert ocr_read == 1


def test_two_edits_away_does_not_count():
    ocr_read, _ = best_match([word("cow")], "cat")  # distance 2
    assert ocr_read == 0


def test_below_confidence_threshold_is_ignored():
    ocr_read, confidence = best_match([word("cat", kept=False)], "cat")
    assert ocr_read == 0
    assert confidence == 0.0


def test_nothing_detected():
    ocr_read, confidence = best_match([], "cat")
    assert ocr_read == 0
    assert confidence == 0.0


def test_picks_the_closest_of_several_detections():
    words = [word("zzz", confidence=0.5), word("cot", confidence=0.7)]
    ocr_read, confidence = best_match(words, "cat")
    assert ocr_read == 1
    assert confidence == 0.7


def test_multi_word_target():
    ocr_read, _ = best_match([word("tuesday")], "TUESDAY")
    assert ocr_read == 1
