"""Find phrases repeated word for word in a LaTeX manuscript.

Usage:
    python find_repeats.py PAPER.tex [--min-words 8]

A claim stated once reads as a claim; the same words in four places read as a formula
the authors had to repeat. Prints every phrase of at least --min-words words (default 8)
that occurs more than once in the text, with the line of each occurrence. Citations,
references, labels, LaTeX comments and the bibliography are ignored; an inline formula
is one word; captions count.
"""
import re
import sys
from collections import defaultdict

DROP = ("cite[tp]?", "citep", "citet", "citealp", "ref", "eqref", "autoref", "cref", "Cref",
        "label", "includegraphics", "url")


def _blank(s):
    return re.sub(r"[^\n]", " ", s)


def _blank_braced(text, command):
    """Blank out \\command[opt]{...} (balanced braces), keeping line breaks."""
    pat = re.compile(r"\\" + command + r"\*?(\[[^\]]*\])?\{")
    out, i = [], 0
    while True:
        m = pat.search(text, i)
        if not m:
            out.append(text[i:])
            return "".join(out)
        out.append(text[i:m.start()])
        depth, j = 1, m.end()
        while j < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        out.append(_blank(text[m.start():j]))
        i = j


def _math_token(m):
    s = m.group()
    return "\u00a7" + re.sub(r"\s+", "", s) + "\u00a7" + "\n" * s.count("\n")


def tokens(tex):
    """Words of the body as (word, line number), line numbers of the original file."""
    start = tex.find("\\begin{document}")
    start = 0 if start < 0 else start
    head_lines = tex[:start].count("\n")
    body = re.split(r"\\bibliography\{|\\begin\{thebibliography\}|\\printbibliography",
                    tex[start:])[0]
    body = re.sub(r"(?<!\\)%.*", lambda m: _blank(m.group()), body)
    for c in DROP:
        body = _blank_braced(body, c)
    body = re.sub(r"\\href\{[^}]*\}", lambda m: _blank(m.group()), body)
    body = re.sub(r"\$\$.*?\$\$|\$[^$]*\$|\\\[.*?\\\]|\\\(.*?\\\)", _math_token, body,
                  flags=re.S)
    out = []
    for k, line in enumerate(body.split("\n")):
        line = re.sub(r"\\[A-Za-z]+\*?", " ", line)
        line = re.sub(r"[{}\[\]~]", " ", line)
        for w in re.findall(r"\u00a7[^\u00a7]*\u00a7|[A-Za-z0-9][A-Za-z0-9'\u2019\-]*", line):
            out.append((w.lower(), head_lines + k + 1))
    return out


def find_repeats(tex, min_words=8):
    """Return [(phrase, [line of each occurrence])], most repeated first, then longest.

    A stretch of text whose every window of min_words words occurs elsewhere is one
    occurrence. Occurrences that share any window are one repeated phrase, even when one
    of them was reworded at its edges or in the middle; the longest occurrence is shown.
    """
    toks = tokens(tex)
    words = [w for w, _ in toks]
    grams = defaultdict(list)
    for i in range(len(words) - min_words + 1):
        grams[tuple(words[i:i + min_words])].append(i)
    repeated = sorted(i for starts in grams.values() if len(starts) > 1 for i in starts)
    runs = []  # (first start, last start) of each stretch
    for i in repeated:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    parent = list(range(len(runs)))

    def root(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    owner = {}
    for r, (a, b) in enumerate(runs):
        for s in range(a, b + 1):
            key = tuple(words[s:s + min_words])
            if key in owner:
                parent[root(r)] = root(owner[key])
            else:
                owner[key] = r
    groups = defaultdict(list)
    for r in range(len(runs)):
        groups[root(r)].append(runs[r])
    found = []
    for members in groups.values():
        lines = sorted({toks[a][1] for a, _ in members})
        if len(lines) < 2:
            continue
        a, b = max(members, key=lambda m: m[1] - m[0])
        found.append((" ".join(words[a:b + min_words]), lines))
    found.sort(key=lambda f: (-len(f[1]), -len(f[0])))
    return found


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 1
    n = 8
    if "--min-words" in argv:
        n = int(argv[argv.index("--min-words") + 1])
        args = [a for a in args if a != str(n)]
    found = find_repeats(open(args[0], encoding="utf-8").read(), n)
    if not found:
        print(f"No phrase of {n}+ words occurs twice.")
        return 0
    for phrase, lines in found:
        print(f"x{len(lines)}  lines {', '.join(map(str, lines))}:  {phrase}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv))
