from core.pyball.match.domain.matches import Matches
from core.pyball.settings import DATA_DIRECTORY_PATH


class MatchJsonRepository(Matches):
    def __init__(self) -> None:
        self._json_file = DATA_DIRECTORY_PATH.joinpath("matches.json")
        if not self._json_file.exists():
            self._json_file.write_text("[]")

    # Finish
