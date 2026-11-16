#!/usr/bin/env bash
set -euo pipefail

ENV="${HOME}/.config/agg/telegram.env"
PY="${HOME}/twitter/.venv/bin/python"
ACCOUNT="${HOME}/twitter/oropis"

mkdir -p "$(dirname "$ENV")"

if [[ -f "$ENV" ]]; then
    read -rp "Overwrite ${ENV}? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || exit 1
fi

read -rsp "Telegram bot token: " TOKEN
echo
read -rp "Telegram chat ID: " CHAT

if [[ -z "$TOKEN" || -z "$CHAT" ]]; then
    echo "token and chat ID are required" >&2
    exit 1
fi

echo "Sending test message..."
TELEGRAM_BOT_TOKEN="$TOKEN" TELEGRAM_CHAT_ID="$CHAT" \
    "$PY" -m agg -a "$ACCOUNT" bot --test

umask 077
printf 'TELEGRAM_BOT_TOKEN=%s\nTELEGRAM_CHAT_ID=%s\n' "$TOKEN" "$CHAT" > "$ENV"
chmod 600 "$ENV"

systemctl --user daemon-reload

if command -v loginctl >/dev/null 2>&1; then
    if [[ "$(loginctl show-user "${USER}" -p Linger 2>/dev/null || true)" != "Linger=yes" ]]; then
        loginctl enable-linger "${USER}" >/dev/null 2>&1 || \
            echo "Could not enable linger. Run: sudo loginctl enable-linger ${USER}"
    fi
fi

systemctl --user enable agg-telegram@oropis.service
systemctl --user restart agg-telegram@oropis.service
systemctl --user --no-pager status agg-telegram@oropis.service
