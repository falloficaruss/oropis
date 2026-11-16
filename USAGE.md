# agg — usage

Robotics and AI news desk for **Oropis**. It polls 50 curated sources (25 AI, 25
robotics) plus four Google News discovery queries, deduplicates the same story across
sources, scores it for Telegram alerts, and gives you a latest-first review queue, a
Telegram push feed, and a full drafting packet. It never posts to X — you draft and post
manually.

Run from anywhere. `-a` is normally `oropis`.

---

## Is it running?

```bash
agg -a oropis status
```

Healthy output looks like:

```
last poll: 41s ago   last run finished: 41s ago
items: 1840 total / 220 in 24h   clusters(24h): 91   sources: 54 enabled / 0 failing
```

The source table shows `Age` (age of the newest item), `State` (`ok` / `stale` /
`failing`), and the last error if any. `failing` means 3+ consecutive failures.

---

## Telegram news bot

The bot is a private push feed. It watches for new clusters, filters out low-signal
stories, and sends the rest to your Telegram chat. It runs as a systemd user service.

**One-time setup**

1. Create a bot with `@BotFather` and copy its token.
2. Send `/start` to your bot.
3. Get your chat ID from `@userinfobot`, or call `getUpdates` once.
4. Run the setup helper:

```bash
~/twitter/systemd/setup-telegram.sh
```

It prompts for the token and chat ID without echoing the token, writes
`~/.config/agg/telegram.env` with mode `600`, sends a test message, and enables
`agg-telegram@oropis.service`. Alternatively, copy
`systemd/telegram.env.example` to `~/.config/agg/telegram.env`, fill it in, and run
the test/enable commands below.

Do not put the token in `config.yaml` or commit it anywhere.

**Test and tune before enabling**

```bash
agg -a oropis bot --test
agg -a oropis bot --preview --since 24 --limit 20
agg -a oropis bot --status
```

`--preview` applies the same score/source filters without sending. Adjust
`telegram.min_score`, `telegram.instant_sources`, and
`telegram.discovery_only_sources` in `oropis/config.yaml` if it is too noisy or too
quiet.

**Start it automatically**

```bash
systemctl --user daemon-reload
systemctl --user enable --now agg-telegram@oropis.service
systemctl --user status agg-telegram@oropis.service
journalctl --user -u agg-telegram@oropis -f
```

`install.sh` and `setup-telegram.sh` also enable user lingering, so the bot starts
at boot without waiting for you to log in. Without lingering a user service only
runs while that user has a session open.

The bot sends one alert per new cluster. Official/lab sources in `instant_sources`
can alert from score `0.48`; other reporting sources need `0.60`. arXiv and Google
News are discovery-only and never trigger an alert on their own.

**Catch-up after downtime**

The bot remembers the last cluster it processed. When the machine is off, or the
service is stopped, the next start replays any qualifying clusters it missed
instead of discarding them. The freshness window (`telegram.max_age_h`, 12h by
default) is widened to cover the outage, capped by `poll.catchup_hours` (72h), so
long outages still produce catch-up alerts. Score thresholds and hourly/daily rate
limits apply as usual; if the limit is hit the bot resumes the catch-up on the next
poll. Look for `catch-up after ... offline` in the journal.

---

## The daily loop

```bash
agg -a oropis inbox --top 30
agg -a oropis inbox --beat Robotics
agg -a oropis show 143
agg -a oropis packet 143 --fetch-body > /tmp/packet.txt
```

`inbox` is the ranked review queue. `packet` includes the cluster summary, source
links, extracted numbers, beat tags, related coverage, and drafting angles. Use it
to write the story; do not copy source text wholesale.

Other useful commands:

```bash
agg -a oropis digest --since 12 --group beat     # catch-up, grouped by beat
agg -a oropis topics --diff                      # only NEW topics since last run
agg -a oropis stats --days 7                     # volume, dedup ratio, archetypes
agg -a oropis feeds check                        # probe every source
agg -a oropis feeds check --only ai_openai       # probe one source
```

---

## Editorial site

The Astro site source is `oropis/site-repo`. Published stories live in
`oropis/site-repo/src/content/news/` as Markdown, generated from `oropis/site.db`.

**One-time setup**

```bash
~/twitter/systemd/setup-site.sh
```

That writes `~/.config/agg/site.env` with mode `600`, enables the admin service and
the sync/deploy timers, and prints the SSH tunnel command.

**Admin**

```bash
ssh -L 8091:127.0.0.1:8091 user@this-machine
# then open http://127.0.0.1:8091/admin
```

From the admin you can review drafts, edit copy, set the beat (`AI` or `Robotics`),
choose an archetype/format, upload hero and inline images, and publish.

