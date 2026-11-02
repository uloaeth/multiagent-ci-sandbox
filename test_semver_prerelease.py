from semver import Version


def test_is_prerelease():
    assert Version("1.0.0-rc.1").is_prerelease
    assert Version("1.0.0-0").is_prerelease
    assert not Version("1.0.0").is_prerelease
    assert not Version("1.0.0+build.5").is_prerelease  # build metadata is not a prerelease
