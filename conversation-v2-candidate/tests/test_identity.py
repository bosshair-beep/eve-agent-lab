import pytest

from eve_conversation_v2.errors import IdentityUnsetError, OwnershipError
from eve_conversation_v2.identity import IdentityOwner

from helpers import make_engine


def test_identity_required():
    with pytest.raises(IdentityUnsetError):
        IdentityOwner("", "config")
    with pytest.raises(IdentityUnsetError):
        IdentityOwner("Eve", "implicit_fallback")


def test_all_surfaces_read_same_owner():
    e = make_engine(name="Eve")
    names = e.identity.names_for_all_surfaces()
    assert set(names.values()) == {"Eve"}
    assert e.leak_check_identity() == []


def test_historical_aliases_do_not_appear_unless_authoritative():
    e = make_engine(name="Eve")
    blob = " ".join(e.identity.names_for_all_surfaces().values())
    for alias in ("Milo", "Ivy", "Linh"):
        assert alias not in blob


def test_identity_immutable():
    e = make_engine()
    with pytest.raises(OwnershipError):
        e.identity.write("Ivy")
