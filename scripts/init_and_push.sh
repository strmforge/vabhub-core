#!/usr/bin/env bash
set -euo pipefail
REPO_NAME="$(basename "$PWD")"
: "${ORG:=strmforge}"
: "${DEFAULT_BRANCH:=main}"
REMOTE="git@github.com:${ORG}/${REPO_NAME}.git"
if [ ! -d .git ]; then git init && git checkout -b "$DEFAULT_BRANCH"; fi
# basic identity fallback
if ! git config user.name >/dev/null; then git config user.name "${GIT_USER_NAME:-${ORG}}"; fi
if ! git config user.email >/dev/null; then git config user.email "${GIT_USER_EMAIL:-noreply@users.noreply.github.com}"; fi
git add -A
git commit -m "chore(${REPO_NAME}): bootstrap repo with templates" || true
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE"
git push -u origin "$DEFAULT_BRANCH"
echo "Pushed to $REMOTE"
