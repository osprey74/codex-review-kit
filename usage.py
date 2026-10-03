"""Codex の実行ごとのトークン数と使用枠の割合を、セッション記録から一覧にする。

使い方:
    python .claude/codex/usage.py [YYYY-MM-DD] [cwd の一部]
      日付を省略すると今日。cwd の一部を渡すと、その作業場所の実行だけに絞る。

~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl の最後の token_count を読む。
  total   … 入力（キャッシュ分を含む）＋出力
  非cache … total − キャッシュ済み入力（runner.sh のログに出る "tokens used" と同じ値）
  5h% / 週% … その実行を終えた時点の使用枠（rate_limits.primary / secondary）
codex review は親セッション（トークン記録なし）と子セッションに分かれる。数えるのは子のほう。
"""
import datetime
import glob
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def first_prompt(lines):
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        p = d.get("payload") or {}
        if d.get("type") == "response_item" and p.get("role") == "user":
            for c in p.get("content", []):
                t = c.get("text", "")
                if t and not t.startswith(("<", "# AGENTS.md")):
                    return t.replace("\n", " ")[:60]
    return ""


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    where = sys.argv[2] if len(sys.argv) > 2 else ""
    y, m, d = day.split("-")
    files = sorted(glob.glob(os.path.expanduser(f"~/.codex/sessions/{y}/{m}/{d}/rollout-*.jsonl")))
    print("開始(UTC)  作業場所                     total    非cache  5h%  週%  依頼")
    sum_total = sum_fresh = 0
    for f in files:
        lines = open(f, encoding="utf-8", errors="replace").read().splitlines()
        meta = json.loads(lines[0]).get("payload", {})
        cwd = meta.get("cwd", "")
        if where and where not in cwd:
            continue
        last = None
        for line in lines:
            if '"token_count"' in line:
                last = line
        if not last:
            continue
        p = json.loads(last)["payload"]
        u = (p.get("info") or {}).get("total_token_usage") or {}
        rl = p.get("rate_limits") or {}
        total = u.get("total_tokens", 0)
        fresh = total - u.get("cached_input_tokens", 0)
        sum_total += total
        sum_fresh += fresh
        ts = meta.get("timestamp", "")[11:19]
        pr = (rl.get("primary") or {}).get("used_percent", "")
        se = (rl.get("secondary") or {}).get("used_percent", "")
        print(f"{ts}  {os.path.basename(cwd)[:26]:<26} {total:>9,} {fresh:>9,} {pr:>4} {se:>4}  {first_prompt(lines)}")
    print(f"合計  total {sum_total:,} / 非cache {sum_fresh:,}")


if __name__ == "__main__":
    main()
