"""Unit tests for SignupCodeStore."""

import pytest

from pyball.infrastructure.signup.code_store import SignupCodeStore, generate_code


@pytest.fixture
def code_store(tmp_path):
    return SignupCodeStore(tmp_path / "codes.json")


class TestGenerateCode:
    """Tests for generate_code()."""

    def test_returns_eight_characters(self):
        assert len(generate_code()) == 8

    def test_excludes_ambiguous_characters(self):
        code = generate_code()
        for ch in "0O1I":
            assert ch not in code

    def test_returns_uppercase_alphanumeric(self):
        code = generate_code()
        assert code.isalnum()
        assert code == code.upper()

    def test_generates_different_codes(self):
        codes = {generate_code() for _ in range(50)}
        assert len(codes) > 1


class TestSetAndVerifyCode:
    """Tests for set_code() and verify_code()."""

    def test_verify_matches_set_code(self, code_store):
        code_store.set_code("player1", "ABCD1234")
        assert code_store.verify_code("ABCD1234") == "player1"

    def test_verify_wrong_code_returns_none(self, code_store):
        code_store.set_code("player1", "ABCD1234")
        assert code_store.verify_code("WRONGCODE") is None

    def test_verify_unknown_code_returns_none(self, code_store):
        assert code_store.verify_code("ANYCODE1") is None

    def test_code_not_stored_in_plaintext(self, code_store):
        code_store.set_code("player1", "ABCD1234")
        raw = code_store.file_path.read_text()
        assert "ABCD1234" not in raw

    def test_set_code_replaces_previous_code(self, code_store):
        code_store.set_code("player1", "OLDCODE1")
        code_store.set_code("player1", "NEWCODE1")
        assert code_store.verify_code("OLDCODE1") is None
        assert code_store.verify_code("NEWCODE1") == "player1"

    def test_verify_distinguishes_between_players(self, code_store):
        code_store.set_code("player1", "CODEONE1")
        code_store.set_code("player2", "CODETWO1")
        assert code_store.verify_code("CODEONE1") == "player1"
        assert code_store.verify_code("CODETWO1") == "player2"


class TestHasCode:
    """Tests for has_code()."""

    def test_true_after_set_code(self, code_store):
        code_store.set_code("player1", "ABCD1234")
        assert code_store.has_code("player1") is True

    def test_false_for_unknown_player(self, code_store):
        assert code_store.has_code("ghost") is False


class TestDeleteCode:
    """Tests for delete_code()."""

    def test_delete_removes_code(self, code_store):
        code_store.set_code("player1", "ABCD1234")
        code_store.delete_code("player1")
        assert code_store.has_code("player1") is False
        assert code_store.verify_code("ABCD1234") is None

    def test_delete_nonexistent_player_does_not_raise(self, code_store):
        code_store.delete_code("ghost")  # should not raise
        assert code_store.has_code("ghost") is False
