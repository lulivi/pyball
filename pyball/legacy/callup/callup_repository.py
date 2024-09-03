import datetime
import json

from typing import List, Optional

from pyball.legacy.callup.callup import CallUp
from pyball.settings import DATA_DIRECTORY_PATH


class CallUpRepository:
    def __init__(self) -> None:
        self._json_file = DATA_DIRECTORY_PATH.joinpath("call_up.json")
        if not self._json_file.exists():
            self._json_file.write_text("[]")

    def save(self, call_up: CallUp) -> None:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())
        date_time_str = call_up.date_time.isoformat()

        for saved_call_up in saved_file_contents:
            if date_time_str == saved_call_up["date_time"]:
                saved_file_contents.remove(saved_call_up)
                break

        saved_file_contents.append(vars(call_up))
        self._json_file.write_text(json.dumps(saved_file_contents, indent=4))

    def get(self, date_time: datetime.datetime) -> Optional[CallUp]:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())
        date_time_str = date_time.isoformat()

        for saved_call_up in saved_file_contents:
            if date_time_str == saved_call_up["date_time"]:
                return CallUp.from_dict(saved_call_up)

        return None
