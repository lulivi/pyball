# Copyright (c) 2022 Luis Liñán
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

"""Error, error!"""


class PyBallError(Exception):
    """Base error for PyBall bot."""


class NotAdminError(PyBallError):
    """The user is not in the admin list."""


class NoCallUpError(PyBallError):
    """There is no created call-up."""


class ExpectedMessageIdError(PyBallError):
    """When the message identifier is not the expected one."""


class PlayerAlreadyCalledUpError(PyBallError):
    """The player is already in the call-up."""


class PlayerNotCalledUpError(PyBallError):
    """The player hasn't been called-up."""


class PlayerParsingError(PyBallError):
    """The player name was not found in the message."""


class CommandArgumentError(PyBallError):
    """The argument was not specified."""

    def __init__(self, command_name: str, argument_name: str, argument_example: str) -> None:
        self._command_name: str = command_name
        self._argument_name: str = argument_name
        self._argument_example: str = argument_example

    def __str__(self) -> str:
        return (
            f"Por favor, indica el {self._argument_name} a continuación del comando:"
            f" /{self._command_name} <{self._argument_name}>. Por"
            f" ejemplo:\n\n\t/{self._command_name} {self._argument_example}"
        )
