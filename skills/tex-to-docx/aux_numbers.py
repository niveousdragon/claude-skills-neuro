"""Write the numbers LaTeX printed into a copy of a .tex, so that Word shows them too.

Pandoc numbers neither sections nor figures nor tables and leaves every ``\\ref`` empty
or as a raw key. In a comparison of two versions that is worse than ugly: each empty
reference and each number pandoc invents on its own is a change the reader has to
click through. So the numbers are read from the ``.aux`` of the PDF build of *that*
version and written into the copy: section headings, figure and table captions,
``\\ref``/``\\eqref``/``\\cref``/``\\Cref``/``\\autoref``. Display equations are left
to tex2docx, which numbers them as LaTeX does; the two are checked against each other.

The wording of the paper is not touched. Every version of a comparison goes through
this, so the Word files differ only where the text differs.

Usage: python aux_numbers.py SRC.tex AUX OUT.tex
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tex2docx import expand_inputs, resolve_graphic, strip_comments  # noqa: E402

BS = "\\"
LEVELS = ("section", "subsection", "subsubsection")
# cleveref's default names; `capitalise` switches \cref to the \Cref column,
# `noabbrev` writes the words out.
CREF = {"figure": ("fig.", "Fig.", "figure"), "table": ("table", "Table", "table"),
        "equation": ("eq.", "Eq.", "equation"), "section": ("section", "Section", "section"),
        "subsection": ("section", "Section", "section"),
        "subsubsection": ("section", "Section", "section"),
        "appendix": ("appendix", "Appendix", "appendix"),
        "subappendix": ("appendix", "Appendix", "appendix"),
        "algorithm": ("algorithm", "Algorithm", "algorithm"),
        "theorem": ("theorem", "Theorem", "theorem"), "lemma": ("lemma", "Lemma", "lemma")}
AUTOREF = {"figure": "Figure", "table": "Table", "equation": "Equation", "section": "Section",
           "subsection": "Section", "subsubsection": "Section", "appendix": "Appendix"}


def read_aux(path, seen=None):
    """Labels, their kinds, numbered headings and float numbers, in the order LaTeX wrote them."""
    labels, kinds, toc, floats = {}, {}, [], {"figure": [], "table": []}
    seen = seen or set()
    path = Path(path)
    seen.add(path.resolve())
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\\@input\{([^}]+)\}", line)
        if m:                                    # \include'd chapters keep their own .aux
            sub = path.parent / m.group(1)
            if sub.exists() and sub.resolve() not in seen:
                l2, k2, t2, f2 = read_aux(sub, seen)
                labels.update(l2), kinds.update(k2), toc.extend(t2)
                for k in floats:
                    floats[k].extend(f2[k])
            continue
        m = re.match(r"\\newlabel\{(.+?)@cref\}\{\{\[([^\]]*)\]", line)
        if m:
            kinds[m.group(1)] = m.group(2)
            continue
        m = re.match(r"\\newlabel\{(.+?)\}\{\{(.*?)\}\{", line)
        if m:
            labels[m.group(1)] = re.sub(r"\\relax\s*", "", m.group(2)).strip()
            continue
        m = re.match(r"\\@writefile\{toc\}\{\\contentsline \{(\w+)\}\{\\numberline \{([^}]*)\}", line)
        if m and m.group(1) in LEVELS:
            toc.append((m.group(1), m.group(2)))
            continue
        m = re.match(r"\\@writefile\{lo[ft]\}\{\\contentsline \{(figure|table)\}\{\\numberline \{([^}]*)\}", line)
        if m:
            floats[m.group(1)].append(m.group(2))
    return labels, kinds, toc, floats


def _cref_style(head):
    m = re.search(r"\\usepackage(\[[^\]]*\])?\{cleveref\}", head)
    opts = m.group(1) or "" if m else ""
    names = {k: list(v) for k, v in CREF.items()}
    for cmd, col in (("crefname", 0), ("Crefname", 1)):
        for mm in re.finditer(r"\\" + cmd + r"\{(\w+)\}\{([^}]*)\}\{([^}]*)\}", head):
            names.setdefault(mm.group(1), [mm.group(2)] * 3)[col] = mm.group(2)
    return names, "capitalise" in opts or "capitalize" in opts, "noabbrev" in opts


def prepare(src, aux, out, base=None, final=None):
    """Write OUT, a copy of SRC with LaTeX's numbers in it. Returns a list of problems.

    BASE is the folder LaTeX ran in (inputs and figures are found from it); by default the
    folder of SRC. A snapshot saved away from the manuscript names the manuscript's folder.

    FINAL, the labels of the last version ({key: number}), gives every labelled heading,
    figure, table and reference the number it has in the last version. A comparison then
    shows no change that only renumbers: the author does not review numbering (it is
    LaTeX's own in the last version, read from its .aux), and a renumbered "Figure S2"
    in every mention would bury the changes that matter."""
    src, out = Path(src).resolve(), Path(out)
    base = Path(base).resolve() if base else src.parent
    tex = expand_inputs(strip_comments(src.read_text(encoding="utf-8", errors="replace")), base)
    tex = strip_comments(tex)
    labels, kinds, toc, floats = read_aux(aux)
    start = tex.index(BS + "begin{document}")
    head, body = tex[:start], tex[start:]
    problems = []

    # Shorthands for a bare \begin{equation}/\end{equation}: tex2docx would count the
    # definition in the preamble as the first display equation.
    for m in list(re.finditer(r"\\(?:re)?newcommand\*?\{?\\(\w+)\}?\{\\(begin|end)\{(\w+\*?)\}\}[ \t]*\n?", head)):
        head = head.replace(m.group(0), "")
        body = re.sub(r"\\" + m.group(1) + r"(?![A-Za-z])", lambda _m, s=BS + m.group(2) + "{" + m.group(3) + "}": s, body)
    # One-argument macros that wrap a reference (\fig{x} -> Fig.~\ref{x}) are expanded,
    # so that the reference inside them is resolved below.
    for m in re.finditer(r"\\(?:re)?newcommand\*?\{?\\(\w+)\}?\[1\]\{(.*)\}[ \t]*$", head, re.M):
        name, defn = m.group(1), m.group(2)
        if re.search(r"\\(?:eq|c|C|auto)?ref\{#1\}", defn):
            body = re.sub(r"\\" + name + r"\{([^}]*)\}", lambda mm, d=defn: d.replace("#1", mm.group(1)), body)

    # "\S\ref{x}" would become "\S4", and pandoc drops the unknown macro together with the
    # number; write the section sign itself first.
    body = re.sub(r"\\S(?![A-Za-z]) ?", "\u00a7", body)

    # Equations: tex2docx numbers display rows in order; check that against LaTeX.
    eq_keys, n = set(), 0
    for m in re.finditer(r"\\begin\{(equation|align|gather|multline|eqnarray|alignat|flalign)\}(.*?)\\end\{\1\}",
                         body, re.S):
        rows = [m.group(2)] if m.group(1) in ("equation", "multline") else re.split(r"\\\\", m.group(2))
        for row in rows:
            if not row.strip():
                continue
            keys = re.findall(r"\\label\{([^}]+)\}", row)
            eq_keys.update(keys)
            if BS + "nonumber" in row or BS + "notag" in row:
                continue
            n += 1
            for k in keys:
                if labels.get(k) != str(n):
                    problems.append("equation %d (%s): the PDF numbers it %s" % (n, k, labels.get(k)))

    final = final or {}

    def num(key):
        if key in final:
            return final[key]
        if key not in labels:
            problems.append("unresolved reference " + key)
            return "??"
        return labels[key]

    names, capital, full = _cref_style(head)

    def cref(m):
        keys = [k.strip() for k in m.group(2).split(",") if k.strip()]
        kind = kinds.get(keys[0], "")
        nums = [("(%s)" % num(k)) if kind == "equation" else num(k) for k in keys]
        col = 2 if full else (1 if m.group(1) == "C" or capital else 0)
        word = names.get(kind, ["", "", ""])[col]
        if full and (m.group(1) == "C" or capital):
            word = word[:1].upper() + word[1:]
        if len(nums) > 1:
            word = word.rstrip(".") + ("s." if word.endswith(".") else "s")
            nums = [", ".join(nums[:-1]) + " and " + nums[-1]]
        return (word + "\u00a0" if word else "") + nums[0]

    body = re.sub(r"\\(c|C)ref\{([^}]+)\}", cref, body)
    body = re.sub(r"\\autoref\{([^}]+)\}", lambda m: (AUTOREF.get(kinds.get(m.group(1), ""), "") + "\u00a0").lstrip()
                  + num(m.group(1)), body)
    body = re.sub(r"\\eqref\{([^}]+)\}", lambda m: "(%s)" % num(m.group(1)), body)
    body = re.sub(r"\\ref\{([^}]+)\}", lambda m: num(m.group(1)), body)
    body = re.sub(r"\\pageref\{[^}]*\}", "", body)        # Word has no pages to point at

    # Section headings: the numbered ones, in order, against the table of contents in the .aux.
    heads = [m for m in re.finditer(r"\\(section|subsection|subsubsection)(\*?)\s*(?:\[[^\]]*\])?\{", body)
             if not m.group(2)]
    if len(heads) != len(toc) or any(m.group(1) != lev for m, (lev, _) in zip(heads, toc)):
        problems.append("headings: %d numbered in the text, %d in the .aux" % (len(heads), len(toc)))
    else:
        parts, pos = [], 0
        for m, (_, number) in zip(heads, toc):
            lab = re.match(r"[^\n]*?\}\s*\\label\{([^}]+)\}", body[m.end():m.end() + 400])
            if lab and lab.group(1) in final:
                number = final[lab.group(1)]
            parts += [body[pos:m.end()], number + " "]
            pos = m.end()
        body = "".join(parts) + body[pos:]

    # Captions: the name in force (\figurename may change, e.g. for Extended Data) and the
    # number LaTeX printed, in order of the list of figures/tables.
    name = {"figure": "Figure", "table": "Table"}
    for m in re.finditer(r"\\renewcommand\{?\\(figure|table)name\}?\{([^}]*)\}", head):
        name[m.group(1)] = m.group(2)
    used = {"figure": 0, "table": 0}
    parts, pos = [], 0
    events = re.compile(r"\\renewcommand\{?\\(figure|table)name\}?\{([^}]*)\}|\\begin\{(figure|table)\*?\}")
    for m in events.finditer(body):
        if m.start() < pos:
            continue
        if m.group(1):
            name[m.group(1)] = m.group(2)
            continue
        kind = m.group(3)
        end = body.find(BS + "end{" + kind, m.start())
        block = body[m.start():end]
        cap = re.search(r"\\caption\s*(?:\[[^\]]*\])?\s*\{", block)
        if not cap:
            continue
        if used[kind] >= len(floats[kind]):
            problems.append("%s %d: not in the .aux" % (kind, used[kind] + 1))
            number = "??"
        else:
            number = floats[kind][used[kind]]
        used[kind] += 1
        lab = re.search(r"\\label\{([^}]+)\}", block)
        if lab and lab.group(1) in labels and labels[lab.group(1)] != number:
            problems.append("%s %s: its label says %s" % (kind, number, labels[lab.group(1)]))
        if lab and lab.group(1) in final:
            number = final[lab.group(1)]
        block = block[:cap.end()] + BS + "textbf{" + name[kind] + " " + number + ".} " + block[cap.end():]
        parts.append(body[pos:m.start()] + block)
        pos = end
    parts.append(body[pos:])
    body = "".join(parts)
    for kind in used:
        if used[kind] != len(floats[kind]):
            problems.append("%ss: %d captions in the text, %d in the .aux" % (kind, used[kind], len(floats[kind])))

    # Labels are resolved; only those of equations stay, for tex2docx's numbering.
    body = re.sub(r"\\label\{([^}]+)\}", lambda m: m.group(0) if m.group(1) in eq_keys else "", body)

    # Figures: absolute paths, searched as LaTeX searches them (\graphicspath included).
    dirs = [base] + [base / d for d in re.findall(r"\{([^{}]+)\}",
                                                              "".join(re.findall(r"\\graphicspath\{(.*)\}", head)))]

    def graphic(m):
        for d in dirs:
            p = resolve_graphic(m.group(2).strip(), d)
            if p:
                return BS + "includegraphics" + (m.group(1) or "") + "{" + p.as_posix() + "}"
        problems.append("figure not found: " + m.group(2))
        return m.group(0)

    body = re.sub(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}", graphic, body)

    # authblk: pandoc keeps the author names and drops \affil; put them under the title.
    affils = re.findall(r"\\affil(?:\[[^\]]*\])?\{\s*(.*?)\}\s*$", head, re.S | re.M)
    if affils and BS + "maketitle" in body:
        block = "".join("\n\n" + BS + "noindent " + " ".join(a.split()) for a in affils)
        body = body.replace(BS + "maketitle", BS + "maketitle" + block + "\n\n", 1)

    left = re.findall(r"\\(?:c|C|auto|eq)?ref\{[^}]*\}", body)
    if left:
        problems.append("references left unresolved: %s" % sorted(set(left))[:10])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(head + body, encoding="utf-8")
    return problems


if __name__ == "__main__":
    probs = prepare(*sys.argv[1:4])
    for p in probs:
        print("  ", p)
    print("[FAILED]" if probs else "[OK]", sys.argv[3])
    sys.exit(1 if probs else 0)
