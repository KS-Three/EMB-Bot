#!/usr/bin/env bash
# Lane cleanup for EMB-Bot, Kent's ruling 2026-10-23: remove CLEAN lanes whose HEAD is on origin.
# usage:  bash lane_cleanup.sh          -> dry run, prints REMOVE / KEEP per lane
#         bash lane_cleanup.sh --go     -> removes the REMOVE lanes with `git worktree remove`
REPO="C:/Users/EE-LT-11030/Claude Personal/EMB-Bot"
cd "$REPO" || exit 1
GO=0; [ "$1" = "--go" ] && GO=1
git fetch -q --all --prune
git worktree list --porcelain | awk '/^worktree /{print substr($0,10)}' | while read -r wt; do
  case "$wt" in *"/.claude/worktrees/"*) ;; *) continue;; esac
  name="${wt##*/}"
  if [ ! -d "$wt" ]; then echo "PRUNE  $name (folder gone)"; continue; fi
  if [ -n "$(git -C "$wt" status --porcelain --untracked-files=no 2>/dev/null)" ]; then echo "KEEP   $name  dirty"; continue; fi
  head=$(git -C "$wt" rev-parse HEAD 2>/dev/null) || { echo "KEEP   $name  unreadable"; continue; }
  if ! git branch -r --contains "$head" 2>/dev/null | grep -q .; then echo "KEEP   $name  HEAD $head not on origin"; continue; fi
  # a lane a live session is working in has a fresh index/lock or recent writes: skip anything touched in the last 2 hours
  if find "$wt" -maxdepth 2 -newermt "-2 hours" -not -path "*/.git/*" 2>/dev/null | grep -q .; then echo "KEEP   $name  touched in the last 2 h"; continue; fi
  sz=$(du -sm "$wt" 2>/dev/null | cut -f1)
  if [ $GO = 1 ]; then
    git worktree remove --force "$wt" && echo "REMOVED $name  ${sz} MB" || echo "FAILED  $name"
  else
    echo "REMOVE $name  ${sz} MB  (HEAD on origin, clean, idle)"
  fi
done
[ $GO = 1 ] && git worktree prune
df -h /c | tail -1
