import json
import os
import tempfile

import pytest

from osskey.vault import Credential, VaultManager


@pytest.fixture
def vault() -> VaultManager:
    return VaultManager()


class TestAddCredential:
    def test_add_returns_credential_with_generated_id(self, vault):
        cred = vault.add("github.com", "alice", "s3cret!")
        assert cred.id is not None
        assert len(cred.id) == 32
        assert cred.label == "github.com"
        assert cred.username == "alice"
        assert cred.password == "s3cret!"

    def test_add_increments_count(self, vault):
        assert len(vault) == 0
        vault.add("a", "b", "c")
        assert len(vault) == 1
        vault.add("d", "e", "f")
        assert len(vault) == 2

    def test_credential_created_at_set(self, vault):
        import time
        before = time.time()
        cred = vault.add("test", "user", "pass")
        after = time.time()
        assert before <= cred.created_at <= after
        assert cred.updated_at == pytest.approx(cred.created_at, rel=1e-9)


class TestEditCredential:
    def test_edit_updates_fields(self, vault):
        cred = vault.add("old-label", "old-user", "old-pass")
        updated = vault.edit(cred.id, label="new-label", password="new-pass")
        assert updated is not None
        assert updated.label == "new-label"
        assert updated.username == "old-user"
        assert updated.password == "new-pass"

    def test_edit_returns_none_for_unknown_id(self, vault):
        result = vault.edit("nonexistent", label="x")
        assert result is None

    def test_edit_updates_timestamp(self, vault):
        cred = vault.add("test", "u", "p")
        import time
        time.sleep(0.01)
        updated = vault.edit(cred.id, label="changed")
        assert updated.updated_at > cred.created_at


class TestDeleteCredential:
    def test_delete_removes_credential(self, vault):
        cred = vault.add("test", "u", "p")
        assert len(vault) == 1
        assert vault.delete(cred.id) is True
        assert len(vault) == 0

    def test_delete_returns_false_for_missing(self, vault):
        assert vault.delete("nonexistent") is False

    def test_delete_only_removes_specified(self, vault):
        c1 = vault.add("a", "1", "p1")
        c2 = vault.add("b", "2", "p2")
        vault.delete(c1.id)
        assert vault.get(c2.id) is not None
        assert len(vault) == 1


class TestSearchCredential:
    @pytest.fixture
    def populated(self) -> VaultManager:
        v = VaultManager()
        v.add("github.com", "alice@corp", "gh-pass")
        v.add("corp-vpn", "jdoe", "vpn-pass")
        v.add("gitlab.com", "alice@corp", "gl-pass")
        v.add("example.org", "bob", "ex-pass")
        return v

    def test_search_by_label(self, populated):
        results = populated.search("github")
        assert len(results) == 1
        assert results[0].label == "github.com"

    def test_search_by_username(self, populated):
        results = populated.search("jdoe")
        assert len(results) == 1
        assert results[0].username == "jdoe"

    def test_search_case_insensitive(self, populated):
        results = populated.search("GITHUB")
        assert len(results) == 1
        assert results[0].label == "github.com"

    def test_search_partial_match(self, populated):
        results = populated.search("alice")
        assert len(results) == 2
        assert all("alice" in r.username.lower() for r in results)

    def test_search_no_match(self, populated):
        results = populated.search("zzzzzzz")
        assert len(results) == 0

    def test_search_empty_query_returns_all(self, populated):
        results = populated.search("")
        assert len(results) == 4


class TestSerializeDeserialize:
    def test_round_trip_preserves_all_data(self, vault):
        vault.add("a.example.com", "alice", "pass1")
        vault.add("b.example.org", "bob", "pass2!")
        vault.add("c.example.net", "charlie", "pass3@")

        serialized = vault.serialize()
        deserialized_list = json.loads(serialized.decode("utf-8"))

        assert len(deserialized_list) == 3
        for item in deserialized_list:
            assert "id" in item
            assert "label" in item
            assert "username" in item
            assert "password" in item
            assert "created_at" in item
            assert "updated_at" in item

    def test_deserialize_into_empty_vault(self, vault):
        vault.add("orig", "u", "p")
        data = vault.serialize()

        new_vault = VaultManager()
        creds = new_vault.deserialize(data)
        assert len(creds) == 1
        assert new_vault.get(creds[0].id) is not None
        assert new_vault.credentials[0].label == "orig"

    def test_serialize_empty_vault(self, vault):
        data = vault.serialize()
        assert data == b"[]"

    def test_deserialize_empty_vault(self, vault):
        vault.deserialize(b"[]")
        assert len(vault) == 0

    def test_multiple_serialize_deserialize_cycles(self, vault):
        vault.add("test", "user", "pass")
        for _ in range(5):
            data = vault.serialize()
            vault = VaultManager()
            vault.deserialize(data)
        assert len(vault) == 1
        assert vault.credentials[0].label == "test"


class TestFileSaveLoad:
    def test_save_and_load(self, vault):
        vault.add("saved-cred", "saved-user", "saved-pass")
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp = f.name

        try:
            vault.save(tmp)
            loaded = VaultManager()
            loaded.load(tmp)
            assert len(loaded) == 1
            assert loaded.credentials[0].label == "saved-cred"
        finally:
            os.unlink(tmp)

    def test_load_empty_file(self, vault):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(b"[]")
            tmp = f.name

        try:
            loaded = VaultManager()
            loaded.load(tmp)
            assert len(loaded) == 0
        finally:
            os.unlink(tmp)

    def test_save_overwrites_existing(self, vault):
        vault.add("first", "u1", "p1")
        with tempfile.NamedTemporaryFile(delete=False) as f:
            tmp = f.name
        try:
            vault.save(tmp)
            vault2 = VaultManager()
            vault2.add("second", "u2", "p2")
            vault2.save(tmp)
            loaded = VaultManager()
            loaded.load(tmp)
            assert len(loaded) == 1
            assert loaded.credentials[0].label == "second"
        finally:
            os.unlink(tmp)


class TestGetCredential:
    def test_get_returns_credential(self, vault):
        cred = vault.add("test", "user", "pass")
        found = vault.get(cred.id)
        assert found is not None
        assert found.id == cred.id

    def test_get_returns_none_for_missing(self, vault):
        assert vault.get("nonexistent") is None

    def test_credentials_property_returns_copy(self, vault):
        vault.add("test", "u", "p")
        orig_list = vault.credentials
        orig_list.clear()
        assert len(vault.credentials) == 1


class TestCredentialDataclass:
    def test_credential_defaults(self):
        c = Credential(label="test", username="u", password="p")
        assert c.id is not None
        assert len(c.id) == 32
        assert c.label == "test"
        assert c.username == "u"
        assert c.password == "p"
        assert c.created_at > 0
        assert c.updated_at == pytest.approx(c.created_at, rel=1e-9)
