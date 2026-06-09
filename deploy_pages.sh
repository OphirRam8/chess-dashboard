#!/bin/zsh
# Build dist/ and deploy to Cloudflare Pages (direct upload).
# Requires: npx wrangler login (once) and the KV namespace id in wrangler.toml.
set -e
cd /Users/beanhq/chess-dashboard

rm -rf dist && mkdir -p dist
cp index.html trainer.html manifest.json dist/
cp -R icons dist/icons
mkdir -p dist/data
cp data/*.json dist/data/ 2>/dev/null || true

npx -y wrangler pages deploy dist --project-name=chess-trainer --commit-dirty=true
