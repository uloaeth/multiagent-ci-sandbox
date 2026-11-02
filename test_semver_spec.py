"""Acceptance tests (SemVer 2.0.0 + npm-style caret ranges). Do not modify."""
import pytest
from semver import Version, max_satisfying

ORDERED = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2",
           "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0", "1.2.0", "1.10.0", "2.0.0"]


def test_total_order_from_spec():
    vs = [Version(s) for s in ORDERED]
    assert sorted(reversed(vs)) == vs
    for a, b in zip(vs, vs[1:]):
        assert a < b and not b < a and a != b


def test_build_metadata_ignored_in_precedence():
    assert Version("1.0.0+build.1") == Version("1.0.0+build.2")
    assert not Version("1.0.0+b") < Version("1.0.0")


@pytest.mark.parametrize("bad", ["1.2", "1.2.3.4", "01.2.3", "1.2.3-", "1.2.3-alpha..1", "v1.2.3", "", "1.2.x"])
def test_invalid_versions_raise(bad):
    with pytest.raises(ValueError):
        Version(bad)


def test_caret_basic():
    vs = ["1.2.3", "1.4.0", "1.9.9", "2.0.0", "0.9.0"]
    assert str(max_satisfying(vs, "^1.2.3")) == "1.9.9"


def test_caret_zero_major():
    vs = ["0.2.3", "0.2.9", "0.3.0", "1.0.0"]
    assert str(max_satisfying(vs, "^0.2.3")) == "0.2.9"


def test_prerelease_excluded_unless_same_tuple():
    vs = ["1.2.3", "1.3.0-beta.1", "1.2.4-rc.1"]
    assert str(max_satisfying(vs, "^1.2.3")) == "1.2.3"
    assert str(max_satisfying(vs, "^1.2.4-rc.0")) == "1.2.4-rc.1"


def test_no_match_returns_none():
    assert max_satisfying(["2.0.0"], "^1.0.0") is None
