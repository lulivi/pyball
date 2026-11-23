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

"""Tests for the tracked messages and the Telegram links, in the bot's file formats."""

import json

from pyball_telegram.state import LinkStore, MessageStore, TrackedMessage
from tests.conftest import DATE


def test_messages_keep_the_bots_format(tmp_path):
    """A messages.json written by the core's bot reads back; renames move both chats."""
    path = tmp_path / "messages.json"
    path.write_text(
        json.dumps(
            {"2026-11-25T20:00": {"regular": {"chat_id": -1, "thread_id": 5, "message_id": 9}}}
        )
    )
    store = MessageStore(path)
    assert store.get(DATE, "regular") == TrackedMessage(-1, 9, 5)

    store.save(DATE, "substitute", TrackedMessage(-2, 10))
    store.rename_date(DATE, DATE.replace(day=26))
    assert store.get(DATE, "regular") is None
    assert store.get(DATE.replace(day=26), "substitute") == TrackedMessage(-2, 10)

    store.delete(DATE.replace(day=26), "regular")
    store.delete(DATE.replace(day=26), "substitute")
    assert json.loads(path.read_text()) == {}


def test_links_round_trip(tmp_path):
    """Link, look up both ways, unlink; a missing file has no links."""
    links = LinkStore(tmp_path / "telegram-uuid.json")
    assert links.player_id(7) is None
    links.link(7, "p1")
    assert links.player_id(7) == "p1"
    assert links.telegram_id("p1") == 7
    links.unlink(7)
    assert links.telegram_id("p1") is None
