#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV="${HOME}/.config/agg/site.env"
PY="${HOME}/twitter/.venv/bin/python"
UNIT_DIR="${HOME}/.config/systemd/user"

mkdir -p "$(dirname "$ENV")" "$UNIT_DIR"
for unit in agg-site@.service agg-site-sync@.service agg-site-sync@.timer \
    agg-site-deploy@.service agg-site-deploy@.timer; do
    if [[ ! -f "${UNIT_DIR}/${unit}" ]]; then
        install -m 0644 "${HERE}/${unit}" "${UNIT_DIR}/${unit}"
    fi
done

if [[ -f "$ENV" ]]; then
    read -rp "Overwrite ${ENV}? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || exit 1
fi

read -rp "Admin username [oropis]: " USERNAME
USERNAME="${USERNAME:-oropis}"

read -rsp "Admin password (12+ chars): " PASSWORD
echo
if [[ ${#PASSWORD} -lt 12 ]]; then
    echo "password must be at least 12 characters" >&2
    exit 1
fi

read -rsp "Confirm password: " CONFIRM
echo
if [[ "$PASSWORD" != "$CONFIRM" ]]; then
    echo "passwords do not match" >&2
    exit 1
fi

SECRET="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(32))')"

umask 077
printf 'SITE_ADMIN_USER=%s\nSITE_ADMIN_PASSWORD=%s\nSITE_SECRET_KEY=%s\n' \
    "$USERNAME" "$PASSWORD" "$SECRET" > "$ENV"
chmod 600 "$ENV"

echo "Wrote ${ENV} (mode 600)."
echo "Admin credentials are required in the environment, not in config.yaml."

systemctl --user daemon-reload
systemctl --user enable agg-site@oropis.service
systemctl --user enable --now agg-site-sync@oropis.timer
systemctl --user restart agg-site@oropis.service
echo
echo "Deploy timer left disabled. Commit and push site-repo changes first, then run:"
echo "  systemctl --user enable --now agg-site-deploy@oropis.timer"

echo
systemctl --user --no-pager status agg-site@oropis.service || true
echo
echo "Admin: http://127.0.0.1:8091/admin"
echo "Tunnel from your laptop: ssh -L 8091:127.0.0.1:8091 user@this-machine"
