#!/bin/zsh
# Daily Blunder Trainer sync: analyze new Chess.com games, push updated drill bank.
# Pure python + stockfish — no Claude session needed.
set -e
cd /Users/beanhq/chess-dashboard

.venv/bin/python sync_trainer.py >> /tmp/trainer-sync.log 2>&1

if ! git diff --quiet data/trainer-drills.json 2>/dev/null || [ -n "$(git status --porcelain data/)" ]; then
  git add data/trainer-drills.json data/trainer-cache.json
  git commit -m "trainer sync $(date +%Y-%m-%d)" >> /tmp/trainer-sync.log 2>&1
  git push origin main >> /tmp/trainer-sync.log 2>&1
  echo "$(date): pushed new drill bank" >> /tmp/trainer-sync.log
else
  echo "$(date): no new games" >> /tmp/trainer-sync.log
fi
