"""Count reported numbers per 100 words in a LaTeX manuscript, prose and captions apart.

Usage:
    python count_numbers.py PAPER.tex [OLD.tex]

Prints, for each \\section (and for captions separately): words, numbers, numbers per
100 words. With a second file, prints both versions side by side.

What counts as a number: a quantity the reader is told. "0.28", "5{,}365", "p < 0.001",
"27 of 29", "10^{-5}" (one number), "-0.07". Each number in a range or a list counts.
A quantity in words counts like a digit: "a quarter of", "one in six", "nearly half"
("majority", "first half" and "a third variable" do not).
What does not count, because it names something rather than reports a value:
- digits inside an identifier: F1, CA1, L2/3, S2, v1.2.2, R^2, F_1;
- a number after a label: Fig. 2, Figure 3c, Table 1, Section 4, Eq. 5, Stage 1, Step 2,
  Supplementary Fig. 4, Extended Data Fig. 1, Methods 3.2;
- anything inside \\cite, \\ref, \\eqref, \\label, \\includegraphics, \\url, \\href targets,
  and LaTeX comments.
"""
import re
import sys

LABELS = r"(?:Figs?\.|Figures?|Tables?|Sections?|Sec\.|Eqs?\.|Equations?|Stages?|Steps?|" \
         r"Supplementary|Extended\s+Data|Methods|Panels?|Chapters?|Appendix|Note)"

_W = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|hundred)"
_FR = r"(?:half|halves|thirds?|quarters?|fifths?|sixths?|tenths?)"
# Order matters: each match becomes "1", so a qualified fraction counts once.
VERBAL = [
    r"\b(?:nearly|almost|about|roughly|over|under|(?:more|less|fewer)\s+than)\s+"
    r"(?:a\s+|one\s+)?" + _FR + r"\b",
    r"\b(?:a|" + _W + r")\s+" + _FR + r"\s+of\b",
    r"\b" + _W + r"\s+(?:[a-z-]+\s+)?(?:in|out\s+of)\s+" + _W + r"\b",
    r"(?<!first )(?<!second )(?<!last )(?<!other )\bhalf\s+of\b",
]


def _drop_braced(text, command):
    """Remove \\command[opt]{...} with balanced braces."""
    out, i = [], 0
    pat = re.compile(r"\\" + command + r"\*?(\[[^\]]*\])?\{")
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
        i = j


def _take_braced(text, command):
    """Return (text without \\command{...}, list of the removed contents)."""
    found, out, i = [], [], 0
    pat = re.compile(r"\\" + command + r"\*?(\[[^\]]*\])?\{")
    while True:
        m = pat.search(text, i)
        if not m:
            out.append(text[i:])
            return "".join(out), found
        out.append(text[i:m.start()])
        depth, j = 1, m.end()
        while j < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        found.append(text[m.end():j - 1])
        i = j


def clean(text):
    text = re.sub(r"(?<!\\)%.*", "", text)
    for c in ("cite[tp]?", "citep", "citet", "ref", "eqref", "label", "includegraphics",
              "url", "fig", "autoref", "cref", "Cref"):
        text = _drop_braced(text, c)
    text = re.sub(r"\\href\{[^}]*\}", "", text)
    return text


def count_numbers(text):
    t = clean(text)
    t = t.replace("{,}", ",").replace("\\,", " ").replace("~", " ")
    t = re.sub(r"\\(?:times|cdot)", " ", t)
    # one number: 10^{-5}, 10^5
    t = re.sub(r"\b10\s*\^\s*\{?\s*[-−]?\s*\d+\s*\}?", " 1 ", t)
    # identifiers: sub/superscripts on letters, letters glued to digits, versions
    t = re.sub(r"[A-Za-z\\}]\s*[_^]\s*\{?[-\d.,]+\}?", " ID ", t)
    t = re.sub(r"\bv?\d+(?:\.\d+){2,}\b", " ID ", t)
    t = re.sub(r"\b[A-Za-z]+\d+[A-Za-z\d/]*\b", " ID ", t)
    t = re.sub(r"\b\d+[A-Za-z]+\b(?<!\d[st]h)", lambda m: " ID " if not re.fullmatch(
        r"\d+(?:st|nd|rd|th|s|ms|Hz|kHz|mm|cm|um|nm|min|h|d|x|fold|D)", m.group()) else m.group(), t)
    # a quantity in words is still a quantity: "a quarter", "one in six" must not
    # lower the count, or a pass can trade digits for words and look lighter
    for pat in VERBAL:
        t = re.sub(pat, " 1 ", t, flags=re.IGNORECASE)
    # labels followed by numbers (and panel letters / ranges)
    t = re.sub(LABELS + r"\s*\.?\s*(?:Fig\.\s*|Figure\s*)?S?\d+(?:\.\d+)*[a-z]?"
               r"(?:\s*[,–-]\s*(?:S?\d+[a-z]?|[a-z]\b))*", " LABEL ", t)
    nums = re.findall(r"(?<![\w.])[-−]?\d+(?:,\d{3})*(?:\.\d+)?", t)
    return len(nums)


def count_words(text):
    t = clean(text)
    t = re.sub(r"\$[^$]*\$", " x ", t)
    t = re.sub(r"\\[A-Za-z]+\*?", " ", t)
    t = re.sub(r"[{}\[\]]", " ", t)
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-.,]*", t))


def sections(tex):
    body = tex.split("\\begin{document}", 1)[-1]
    body = re.split(r"\\bibliography\{|\\begin\{thebibliography\}|\\printbibliography", body)[0]
    body, caps = _take_braced(body, "caption")
    parts = re.split(r"\\section\*?\{([^}]*)\}", body)
    out = [("(before first section)", parts[0])] if parts[0].strip() else []
    out += [(parts[k], parts[k + 1]) for k in range(1, len(parts) - 1, 2)]
    out.append(("Captions", "\n".join(caps)))
    return out


def report(tex):
    rows = []
    for name, text in sections(tex):
        w, n = count_words(text), count_numbers(text)
        rows.append((name.strip(), w, n, round(100 * n / w, 1) if w else 0.0))
    return rows


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    reports = [report(open(p, encoding="utf-8").read()) for p in argv[1:3]]
    if len(reports) == 1:
        print(f"{'section':40s} {'words':>7s} {'numbers':>8s} {'per100':>7s}")
        for name, w, n, r in reports[0]:
            print(f"{name[:40]:40s} {w:7d} {n:8d} {r:7.1f}")
    else:
        new = {r[0]: r for r in reports[1]}
        print(f"{'section':40s} {'old/100w':>9s} {'new/100w':>9s} {'old n':>6s} {'new n':>6s}")
        for name, w, n, r in reports[0]:
            nr = new.get(name, (name, 0, 0, 0.0))
            print(f"{name[:40]:40s} {r:9.1f} {nr[3]:9.1f} {n:6d} {nr[2]:6d}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv))
