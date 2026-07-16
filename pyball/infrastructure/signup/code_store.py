# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Signup code storage — per-player self-service identification codes."""

import hashlib
import hmac
import json
import secrets
from pathlib import Path

_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # excludes 0/O/1/I
_CODE_LENGTH = 8
_PBKDF2_ITERATIONS = 200_000


class SignupCodeStore:
    """Maps player_id -> salted hash of their personal signup code."""

    def __init__(self, file_path: Path):
        """Initialize the store with the given file path."""
        self.file_path = file_path
        self._ensure_file_exists()

    def set_code(self, player_id: str, code: str) -> None:
        """Hash and store a new code for a player, replacing any previous one."""
        salt = secrets.token_bytes(16)
        data = self._read()
        data[player_id] = {"salt": salt.hex(), "hash": _hash_code(code, salt)}
        self._write(data)

    def verify_code(self, code: str) -> str | None:
        """Return the player_id whose stored code matches, or None if no match."""
        data = self._read()
        for player_id, record in data.items():
            salt = bytes.fromhex(record["salt"])
            candidate = _hash_code(code, salt)
            if hmac.compare_digest(candidate, record["hash"]):
                return player_id
        return None

    def has_code(self, player_id: str) -> bool:
        """Return True if the player has a code set."""
        return player_id in self._read()

    def delete_code(self, player_id: str) -> None:
        """Delete a player's code, if any."""
        data = self._read()
        if player_id in data:
            del data[player_id]
            self._write(data)

    def _ensure_file_exists(self) -> None:
        """Ensure the storage file exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write({})

    def _read(self) -> dict:
        """Read data from the JSON file."""
        with open(self.file_path, encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        """Write data to the JSON file."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def generate_code() -> str:
    """Generate a random 8-character signup code from an unambiguous alphabet."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))


def _hash_code(code: str, salt: bytes) -> str:
    """Return the hex PBKDF2-HMAC-SHA256 hash of a code with the given salt."""
    return hashlib.pbkdf2_hmac("sha256", code.encode(), salt, _PBKDF2_ITERATIONS).hex()
