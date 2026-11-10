#!/usr/bin/env bash
# Builds lizard-voyager.zip: lizard's source at HEAD plus the libraries listed
# in bundle-requirements.txt, all under one root folder (voyenv renames it).
# Usage: build-bundle.sh [output.zip]   (PYTHON=... to pick the interpreter)
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(git -C "$here" rev-parse --show-toplevel)"
out="${1:-$repo/lizard-voyager.zip}"
python="${PYTHON:-python3}"
work="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf "$work"' EXIT

git -C "$repo" archive --format=tar --prefix=lizard/ HEAD | tar -x -C "$work"

# Wheels only, pinned by hash. Library packages land next to lizard.py, which
# Python puts on sys.path when it runs the script. Their *.dist-info folders
# keep the license texts and let scanners see the versions.
"$python" -m pip install --quiet --disable-pip-version-check --no-deps \
    --only-binary=:all: --require-hashes \
    --target "$work/lizard" -r "$here/bundle-requirements.txt"
rm -rf "$work/lizard/bin"  # console scripts (pygmentize) are not needed

# Smoke test with no site-packages at all (-S): only the bundled copy counts.
mkdir "$work/smoke"
printf 'hello(Name) ->\n    case Name of\n        [] -> none;\n        _ -> Name\n    end.\n' > "$work/smoke/smoke.erl"
pygments_file="$(cd "$work/lizard" && "$python" -S -c 'import sys; sys.path.insert(0, ""); import pygments; print(pygments.__file__)')"
case "$pygments_file" in
    "$work/lizard/"*|pygments/*) ;;
    *) echo "Pygments was not loaded from the bundle: $pygments_file" >&2; exit 1 ;;
esac
(cd "$work/lizard" && "$python" -S lizard.py --csv "$work/smoke" 2>/dev/null) | grep -q '"hello"' || {
    echo "Smoke test failed: lizard did not report the Erlang function" >&2; exit 1; }

rm -rf "$work/smoke" "$out"
(cd "$work" && zip -qrX "$out" lizard)
echo "Built $out"
