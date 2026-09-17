import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))

from app.validation.email import normalize_email, valid_syntax, classify
from app.matching.services import match


def test_email_normalization_and_roles():
    assert normalize_email(" MAILTO:Sales@Example.COM ") == "sales@example.com"
    assert valid_syntax("sales@example.com")
    assert not valid_syntax("not-an-email")
    assert classify("noreply@example.com")[0] == "blocked"
    assert classify("sales@example.com")[0] == "high"
    assert classify("info@example.com")[0] == "medium"


def test_service_matching_has_fallback():
    assert len(match("ecommerce")) >= 1
    assert len(match("unknown-sector")) >= 1
