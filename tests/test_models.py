import pytest
from pydantic import ValidationError

from smart_janitor.models import Age, Extension, Rule


def test_extension_normalizes_lowercase() -> None:
    ext = Extension(type="extension", pattern="PDF")
    assert ext.pattern == "pdf"


def test_extension_strips_leading_dot() -> None:
    ext = Extension(type="extension", pattern=".pdf")
    assert ext.pattern == "pdf"


def test_extension_handles_dot_and_uppercase() -> None:
    ext = Extension(type="extension", pattern=".PDF")
    assert ext.pattern == "pdf"


def test_age_rejects_negative_days() -> None:
    with pytest.raises(ValidationError):
        Age(type="age", older_than_days=-1)


def test_age_accepts_zero_days() -> None:
    age = Age(type="age", older_than_days=0)
    assert age.older_than_days == 0


def test_rule_discriminates_match_by_type() -> None:
    """Rule should parse the correct match subtype based on the 'type' field."""
    rule = Rule.model_validate(
        {
            "match": {"type": "extension", "pattern": "pdf"},
            "action": {"kind": "move_to", "dst": "/tmp"},
        }
    )
    assert isinstance(rule.match, Extension)


def test_rule_rejects_unknown_match_type() -> None:
    with pytest.raises(ValidationError):
        Rule.model_validate(
            {
                "match": {"type": "unknown", "pattern": "x"},
                "action": {"kind": "move_to", "dst": "/tmp"},
            }
        )
