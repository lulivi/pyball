# Copyright (c) 2024 Luis Liñán
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

import uuid


class PlayerIdNotFoundError(Exception):
    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"There is no player with the id `{id}` in the match"
        super().__init__(self.message)


class PlayerIdNotInGoalError(Exception):
    def __init__(self) -> None:
        self.message = f"The scorer ID was not found in the goal"
        super().__init__(self.message)


class TeamNotInGoalError(Exception):
    def __init__(self) -> None:
        self.message = f"The team was not found in the goal"
        super().__init__(self.message)


class AssistantIsRivalError(Exception):
    def __init__(self, player_id: uuid.UUID, assistant_id: uuid.UUID) -> None:
        self.player_id = player_id
        self.assistant_id = assistant_id
        self.message = (
            f"The assistant player with the id `{assistant_id}` is rival of id `{player_id}`"
        )
        super().__init__(self.message)


class OwnGoalWithAssistError(Exception):
    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"Goal with player id `{id}` has assistant and it's an own goal"
        super().__init__(self.message)


class MatchAlreadyExistsError(Exception):
    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"There is already a match with the id `{id}`"
        super().__init__(self.message)
