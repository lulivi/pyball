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
"""Pydantic request/response models for the HTTP API."""

from pydantic import BaseModel


class GoalEventInput(BaseModel):
    """Pydantic model for a single goal event from the frontend."""

    scorer: str
    assistant: str | None
    team: str
    timestamp: str
    is_own_goal: bool = False


class FinalScore(BaseModel):
    """Pydantic model for the final score."""

    A: int
    B: int


class FinishMatchInput(BaseModel):
    """Pydantic model for the POST /api/match/finish request body."""

    meetup_date: str
    events: list[GoalEventInput]
    finalScore: FinalScore


class ParseCallupInput(BaseModel):
    """Request body for POST /api/meetup/parse-callup."""

    text: str


class MeetupDateInput(BaseModel):
    """Request body for POST /api/meetup/destroy-teams."""

    date: str


class AssignTeamsInput(BaseModel):
    """Request body for POST /api/meetup/assign-teams."""

    date: str
    team_a_ids: list[str]
    team_b_ids: list[str]
    team_c_ids: list[str] | None = None
    team_a_goalkeeper_id: str | None = None
    team_b_goalkeeper_id: str | None = None
    team_c_goalkeeper_id: str | None = None


class CreateMeetupInput(BaseModel):
    """Request body for POST /api/meetup/create."""

    date: str
    player_ids: list[str]


class MeetupCapacityInput(BaseModel):
    """Request body for POST /api/meetup/capacity."""

    date: str
    capacity: int


class GenerateTeamsInput(BaseModel):
    """Request body for POST /api/meetup/generate-teams."""

    date: str
    algorithm: str = "balanceado"
    team_count: int = 2


class CreatePlayerInput(BaseModel):
    """Request body for POST /api/players."""

    name: str
    group: str = "substitute"
    position: str | None = None


class EditPlayerInput(BaseModel):
    """Request body for POST /api/players/{id}/edit."""

    name: str
    group: str
    position: str | None = None


class UpdateMeetupDateInput(BaseModel):
    """Request body for POST /api/meetup/date."""

    old_date: str
    new_date: str


class UpdateMeetupLocationInput(BaseModel):
    """Request body for POST /api/meetup/location."""

    date: str
    location: str
