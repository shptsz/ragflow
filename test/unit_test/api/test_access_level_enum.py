from api.db import AccessLevel


def test_access_level_values():
    assert AccessLevel.FULL == "full"
    assert AccessLevel.KB_ONLY == "kb_only"
    assert AccessLevel.FULL in AccessLevel
