from semver import Version


def test_parse_core():
    v = Version("1.2.3")
    assert (v.major, v.minor, v.patch) == (1, 2, 3)
