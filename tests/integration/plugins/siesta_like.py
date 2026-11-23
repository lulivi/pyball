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
