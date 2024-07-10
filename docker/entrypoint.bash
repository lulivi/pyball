#!/usr/bin/env bash

if [ -z "$PYBALL_COMPONENT" ]; then
    printf 'The executing component is necessary. Please, set $PYBALL_COMPONENT.\n' >&2
    exit 1
fi

command="pyball"
if [ "$PYBALL_COMPONENT" = "bot" ]; then
    command="pyballbot"
fi

$command
exit "$?"
