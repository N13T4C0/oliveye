#!/usr/bin/env bash
# Commit and push everything new in the results worktree. Used after every job and by the
# safety-net step. A failed push is retried after a clean rebase; a rebase that cannot be
# completed is aborted so the worktree is never left half-rebased.
set -u
dir=${RESULTS_DIR:-results-branch}
message=${1:-results}

# Identity for commit AND for rebase (a rebase rewrites commits and needs a committer too).
git -C "$dir" config user.name "github-actions[bot]"
git -C "$dir" config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git -C "$dir" add -A
if git -C "$dir" diff --cached --quiet; then
  exit 0
fi
git -C "$dir" commit -q -m "$message"

for attempt in 1 2 3 4 5; do
  if git -C "$dir" push -q origin results; then
    exit 0
  fi
  sleep $((attempt * 10))
  if ! git -C "$dir" pull -q --rebase origin results; then
    git -C "$dir" rebase --abort 2>/dev/null || true
  fi
done
echo "::error::Could not push results after 5 attempts"
exit 1
