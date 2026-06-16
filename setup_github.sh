#!/usr/bin/env bash
# One-time setup: creates the GitHub repo, pushes the site, sets the API secret, enables Pages.
# Requirements: git + GitHub CLI (gh). Install gh: https://cli.github.com  (mac: brew install gh)
set -e
cd "$(dirname "$0")"
REPO="${1:-quiniela-2026}"

command -v gh >/dev/null || { echo "GitHub CLI 'gh' not installed. Run: brew install gh"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Not logged in. Run: gh auth login"; exit 1; }

rm -rf scripts/__pycache__ 2>/dev/null || true

echo "Enter your football-data.org API token (free at https://www.football-data.org/client/register):"
read -r -s TOKEN; echo

# init + commit
[ -d .git ] || git init -q
git add .
git commit -q -m "Quiniela Mundial 2026 — auto-updating tracker" || echo "(nothing new to commit)"
git branch -M main

# create repo (public) and push
gh repo create "$REPO" --public --source=. --remote=origin --push

OWNER=$(gh api user -q .login)

# set secret for the Action
printf '%s' "$TOKEN" | gh secret set FOOTBALL_DATA_TOKEN --repo "$OWNER/$REPO"

# enable GitHub Pages on main / root
gh api -X POST "repos/$OWNER/$REPO/pages" -f "source[branch]=main" -f "source[path]=/" >/dev/null 2>&1 \
  || echo "NOTE: enable Pages manually in Settings → Pages → main / (root) if the line above errored."

# kick off the first results fetch now
gh workflow run "Update results" --repo "$OWNER/$REPO" >/dev/null 2>&1 || true

echo
echo "Done. Your public tracker URL (live in ~1 min):"
echo "   https://$OWNER.github.io/$REPO/"
echo "Share that link on WhatsApp. It updates itself every 2 hours."
