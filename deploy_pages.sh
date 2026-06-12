#!/bin/zsh
# Build dist/ and deploy to Cloudflare Pages (direct upload).
# Uses expect because `wrangler pages deploy` requires a TTY for OAuth auth.
set -e
cd /Users/beanhq/chess-dashboard

rm -rf dist && mkdir -p dist
cp index.html trainer.html manifest.json dist/
cp -R icons dist/icons
mkdir -p dist/data
cp data/*.json dist/data/ 2>/dev/null || true

expect << 'EXP'
set timeout 240
spawn npx wrangler pages deploy dist --project-name=chess-trainer --commit-dirty=true
expect {
    -re {\(Y/n\)} { send "n\r"; exp_continue }
    -re {Deployment complete} { }
    timeout { puts "DEPLOY TIMEOUT"; exit 1 }
    eof { }
}
EXP
