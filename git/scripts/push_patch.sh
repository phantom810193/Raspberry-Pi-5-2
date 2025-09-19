#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/phantom810193/Raspberry-Pi-5-2.git}"
BRANCH="${BRANCH:-main}"

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "ERROR: GITHUB_TOKEN is not set. Please add it in Codex Secrets or export it before running."
  exit 1
fi

if [ ! -d ".git" ]; then
  echo "Cloning repository..."
  git clone "$REPO_URL" repo_workdir
  cd repo_workdir
else
  echo "Found existing git repo. Using current directory."
fi

echo "Unpacking patch..."
unzip -o /mnt/data/repo_patch_v2.zip -d .

echo "Configuring git identity (override via GIT_NAME / GIT_EMAIL envs if needed)..."
git config user.name  "${GIT_NAME:-codex-bot}"
git config user.email "${GIT_EMAIL:-codex-bot@example.com}"

echo "Setting remote with token..."
git remote set-url origin "https://${GITHUB_TOKEN}@${REPO_URL#https://}"

echo "Committing changes..."
git add -A
git commit -m "Apply CI workflows, tests, docs, README, and tooling (patch v2)" || echo "Nothing to commit."

echo "Pushing to ${BRANCH}..."
git push origin HEAD:"${BRANCH}"

echo "Done. Check GitHub Actions → workflows should start automatically."
