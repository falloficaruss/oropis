#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACCOUNT="${1:-oropis}"
DEST="${HOME}/.config/systemd/user"
mkdir -p "$DEST" "${HOME}/.config/agg"
if [[ ! -f "${HOME}/.config/agg/telegram.env.example" ]]; then
    install -m 0600 "${HERE}/telegram.env.example" "${HOME}/.config/agg/telegram.env.example"
fi
if [[ ! -f "${HOME}/.config/agg/site.env.example" ]]; then
    install -m 0600 "${HERE}/site.env.example" "${HOME}/.config/agg/site.env.example"
fi

chmod +x "${HERE}/digest.sh" "${HERE}/setup-telegram.sh" "${HERE}/setup-site.sh"
install -m 0644 "${HERE}/agg@.service" "${DEST}/agg@.service"
install -m 0644 "${HERE}/agg-digest@.service" "${DEST}/agg-digest@.service"
install -m 0644 "${HERE}/agg-digest@.timer" "${DEST}/agg-digest@.timer"
install -m 0644 "${HERE}/agg-telegram@.service" "${DEST}/agg-telegram@.service"
install -m 0644 "${HERE}/agg-site@.service" "${DEST}/agg-site@.service"
install -m 0644 "${HERE}/agg-site-sync@.service" "${DEST}/agg-site-sync@.service"
install -m 0644 "${HERE}/agg-site-sync@.timer" "${DEST}/agg-site-sync@.timer"
install -m 0644 "${HERE}/agg-site-deploy@.service" "${DEST}/agg-site-deploy@.service"
install -m 0644 "${HERE}/agg-site-deploy@.timer" "${DEST}/agg-site-deploy@.timer"

systemctl --user daemon-reload

if command -v loginctl >/dev/null 2>&1; then
    if [[ "$(loginctl show-user "${USER}" -p Linger 2>/dev/null || true)" != "Linger=yes" ]]; then
        loginctl enable-linger "${USER}" >/dev/null 2>&1 || \
            echo "Could not enable linger. Run: sudo loginctl enable-linger ${USER}"
    fi
fi

systemctl --user enable --now agg@${ACCOUNT}.service

if [[ -f "${HOME}/.config/agg/telegram.env" ]]; then
    systemctl --user enable agg-telegram@${ACCOUNT}.service
    systemctl --user restart agg-telegram@${ACCOUNT}.service
else
    echo "Telegram env not found; skipping bot service."
    echo "Create ${HOME}/.config/agg/telegram.env, then run:"
    echo "  systemctl --user enable --now agg-telegram@${ACCOUNT}.service"
fi

if [[ -f "${HOME}/.config/agg/site.env" ]]; then
    systemctl --user enable --now agg-site@${ACCOUNT}.service
    systemctl --user enable --now agg-site-sync@${ACCOUNT}.timer
    if [[ "${AGG_ENABLE_DEPLOY:-0}" == "1" ]]; then
        systemctl --user enable --now agg-site-deploy@${ACCOUNT}.timer
    else
        echo "Deploy timer left disabled. Commit and push site-repo changes first, then run:"
        echo "  systemctl --user enable --now agg-site-deploy@${ACCOUNT}.timer"
    fi
else
    echo "Site env not found; skipping site services."
    echo "Create ${HOME}/.config/agg/site.env from systemd/site.env.example, then run:"
    echo "  systemctl --user enable --now agg-site@${ACCOUNT}.service"
    echo "  systemctl --user enable --now agg-site-sync@${ACCOUNT}.timer"
    echo "  systemctl --user enable --now agg-site-deploy@${ACCOUNT}.timer"
fi

echo
systemctl --user --no-pager status agg@${ACCOUNT}.service || true
echo
systemctl --user list-timers --all 'agg*' || true
