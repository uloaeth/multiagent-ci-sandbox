"""Semantic Versioning (SemVer) 2.0.0 helpers.

Provides :class:`Version` (strict SemVer 2.0.0 parsing and precedence) and
:func:`max_satisfying` (npm-style caret range resolution).
"""

from functools import total_ordering

import re

__all__ = ["Version", "max_satisfying"]

_ALLOWED_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.-+")
_IDENT_RE = re.compile(r"[0-9A-Za-z-]+")
_NUMERIC_RE = re.compile(r"0|[1-9][0-9]*")


@total_ordering
class Version:
    """A single SemVer 2.0.0 version: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]."""

    def __init__(self, text):
        if not isinstance(text, str):
            raise ValueError(f"version must be a string, got {type(text).__name__}")
        if not text:
            raise ValueError("empty version string")
        if any(ch not in _ALLOWED_CHARS for ch in text):
            raise ValueError(f"invalid character in version: {text!r}")

        # Build metadata, if any: everything after the first '+'.  Build
        # identifiers may contain leading zeros and hyphens.
        head, sep, build = text.partition("+")
        build_idents = None
        if sep:
            if not build:
                raise ValueError(f"empty build metadata in version: {text!r}")
            build_idents = self._split_identifiers(build, "build")

        # Prerelease, if any: everything after the first '-' in the head part.
        core, sep, pre = head.partition("-")
        pre_idents = None
        if sep:
            if not pre:
                raise ValueError(f"empty prerelease in version: {text!r}")
            pre_idents = self._split_identifiers(pre, "prerelease")
            # Numeric prerelease identifiers must not have leading zeros.
            for ident in pre_idents:
                if ident.isdigit() and len(ident) > 1 and ident.startswith("0"):
                    raise ValueError(
                        f"leading zero in numeric prerelease identifier {ident!r} in {text!r}"
                    )

        core_parts = core.split(".")
        if len(core_parts) != 3:
            raise ValueError(f"version core must be MAJOR.MINOR.PATCH: {text!r}")
        for part in core_parts:
            if not _NUMERIC_RE.fullmatch(part):
                raise ValueError(f"invalid numeric core part {part!r} in {text!r}")

        self.major = int(core_parts[0])
        self.minor = int(core_parts[1])
        self.patch = int(core_parts[2])
        # prerelease/build: None when absent, otherwise a list of identifier strings.
        self.pre = pre_idents
        self.build = build_idents
        self.text = text

    @staticmethod
    def _split_identifiers(text, kind):
        idents = text.split(".")
        for ident in idents:
            if not ident or not _IDENT_RE.fullmatch(ident):
                raise ValueError(f"invalid {kind} identifier {ident!r}")
        return idents

    def _core_key(self):
        return (self.major, self.minor, self.patch)

    def _pre_less_than(self, other):
        """Compare prerelease identifier lists (SemVer 2.0.0, section 11).

        Assumes both instances have a non-empty prerelease list.
        """
        for mine, theirs in zip(self.pre, other.pre):
            mine_num = mine.isdigit()
            theirs_num = theirs.isdigit()
            if mine_num and theirs_num:
                diff = int(mine) - int(theirs)
                if diff:
                    return diff < 0
            elif mine_num and not theirs_num:
                return True  # numeric identifiers always rank below alphanumeric
            elif not mine_num and theirs_num:
                return False
            elif mine != theirs:
                return mine < theirs  # ASCII order for alphanumeric identifiers
        # All compared identifiers equal: the larger set has higher precedence.
        return len(self.pre) < len(other.pre)

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        if self._core_key() != other._core_key():
            return self._core_key() < other._core_key()
        if self.pre is None:
            return False  # a release outranks every prerelease of the same core
        if other.pre is None:
            return True
        return self._pre_less_than(other)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        if self._core_key() != other._core_key():
            return False
        # Build metadata is ignored for ordering AND for equality.
        return (self.pre or []) == (other.pre or [])

    def __hash__(self):
        return hash((self._core_key(), tuple(self.pre or [])))

    def __str__(self):
        return self.text

    def __repr__(self):
        return f"Version({self.text!r})"


def _next_breaking(base):
    """First version excluded by a caret range (exclusive upper bound).

    ^1.2.3 -> <2.0.0 ; ^0.2.3 -> <0.3.0 ; ^0.0.3 -> <0.0.4
    """
    if base.major > 0:
        return Version(f"{base.major + 1}.0.0")
    if base.minor > 0:
        return Version(f"0.{base.minor + 1}.0")
    return Version(f"0.0.{base.patch + 1}")


def _parse_constraint(constraint):
    if isinstance(constraint, Version):
        return "exact", constraint
    if not isinstance(constraint, str):
        raise ValueError(f"invalid constraint: {constraint!r}")
    if constraint.startswith("^"):
        body = constraint[1:]
        if not body:
            raise ValueError(f"invalid caret constraint: {constraint!r}")
        return "caret", Version(body)  # ValueError propagates for bad syntax
    return "exact", Version(constraint)  # ValueError propagates for bad syntax


def _satisfies(version, kind, base):
    if kind == "exact":
        return version == base
    # Caret range: >= base and < next breaking version.
    if version < base:
        return False
    if not version < _next_breaking(base):
        return False
    # NPM prerelease rule: a prerelease candidate is only accepted when the
    # constraint itself has a prerelease and both share [major, minor, patch].
    if version.pre is not None:
        if base.pre is None:
            return False
        if (version.major, version.minor, version.patch) != (
            base.major,
            base.minor,
            base.patch,
        ):
            return False
    return True


def max_satisfying(versions, constraint):
    """Return the highest :class:`Version` satisfying *constraint*, or None.

    Entries of *versions* that are not valid versions are skipped silently.
    """
    kind, base = _parse_constraint(constraint)
    best = None
    for entry in versions:
        if isinstance(entry, Version):
            version = entry
        elif isinstance(entry, str):
            try:
                version = Version(entry)
            except ValueError:
                continue  # skip invalid entries silently
        else:
            continue
        if _satisfies(version, kind, base) and (best is None or version > best):
            best = version
    return best
