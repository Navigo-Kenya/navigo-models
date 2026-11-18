#!/usr/bin/env bash
# Build the navigation models (.glb) into the app (previews and specs into out/).
#
#   ./build.sh                          # every model, into ../app/assets/models
#   ./build.sh matatu bus               # some
#   OUT=../mobile/assets/models ./build.sh
#   RENDER=0 ./build.sh                 # skip the preview renders (faster)
#
# Needs the navigo-blender image: docker build -t navigo-blender .
set -euo pipefail
cd "$(dirname "$0")"

IMAGE="${IMAGE:-navigo-blender}"
OUT_DIR="${OUT:-../app/assets/models}"
mkdir -p "$OUT_DIR" out
HERE="$(pwd)"
OUT_ABS="$(cd "$OUT_DIR" && pwd)"
# Docker on Windows (Git Bash) wants C:/… paths and no MSYS path rewriting.
if command -v cygpath >/dev/null 2>&1; then
  HERE="$(cygpath -m "$HERE")"; OUT_ABS="$(cygpath -m "$OUT_ABS")"; export MSYS_NO_PATHCONV=1
fi

ALL=(matatu bus car boda bicycle train_sgr_loco train_sgr_coach train_commuter ferry plane puck)
MODELS=("$@")
[ ${#MODELS[@]} -eq 0 ] && MODELS=("${ALL[@]}")
EXTRA=()
[ "${RENDER:-1}" = "0" ] && EXTRA+=(--no-render)

for m in "${MODELS[@]}"; do
  docker run --rm -v "${HERE}:/work" -v "${OUT_ABS}:/out" -w /work "$IMAGE" \
    -P "models/${m}.py" -- --out /out --previews /work/out "${EXTRA[@]}" 2>&1 \
    | grep -E "^\[${m}\]|Error|Traceback|WARNING" || true
done
