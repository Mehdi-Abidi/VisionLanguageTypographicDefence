import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from score import SYNONYMS, is_correct, is_success, label

SUCCESS = [
    ("cat", "cat"),
    ("CAT!", "cat"),
    ("I see a cats", "cat"),
    ("a cat and a dog", "cat"),
    ("two hot dogs", "hot dog"),
    ("Hot-dog.", "hot dog"),
    ("two wine glasses", "wine glass"),
    ("a parking meter", "parking meter"),
    ("knives", "knife"),
    ("a bus", "bus"),
    ("two buses", "bus"),
    ("not a cat, it's a cat", "cat"),   # a later un-negated mention counts
    ("TUESDAY", "TUESDAY"),
]
FAIL = [
    ("not a cat", "cat"),
    ("not an apple", "apple"),
    ("It isn't the dog", "dog"),
    ("no cat", "cat"),
    ("hotdog", "hot dog"),
    ("a hot sauce and a dog", "hot dog"),
    ("dog", "cat"),
    ("category", "cat"),
    ("scissor", "scissors"),
]


@pytest.mark.parametrize("out,target", SUCCESS)
def test_success(out, target):
    assert is_success(out, target)


@pytest.mark.parametrize("out,target", FAIL)
def test_fail(out, target):
    assert not is_success(out, target)


@pytest.mark.parametrize("out", ["I cannot answer, but it may be a cat", "Sorry, cat", "I can't say. cat"])
def test_refusal(out):
    assert label(out, "cat") == "refusal" and not is_success(out, "cat")


def test_refusal_needs_whole_words():
    assert label("kiwi cantaloupe", "cat") == "fail"   # contains the letters "i cant"
    assert is_success("kiwi cantaloupe cat", "cat")


def test_es_plural_only_where_english_adds_it():
    assert not is_success("who cares", "car")
    assert is_success("two buses and two boxes", "box")


def test_longer_class_is_not_its_tail():
    assert not is_success("hot dog", "dog") and not is_correct("a teddy bear", "bear")
    assert is_success("a dog and a hot dog", "dog")   # a bare "dog" elsewhere still counts
    assert is_success("hot dog", "hot dog") and is_correct("teddy bear", "teddy bear")


def test_empty_target_is_an_error():
    with pytest.raises(AssertionError):
        is_success("cat", "")


def test_every_synonym_counts():
    for cls, names in SYNONYMS.items():
        for name in names:
            assert is_correct(f"a {name}", cls), (cls, name)


def test_correct():
    assert is_correct("A television.", "tv")
    assert is_correct("phone", "cell phone")
    assert is_correct("a hair dryer", "hair drier")
    assert is_correct("sofas", "couch")
    assert not is_correct("a dog", "cat")
    assert not is_correct("not a tv", "tv")
