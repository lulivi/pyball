#!/usr/bin/env sh

tag=""
if ! tag=$(git describe --tags --abbrev=0 2>/dev/null); then
    echo "Warning: no git tags found, using 0.0.1.dev0" >&2
    echo "0.0.1.dev0"
    return
fi
tag_clean="${tag#v}"
commits=$(git rev-list "${tag}..HEAD" --count)

if [ "$commits" -eq 0 ]; then
    echo "$tag_clean"
else
    patch=$(echo "$tag_clean" | cut -d. -f3)
    prefix=$(echo "$tag_clean" | cut -d. -f1-2)
    echo "${prefix}.$((patch + 1)).dev${commits}"
fi
