"""Codex レビュー報告の「ファイル:行＋コード片」を、リポジトリの実物に機械照合する（開発用）。

使い方（リポジトリのルートで）:
    python .claude/codex/refcheck.py .claude/codex/reports/D1_*.md [...]

表の行から `path/to/file.ext:42` とその次の列（コード片）を拾い、判定する：
    一致       … その行（前後4行以内）にコード片がそのままある
    行番号ずれ … ファイル内にはあるが、書かれた行の前後4行に無い
    別ファイル … そのファイルには無いが、リポジトリの別のファイルにある（パスの誤り）
    不一致     … どこにも無い（要約・言い換え・作り話）
    ファイル無し … パスが存在しない
コード片の ` と <br> は空白に置き換え、\| は | に戻して比べる。空白の違いは無視する（連続する空白を一つにまとめる）。
一致したものでも、採否は再現テストで決める。これは作り話と場所の誤りを先に落とすための道具。
"""
import io
import os
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
REF = re.compile(r"^`?([\w./\\-]+\.[A-Za-z0-9]+):(\d+)(?:[-–](\d+))?`?")


def norm(s):
    s = re.sub(r"<br\s*/?>", " ", s)          # セル内の改行
    s = s.replace(r"\`", "`")                   # \` はコード片の中のバッククォート
    s = s.replace("`", " ")                     # 引用側・ソース側とも ` は空白として比べる
    return re.sub(r"\s+", " ", s).strip()


def tracked_files():
    try:
        out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, encoding="utf-8").stdout
        return [f for f in out.splitlines() if f]
    except Exception:
        return []


def read_lines(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read().split("\n")
    except OSError:
        return None


def check(rep, files):
    c = {"一致": 0, "行番号ずれ": 0, "別ファイル": 0, "不一致": 0, "ファイル無し": 0}
    ngs = []
    for row in open(rep, encoding="utf-8"):
        if not row.startswith("|"):
            continue
        # \| は表の区切りではなくセル内の縦棒
        cells = [x.strip().replace(r"\|", "|") for x in re.split(r"(?<!\\)\|",row.strip().strip("|"))]
        for i, cell in enumerate(cells[:-1]):
            m = REF.match(cell)
            if not m:
                continue
            path, ln = m.group(1).replace("\\", "/"), int(m.group(2))
            q = norm(cells[i + 1])
            if not q:
                break
            lines = read_lines(path)
            if lines is None:
                c["ファイル無し"] += 1
                ngs.append(f"{path}:{ln} ファイル無し")
                break
            near = norm(" ".join(lines[max(0, ln - 5):ln + 4]))
            whole = norm(" ".join(lines))
            if q in near:
                c["一致"] += 1
            elif q in whole:
                c["行番号ずれ"] += 1
                ngs.append(f"{path}:{ln} 行番号ずれ … {q[:50]}")
            else:
                other = [f for f in files if f != path and (t := read_lines(f)) and q in norm(" ".join(t))]
                if other:
                    c["別ファイル"] += 1
                    ngs.append(f"{path}:{ln} 実際は {', '.join(other[:3])} … {q[:50]}")
                else:
                    c["不一致"] += 1
                    ngs.append(f"{path}:{ln} 不一致 … {q[:60]}")
            break
    total = sum(c.values())
    print(f"{os.path.basename(rep)}: 計 {total} / " + " / ".join(f"{k} {v}" for k, v in c.items()))
    for s in ngs:
        print("   NG", s)


if __name__ == "__main__":
    fs = tracked_files()
    for r in sys.argv[1:]:
        check(r, fs)
