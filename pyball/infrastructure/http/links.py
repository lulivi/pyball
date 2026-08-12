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
"""URL builders for web-facing links."""


class MatchLinkBuilder:
    """Build the public match-tracker URL for this instance."""

    def __init__(self, base_url: str, match_token: str = "") -> None:
        """Initialize with the instance base URL and optional match token."""
        self._base_url = base_url
        self._match_token = match_token

    def build(self) -> str:
        """Return the match URL, embedding the access token when configured."""
        if self._match_token:
            return f"{self._base_url}/match?token={self._match_token}"
        return f"{self._base_url}/match"


class SignupLinkBuilder:
    """Build the public signup-page URL for this instance."""

    def __init__(self, base_url: str, signup_token: str = "") -> None:
        """Initialize with the instance base URL and optional signup token."""
        self._base_url = base_url
        self._signup_token = signup_token

    def build(self) -> str:
        """Return the signup URL, embedding the access token when configured."""
        if self._signup_token:
            return f"{self._base_url}/signup?token={self._signup_token}"
        return f"{self._base_url}/signup"
