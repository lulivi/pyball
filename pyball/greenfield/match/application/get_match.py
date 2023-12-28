# Copyright (c) 2023 Luis Liñán
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

"""Get an existing match use case."""

import datetime
import uuid

from pyball.greenfield.match.application.errors import MatchDateNotFound, MatchIdNotFound
from pyball.greenfield.match.domain.matches import Matches
from pyball.greenfield.match.domain.model.match import Match


class GetMatch:
    def __init__(self, match_repository: Matches) -> None:
        self._matches = match_repository

    def by_id(self, id: uuid.UUID) -> Match:
        match = self._matches.get(id=id)

        if match is None:
            raise MatchIdNotFound(id=id)

        return match

    def by_date(self, date_time: datetime.datetime) -> Match:
        match = self._matches.get_by_date(date_time=date_time)

        if match is None:
            raise MatchDateNotFound(date_time=date_time)

        return match