**CLI**

```bash
agg -a oropis site sync --since 72     # turn scored clusters into drafts
agg -a oropis site status
agg -a oropis site coverage            # published vs. weekly plan
agg -a oropis site publish ID
agg -a oropis site unpublish ID
agg -a oropis site export
agg -a oropis site deploy --dry-run
agg -a oropis site deploy --if-dirty
```

`site sync` only imports clusters tagged with a beat in `watchlist.beats`, so
off-topic clusters stay out of the editorial queue. Add a beat to
`watchlist.beats` and `beat_aliases` to widen the desk.

`site deploy` exports published stories, builds the Astro site, commits, and pushes
to `master`. It runs `git fetch` and `git reset --hard origin/master` first, so any
local site-code changes must be committed and pushed before the timer runs.

---

## Configuration

`oropis/config.yaml` contains:

- `sources`: 25 AI feeds, 25 robotics feeds, and 4 discovery-only Google News queries.
- `relevance`: the global AI/robotics gate plus exclusions.
- `watchlist`: beats, publishers, companies, hardware, and keywords.
- `beat_aliases`: alternate names for `AI` and `Robotics`.
- `telegram`: score thresholds, rate limits, age window, instant and discovery
  sources.
- `site`: branding, database, Astro repo, port, and weekly coverage targets.
- `voice`: tone, character limit, and banned hype words.

**Source options** vary by kind:

| Kind | Options |
| --- | --- |
| `rss` | `item_kind`, `limit`, optional `require_any` |
| `google_news` | `query`, `item_kind`, `limit`, optional `require_any` |
| `telegram` | `channel`, `limit`, optional `require_any` |
| `x` | `limit`, `max_age_h`, optional `require_any` |
| `web` | XPath selectors, `date_formats`, `url_base`, `item_kind` |

Broad feeds (`ai_nvidia`, `ai_microsoft_research`, `ai_amazon_science`,
`ai_databricks`, `ai_simon_willison`, `robotics_design_world`, and others) use per-source `require_any` so unrelated
posts do not enter the queue. Topical feeds use `skip_relevance: true` because the
feed itself is already scoped.

`telegram.discovery_only_sources` currently contains the four arXiv feeds and the
four Google News queries. They enrich clusters and provide corroboration but cannot
alert on their own.

The old esports/gaming and market source kinds (`liquipedia`, `steam_news`,
`steam_featured`, `cheapshark`, `edgar`, `bluesky`) have been removed from the
fetcher registry.

---

## Services

```bash
systemd/install.sh                 # install/enable oropis services
systemd/install.sh oropis          # explicit account
```

The deploy timer is intentionally left disabled by `install.sh` because `site deploy`
resets the Astro repo to `origin/master`. Commit and push site-repo changes first,
then enable it:

```bash
systemctl --user enable --now agg-site-deploy@oropis.timer
```

Services and timers:

| Unit | Purpose |
| --- | --- |
| `agg@oropis.service` | Feed polling and cluster scoring |
| `agg-telegram@oropis.service` | Telegram push bot |
| `agg-site@oropis.service` | Admin UI on `127.0.0.1:8091` |
| `agg-site-sync@oropis.timer` | Draft sync every 30 minutes |
| `agg-site-deploy@oropis.timer` | Export/build/deploy every 5 minutes (disabled until site changes are pushed) |
| `agg-digest@oropis.timer` | Optional daily digest (not enabled by default) |

Common checks:

```bash
systemctl --user status agg@oropis agg-telegram@oropis
systemctl --user restart agg@oropis agg-telegram@oropis
journalctl --user -u agg@oropis -u agg-telegram@oropis -f
systemctl --user status agg-site@oropis
systemctl --user restart agg-site@oropis
systemctl --user list-timers --all 'agg*'
```

The daily digest, when enabled, writes to `oropis/digests/YYYY-MM-DD.md`.

---

## Troubleshooting

- **No alerts:** run `agg -a oropis bot --preview --since 6 --limit 30`. If the
  queue is empty, check `agg -a oropis status` for failing sources.
- **Too many alerts:** raise `telegram.min_score` or `max_per_hour` in
  `oropis/config.yaml`.
- **A source is failing:** run `agg -a oropis feeds check --only NAME`. Some
  corporate IR feeds block cloud IPs; replace them with an official RSS feed or a
  Google News query rather than retrying indefinitely.
- **No new clusters after a source change:** run `agg -a oropis fetch` and
  check `last poll` in `status`.
- **Admin login fails:** confirm `~/.config/agg/site.env` exists and the service
  was restarted after writing it.
- **Deploy overwrote local site edits:** expected; `site deploy` resets the repo to
  `origin/master`. Commit and push site-code changes first.
