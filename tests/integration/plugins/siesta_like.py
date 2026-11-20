"""A plugin that only uses /api/v1: the weekly draw siesta runs, against real capacity.

Writes "done" to the file named by argv[1] when the draw is over.
"""

import json
import os
import sys
import urllib.request

API = os.environ["PYBALL_API_URL"]
HEADERS = {
    "Authorization": f"Bearer {os.environ['PYBALL_API_TOKEN']}",
    "Content-Type": "application/json",
}


def call(method, path, body=None):
    """Call the plugin API and return the decoded JSON body."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(API + path, data=data, method=method, headers=HEADERS)
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


meetup = call("GET", "/meetups/active")
if len(meetup["players"]) > meetup["capacity"]:
    lineup = meetup["players"][: meetup["capacity"]]
    call("PUT", f"/meetups/{meetup['id']}/lineup", {"players": lineup, "team_algorithm": "random"})
elif len(meetup["players"]) < meetup["capacity"]:
    call("POST", f"/meetups/{meetup['id']}/substitute-search")
with open(sys.argv[1], "w", encoding="utf-8") as f:
    f.write("done")
