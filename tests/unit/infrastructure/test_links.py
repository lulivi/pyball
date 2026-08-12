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
"""Tests for MatchLinkBuilder and SignupLinkBuilder."""

from pyball.infrastructure.http.links import MatchLinkBuilder, SignupLinkBuilder


def test_build_with_token():
    builder = MatchLinkBuilder("http://pyball:8000", match_token="tok-123")
    assert builder.build() == "http://pyball:8000/match?token=tok-123"


def test_build_without_token():
    builder = MatchLinkBuilder("http://pyball:8000")
    assert builder.build() == "http://pyball:8000/match"


def test_signup_build_with_token():
    builder = SignupLinkBuilder("http://pyball:8000", signup_token="tok-456")
    assert builder.build() == "http://pyball:8000/signup?token=tok-456"


def test_signup_build_without_token():
    builder = SignupLinkBuilder("http://pyball:8000")
    assert builder.build() == "http://pyball:8000/signup"
