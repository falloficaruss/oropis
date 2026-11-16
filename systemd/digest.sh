#!/bin/sh
set -eu

ACCOUNT="${1:?usage: digest.sh <oropis>}"
ROOT="${HOME}/twitter"
OUT="${ROOT}/${ACCOUNT}/digests"
PY="${ROOT}/.venv/bin/python"
CFG="${ROOT}/${ACCOUNT}"

mkdir -p "${OUT}"

{
    printf '# %s digest %s\n\n' "${ACCOUNT}" "$(date +%F)"
    "${PY}" -m agg -a "${CFG}" digest --since 12 --cap 45 --group beat
    printf '\n\n'
    "${PY}" -m agg -a "${CFG}" topics --since 24 --limit 15
} > "${OUT}/$(date +%F).md" 2>&1

printf 'wrote %s\n' "${OUT}/$(date +%F).md"
