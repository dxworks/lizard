#!/usr/bin/env bash
# Builds lizard-voyager.zip: only what Voyager runs (lizard.py and its code
# packages, at HEAD) plus the libraries listed in bundle-requirements.txt,
# all under one root folder (voyenv renames it). Tests, docs, website, dev
# tooling and lock files stay out. The allow-list below is explicit, so files
# upstream adds later stay out too.
# Usage: build-bundle.sh [output.zip]   (PYTHON=... to pick the interpreter)
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(git -C "$here" rev-parse --show-toplevel)"
out="${1:-$repo/lizard-voyager.zip}"
python="${PYTHON:-python3}"
work="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf "$work"' EXIT

# What Voyager needs at run time. git archive fails if a path is missing.
#   lizard.py + lizard_core/lizard_languages/lizard_ext  the analyser
#   instrument.yml, .ignore, results/                     the Voyager instrument
#   LICENSE.txt                                           lizard's MIT notice
#   instrument.v2.yml, lizard-summary.py, summary_*.py,
#   templates/summary.html                                the V2 manifest and the summary
ship=(lizard.py lizard_core lizard_languages lizard_ext
      instrument.yml .ignore results LICENSE.txt
      instrument.v2.yml lizard-summary.py summary_extract.py summary_render.py
      templates/summary.html)
git -C "$repo" archive --format=tar --prefix=lizard/ HEAD -- "${ship[@]}" \
    | tar -x -C "$work"
# On a release, the tool's version from the tag, in both manifests (V1 and V2)
if [[ "${GITHUB_REF_NAME:-}" == v*-voyager ]]; then
    version="${GITHUB_REF_NAME#v}"; version="${version%-voyager}"
    for f in "$work/lizard/instrument.yml" "$work/lizard/instrument.v2.yml"; do
        awk -v v="$version" '!/^version:/ {print} /^name:/ {print "version: " v}' "$f" > "$f.tmp"
        mv "$f.tmp" "$f"
    done
fi
# Documentation and example images inside the code packages are not used.
find "$work/lizard" -name '*.md' -type f -delete
rm -rf "$work/lizard/lizard_ext/images"

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
