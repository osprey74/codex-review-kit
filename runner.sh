#!/usr/bin/env bash
# Codex レビューの依頼一覧を上から順に流す（開発用）。
# 置き場所：各プロジェクトの .claude/codex/ に写して使う。
#
# 使い方（Git Bash、リポジトリのどこからでも）:
#   bash .claude/codex/runner.sh [queue] [wait]
#     queue : 依頼一覧（省略時 .claude/codex/queue.txt）。各行 "ID|依頼文"。# で始まる行は飛ばす
#     wait  : 指定すると、使用量の上限に当たったとき再開時刻まで待って続ける。
#             省略すると、再開時刻を表示して終了する（検証を挟むための区切り）。
#
# $OUTDIR/ID_*.md が既にある依頼は済みとして飛ばす（OUTDIR の既定は .claude/codex/reports）。途中で止まっても、再実行すれば残りから続く。
# Codex は読み取り専用（-s read-only）で動き、報告は CLI が -o で保存する。
# ログは .claude/codex/logs/ に残る。

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT" || exit 1
Q="${1:-$HERE/queue.txt}"; MODE="$2"
LOGDIR="$HERE/logs"; mkdir -p "$LOGDIR"
OUTDIR="${OUTDIR:-.claude/codex/reports}"; mkdir -p "$OUTDIR"
ROOT_WIN="$(cygpath -w "$ROOT" 2>/dev/null || echo "$ROOT")"

C=$(ls -t /c/Users/*/.vscode/extensions/openai.chatgpt-*/bin/windows-x86_64/codex.exe 2>/dev/null | head -1)
[ -z "$C" ] && C=$(command -v codex)
[ -z "$C" ] && { echo "codex.exe が見つからない"; exit 1; }

wait_until() { # 引数 "2:52 PM"。その2分後まで待つ
  local t="$1" h m ap; h=${t%%:*}; m=${t#*:}; m=${m%% *}; ap=${t##* }
  h=$((10#$h)); [ "$ap" = PM ] && [ $h -ne 12 ] && h=$((h+12)); [ "$ap" = AM ] && [ $h -eq 12 ] && h=0
  local target=$((h*60+10#$m+2))
  echo "  wait until $(printf %02d:%02d $((target/60%24)) $((target%60)))"
  while :; do now=$((10#$(date +%H)*60+10#$(date +%M))); [ $now -ge $target ] && [ $((now-target)) -lt 600 ] && break; sleep 60; done
}

while IFS='|' read -r ID PROMPT; do
  [ -z "$ID" ] && continue; case "$ID" in \#*) continue;; esac
  ls "$OUTDIR"/${ID}_*.md >/dev/null 2>&1 && { echo "skip $ID"; continue; }
  while :; do
    OUT="$OUTDIR/${ID}_$(date +%F).md"; LOG="$LOGDIR/${ID}.log"
    echo "== $ID start $(date '+%F %T')"
    # < /dev/null が要る。無いと codex が標準入力を読み、一覧の残りの行を飲み込む
    "$C" exec -C "$ROOT_WIN" -s read-only -o "$OUT" "$PROMPT" < /dev/null > "$LOG" 2>&1; rc=$?
    tok=$(grep -a -A1 'tokens used' "$LOG" | tail -1)
    if grep -aq "usage limit" "$LOG"; then
      rm -f "$OUT"; t=$(grep -ao "try again at [^.]*[0-9]:[0-9][0-9] [AP]M" "$LOG" | head -1 | grep -o "[0-9]*:[0-9][0-9] [AP]M")
      echo "== $ID LIMIT $(date +%T) tokens=$tok retry_at=${t:-unknown}"
      if [ "$MODE" = wait ] && [ -n "$t" ]; then wait_until "$t"; continue; fi
      echo "STOPPED_AT_LIMIT $t"; git status --porcelain; exit 0
    fi
    echo "== $ID done rc=$rc $(date +%T) tokens=$tok size=$(wc -m < "$OUT" 2>/dev/null)"
    [ -s "$OUT" ] || echo "   !! output empty"
    break
  done
done < "$Q"
echo "QUEUE_DONE"; git status --porcelain
