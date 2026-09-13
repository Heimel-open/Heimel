from vaig import __version__
from vaig._version import __version__ as canonical_version


def test_public_version_uses_canonical_source():
    assert __version__ == canonical_version
    assert __version__ == "0.5.0"
