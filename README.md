# Chess Dashboard

Visual chess practice dashboard for Ophir's path from rapid 937 → 1500 by EOY 2026, anchored in Levy Rozman's *How to Win at Chess*.

**Live**: https://ophirram8.github.io/chess-dashboard/

## What it shows

Pure read-only visual dashboard — Hermes is the coach, this is the mirror. No buttons, no logging, no localStorage.

10 sections:
1. **Goal banner** — current rapid → 1500 target with progress bar + days remaining
2. **ELO trend** — line chart of rapid + puzzle ratings over time
3. **This week** — current Cycle 1 theme + drill link
4. **Featured pattern** — board image of this week's tactical pattern
5. **Cycle calendar** — 8-week strip with current week highlighted
6. **Recent games** — last 3 games with worst-move boards
7. **Weakness zones** — Stockfish-validated mistake zones (move ranges)
8. **Pattern gallery** — Levy's curated tactical positions, filterable by theme
9. **Openings library** — Levy's recommended sub-1500 repertoire + reference openings, filterable
10. **Quick links** — to Notion, Chess.com, Lichess, this week's puzzles

## Architecture

```
[Mac mini]
  ├── ~/.hermes/state/chess_*.json (Hermes state, updated by existing crons)
  ├── ~/chess-dashboard/data/openings.json (curated openings library)
  ├── ~/chess-dashboard/data/elo_history.json (appended daily)
  └── ~/scripts/chess_dashboard_data.py (pulls everything, writes data.json)
              │
              ▼ (Hermes cron at 23:30 daily)
       commits + pushes to GitHub
              │
              ▼
[GitHub Pages: chess-dashboard repo]
  - index.html (single-file dashboard)
  - data.json (regenerated daily)
              │
              ▼
   chess-dashboard.pages.dev (this site)
```

Data sources:
- **Hermes state files** (`~/.hermes/state/`): chess_week.json, chess_today.json, chess_pattern_positions.json
- **Chess.com API** (public): current rapid + puzzle ratings
- **Lichess API** (public): current puzzle rating
- **Local curation**: openings.json + chess_pattern_positions.json (FENs verified by hand)

No Notion API integration needed — Hermes state files + public game-site APIs are the source of truth.

## Tech

Single-file HTML/CSS/JS. No build, no backend, no dependencies. Lichess board image API for all chess visuals. SVG-based ELO chart. Mobile-first responsive.

## Updating

The dashboard auto-syncs at 23:30 daily via a Hermes cron that runs `chess_dashboard_data.py` then commits + pushes. To update manually:

```bash
~/scripts/chess_dashboard_data.py
cd ~/chess-dashboard
git add data.json data/elo_history.json
git commit -m "data sync $(date +%Y-%m-%d)"
git push
```

## Curated content

- **Tactical positions**: `~/.hermes/state/chess_pattern_positions.json` — 16 positions across all 8 Cycle 1 themes (2 per theme). Add more as you verify FENs.
- **Openings library**: `~/chess-dashboard/data/openings.json` — 12 openings, 6 marked as Levy's picks for sub-1500.
