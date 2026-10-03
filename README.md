# codex-review-kit

「Claude Code が実装し、ChatGPT Codex が読み取り専用でレビューの指摘を**抜き出し**、Claude Code が**再現テストで裏を取って**から直す」分業の道具一式。
書き手は Claude Code 一人に保ち、別のモデル（OpenAI Codex）にはファイルを書けない状態でレビューだけをさせます。一つのものを二つの目で確かめるための道具です。

## 使う前に

- **このリポジトリのコードを外部サービス（OpenAI）に送ってよいか**を確かめる。業務・顧客のコードは社内規程と契約が先。学習オプトアウトとは別問題。
- ChatGPT のアカウントで Codex が使えること（VSCode の ChatGPT 拡張に `codex.exe` が同梱。ログインは拡張と共有）。

## 導入（プロジェクトごと）

1. `AGENTS.md` をリポジトリ直下に写し、【プロジェクトごとに書く】を埋める（構成、ビルド・テストのコマンド、決着済みの設計判断、対象外のパス）。
2. `runner.sh` `refcheck.py` `usage.py` `queue.example.txt` `.gitignore` を `<repo>/.claude/codex/` に写す。
3. `queue.example.txt` を `queue.txt` に写し、差分の範囲（`<base>..<head>`）を書き換える。
4. 一本だけ試す → 報告を Claude に検証させ、誤検出の原因を AGENTS.md §3 に足す。

## 流れ（1回のレビュー）

1. **Codex**：`bash .claude/codex/runner.sh`（依頼一覧を流す。報告は `.claude/codex/reports/ID_日付.md`、`OUTDIR` で変更可）
   - 手軽に一本だけなら `codex review --commit <sha>` でもよい。**`-s` と `-o` が無い**ので `-c sandbox_mode='"read-only"'` を付け、標準出力を保存する（例：`codex review -c sandbox_mode='"read-only"' --commit abc123 < /dev/null > .claude/codex/reports/CR_$(date +%F).md`）。
   - kazahana の試運転（2026-09-26）では、`codex review` 1 回で観点別 5 本と同じ数の不具合を見つけ、コストは約 5 分の 1 だった。観点別は丙群（確認済み）や周辺の指摘（型・テストの抜け）まで残る。普段は review、大きな変更は観点別。
2. **Claude**：`python .claude/codex/refcheck.py .claude/codex/reports/<報告>.md` で「ファイル:行＋コード片」を照合 → 作り話・場所の誤りを落とす。
3. **Claude**：残った甲群ごとに**失敗する再現テスト**を書いて走らせる → 失敗したものだけ採用、通ったものは誤検出として記録。テストの仕組みが無いリポジトリは、作業用ブランチにだけ入れる（main に入れない）。
4. **Claude**：モジュールをまたぐ整合（D3）の突き合わせは自分で行う。
5. 修正 → テストが通ることを確認 → 同じ差分に Codex をもう一度（直したことで生じた問題を拾う）。

## 使用量

- `python .claude/codex/usage.py [YYYY-MM-DD] [作業場所の一部]`：`~/.codex/sessions` から実行ごとのトークン数（キャッシュ込みの合計／キャッシュ除き）と、5 時間枠・週枠の使用率を一覧にする。
- `runner.sh` のログの "tokens used" は**キャッシュ分を除いた値**。枠の消費は `used_percent` で見る。
- kazahana の実測（gpt-5.6-sol・medium）：差分レビュー 1 本 ≈ 20 万トークン（キャッシュ込み）、1 本 2〜3 分。枠に対する割合はプランによって違うので、`usage.py` で自分の環境の値を確かめてください。

## 注意（実運用で踏んだもの）

- **`codex exec` には `< /dev/null` が要る**（無いと `while read` の一覧の残りを飲み込む。`runner.sh` は対応済み）。
- **読み取り専用**（`-s read-only`）で走らせる。Codex はファイルを一切書けず、報告は CLI が `-o` で保存する。テスト（キャッシュ等を書く）は Claude 側で走らせる。
- **上限時のメッセージ** `try again at 2:52 PM.`／`try again at Sep 24th, 2026 12:55 AM.` を `runner.sh` が読んで待つ。
- **Codex の出力の癖**：引用の要約、場所の取り違え、二か所を一つの欄に並べる。`refcheck.py` で見分ける（kazahana では 96 件中 1 件が行番号の取り違え。表のセル内の `\|`・`<br>`・`\``は refcheck が処理する）。
- **決着済みの事項を AGENTS.md §3 に書かないと、毎回同じ誤検出が出る**。誤検出を見つけたら §3 に一行足すのが一番効く。

## 動作環境

- Windows の Git Bash で動作を確認しています（`runner.sh` は VSCode の ChatGPT 拡張に同梱の `codex.exe` を探し、無ければ PATH の `codex` を使います）。
- Python 3.10 以上（`refcheck.py`・`usage.py`）。

## ライセンス

MIT License
