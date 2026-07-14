#!/usr/bin/env python3
"""Convert a LaTeX document to a clean, reader-ready Word (.docx) file.

The goal is a Word file a non-LaTeX reader can open with nothing lost: figures
embedded (PDF/EPS rasterised so Word actually renders them), citations resolved
to real reference entries, cross-references and math converted to native Word
equations. No LaTeX comments, TODO notes, or author annotations survive into the
output -- the converter first writes a clean copy of the source with every
comment removed, and pandoc consumes that copy.

Pipeline
--------
1. Read the source .tex and locate its bibliography (``\\bibliography`` /
   ``\\addbibresource``) unless one is passed explicitly.
2. Write a clean copy: strip ``%`` comments (honouring escaped ``\\%``) and drop
   pure-comment lines so they never reach the reader.
3. Rasterise every ``\\includegraphics`` target Word cannot embed (.pdf, .eps,
   .ps) to PNG, and rewrite each graphics path to an absolute path so the figure
   resolves no matter where pandoc runs.
4. Run pandoc with ``--citeproc`` to produce the .docx: math becomes native OMML
   equations, figures are embedded, citations and the reference list are built
   from the .bib.
5. Verify the result -- count embedded media and equations, and report them.

A multi-file document built on a heavy template (a thesis, a book) needs
``--flatten``: it inlines every ``\\input``/``\\include`` -- so chapters and the
figures inside them are actually seen -- and swaps the template preamble for a
minimal one, which pandoc would otherwise try to interpret at the cost of
unbounded memory.

Usage
-----
    python tex2docx.py paper.tex
    python tex2docx.py paper.tex -o /out/paper.docx
    python tex2docx.py paper.tex --bib refs.bib --csl nature.csl
    python tex2docx.py paper.tex --keep-clean      # keep the intermediate .tex

    # thesis / book: many files on a template
    python tex2docx.py dissertation.tex --flatten --toc \
        --toc-title "Оглавление" --refs-title "Список литературы" \
        --title "..." --author "..." --csl gost.csl -o thesis.docx

Requirements: pandoc >= 2.x on PATH; PyMuPDF (``pip install pymupdf``) for
figure rasterisation (falls back to ``pdftoppm`` if PyMuPDF is absent).
"""

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


RASTER_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif"}
VECTOR_EXTS = {".pdf", ".eps", ".ps"}
# Order in which a bare \includegraphics{foo} (no extension) is resolved,
# matching LaTeX's graphics-path search preference.
RESOLVE_ORDER = [".pdf", ".png", ".jpg", ".jpeg", ".eps", ".ps", ".gif"]


# --------------------------------------------------------------------------- #
# Step 1 & 2: clean copy of the source
# --------------------------------------------------------------------------- #
def strip_comments(tex_text):
    """Return the LaTeX source with every comment removed.

    A ``%`` starts a comment unless it is escaped (``\\%``). A line that is
    *only* a comment is dropped entirely, because in LaTeX ``%`` also swallows
    the trailing newline -- keeping a blank line there would introduce a
    spurious paragraph break.
    """
    out_lines = []
    for line in tex_text.splitlines():
        # Find the first unescaped '%'.
        cut = None
        i = 0
        while i < len(line):
            if line[i] == "%" and (i == 0 or line[i - 1] != "\\"):
                cut = i
                break
            i += 1
        if cut is None:
            out_lines.append(line)
        else:
            kept = line[:cut]
            if kept.strip() == "":
                # Pure comment line -> drop it (no paragraph break in LaTeX).
                continue
            out_lines.append(kept.rstrip())
    return "\n".join(out_lines) + "\n"


def relocate_caption_labels(tex_text):
    r"""Move ``\label`` out of ``\caption{...}`` to just after the caption.

    Pandoc renders a ``\label`` that sits *inside* a caption as literal text
    (e.g. ``[tab:comparison]``) — an internal artifact leaking to the reader.
    Placing the label immediately *after* the caption keeps pandoc's
    figure/table numbering (so ``\ref`` still resolves to "Table 1") while
    removing the stray text. Uses brace matching so captions containing
    ``\citep{...}`` are handled correctly.
    """
    result = []
    i = 0
    marker = "\\caption"
    while True:
        j = tex_text.find(marker, i)
        if j == -1:
            result.append(tex_text[i:])
            break
        result.append(tex_text[i:j])
        k = j + len(marker)
        # Skip an optional short-caption argument \caption[...]{...}.
        while k < len(tex_text) and tex_text[k] in " \t\n":
            k += 1
        if k < len(tex_text) and tex_text[k] == "[":
            depth, k = 1, k + 1
            while k < len(tex_text) and depth:
                depth += (tex_text[k] == "[") - (tex_text[k] == "]")
                k += 1
        while k < len(tex_text) and tex_text[k] in " \t\n":
            k += 1
        if k >= len(tex_text) or tex_text[k] != "{":
            result.append(tex_text[j:k])
            i = k
            continue
        depth, m = 1, k + 1
        while m < len(tex_text) and depth:
            depth += (tex_text[m] == "{") - (tex_text[m] == "}")
            m += 1
        inner = tex_text[k + 1:m - 1]
        labels = re.findall(r"\\label\{[^}]*\}", inner)
        if labels:
            inner = re.sub(r"\\label\{[^}]*\}", "", inner).lstrip()
        result.append(tex_text[j:k + 1])  # "\caption...{"
        result.append(inner)
        result.append("}")
        result.append("".join(labels))    # labels moved just after the caption
        i = m
    return "".join(result)


def ensure_references_heading(tex_text, title="References"):
    """Give the auto-generated reference list a visible heading.

    Pandoc drops the citeproc bibliography where ``\\bibliography`` sits but adds
    no heading, so a reader sees an unlabelled block of references. If the source
    has no References/Bibliography heading already, insert one just before the
    ``\\bibliography`` command.
    """
    if re.search(r"\\(section|chapter)\*?\s*\{\s*(References|Bibliography|"
                 r"Список литературы|Литература)\s*\}", tex_text, re.IGNORECASE):
        return tex_text
    if re.search(r"\\bibliography\{", tex_text):
        return re.sub(r"(\\bibliography\{)",
                      rf"\\section*{{{title}}}\n\1", tex_text, count=1)
    # biblatex sources have no \bibliography command that survives the
    # conversion; citeproc appends the list at the very end, so the heading goes
    # there too.
    return tex_text.replace(r"\end{document}",
                            f"\\section*{{{title}}}\n\\end{{document}}", 1)


def find_bibliography(tex_text, tex_dir):
    r"""Find every .bib referenced by the document.

    Returns a list: biblatex documents routinely register several databases
    (``\addbibresource`` once per file), and pandoc accepts them all. Also looks
    inside ``\input``/``\include``d files, because templates keep the
    bibliography setup in a separate file.
    """
    haystack = expand_inputs(tex_text, tex_dir)
    found, seen = [], set()
    pattern = r"\\(?:bibliography|addbibresource)(?:\[[^\]]*\])?\{([^}]*)\}"
    for m in re.finditer(pattern, haystack):
        for name in (n.strip() for n in m.group(1).split(",")):
            if not name:
                continue
            cand = tex_dir / name
            if cand.suffix != ".bib":
                cand = cand.with_suffix(".bib")
            key = str(cand.resolve()).lower()
            if cand.exists() and key not in seen:
                seen.add(key)
                found.append(cand.resolve())
    return found


# --------------------------------------------------------------------------- #
# Step 3: figures Word can render
# --------------------------------------------------------------------------- #
def rasterise(src, dst, dpi):
    """Render a PDF/EPS/PS figure to a PNG at ``dpi``. Returns True on success."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(src))
        page = doc.load_page(0)
        zoom = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        pix.save(str(dst))
        doc.close()
        return True
    except Exception as exc:  # noqa: BLE001 -- fall back to pdftoppm
        if shutil.which("pdftoppm") and src.suffix.lower() == ".pdf":
            base = dst.with_suffix("")
            r = subprocess.run(
                ["pdftoppm", "-png", "-r", str(dpi), "-singlefile",
                 str(src), str(base)],
                capture_output=True, text=True,
            )
            if r.returncode == 0 and dst.exists():
                return True
            print(f"  ! pdftoppm failed for {src.name}: {r.stderr.strip()}",
                  file=sys.stderr)
        else:
            print(f"  ! could not rasterise {src.name}: {exc}", file=sys.stderr)
        return False


def resolve_graphic(raw_path, tex_dir):
    """Resolve an \\includegraphics argument to an existing file on disk."""
    p = (tex_dir / raw_path).resolve()
    if p.suffix and p.exists():
        return p
    if p.suffix and not p.exists():
        # Given extension missing; try the same stem with known extensions.
        for ext in RESOLVE_ORDER:
            cand = p.with_suffix(ext)
            if cand.exists():
                return cand
        return None
    # No extension -> search in preference order.
    for ext in RESOLVE_ORDER:
        cand = p.with_suffix(ext)
        if cand.exists():
            return cand
    return None


def process_graphics(tex_text, tex_dir, work_dir, dpi):
    """Rewrite every \\includegraphics to an absolute path Word can embed.

    Vector figures are rasterised into ``work_dir`` and the path repointed at
    the PNG. Raster figures keep their original absolute path.
    """
    missing = []
    converted = 0
    kept = 0

    def repl(m):
        nonlocal converted, kept
        opts, raw = m.group(1) or "", m.group(2).strip()
        resolved = resolve_graphic(raw, tex_dir)
        if resolved is None:
            missing.append(raw)
            return m.group(0)  # leave untouched; pandoc will warn too
        ext = resolved.suffix.lower()
        if ext in VECTOR_EXTS:
            png = work_dir / (resolved.stem + ".png")
            if rasterise(resolved, png, dpi):
                converted += 1
                target = png
            else:
                missing.append(raw)
                target = resolved
        else:
            kept += 1
            target = resolved
        abs_path = target.resolve().as_posix()
        return rf"\includegraphics{opts}{{{abs_path}}}"

    pattern = r"\\includegraphics(\[[^\]]*\])?\{([^}]*)\}"
    new_text = re.sub(pattern, repl, tex_text)
    return new_text, converted, kept, missing


# --------------------------------------------------------------------------- #
# Multi-file documents (theses, books) built on heavy LaTeX templates
# --------------------------------------------------------------------------- #
# Layout-only commands: they carry nothing a Word reader needs, and template
# versions of them routinely confuse pandoc. Value = number of {...} arguments
# to swallow along with the command.
DROP_COMMANDS = {
    "ifnumequal": 4, "ifdefmacro": 3, "providecommand": 2, "addtocontents": 2,
    "counterwithin": 2, "counterwithout": 2, "setcounter": 2, "setlength": 2,
    "hypersetup": 1, "urlstyle": 1, "microtypesetup": 1, "typeout": 1,
    "includeonly": 1, "graphicspath": 1,
    "tableofcontents": 0, "listoffigures": 0, "listoftables": 0,
    "printbibliography": 0, "insertbibliofull": 0, "insertbiblioauthor": 0,
    "insertbiblioexternal": 0, "insertbiblioauthorgrouped": 0,
    "endTOCtrue": 0, "FloatBarrier": 0, "clearpage": 0, "newpage": 0,
    "listfiles": 0, "appendix": 0, "maketitle": 0,
}
# Commands whose *content* must survive even though the command itself must not
# (e.g. the template's \fixme{...} highlighter wraps real text).
UNWRAP_COMMANDS = ["fixme", "texorpdfstring"]


def _match_group(text, i):
    """Given text[i] == '{', return index just past the matching '}'."""
    depth, i = 1, i + 1
    while i < len(text) and depth:
        if text[i] == "\\":          # skip escaped char
            i += 2
            continue
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return i


def drop_command(text, name, nargs):
    r"""Remove every ``\name`` (and ``\name*``) together with its brace args."""
    out, i = [], 0
    token = "\\" + name
    while True:
        j = text.find(token, i)
        if j == -1:
            out.append(text[i:])
            break
        after = j + len(token)
        # Only a real command boundary, not a longer command name.
        if after < len(text) and (text[after].isalpha() or text[after] == "@"):
            out.append(text[i:after])
            i = after
            continue
        out.append(text[i:j])
        k = after
        if k < len(text) and text[k] == "*":
            k += 1
        for _ in range(nargs):
            while k < len(text) and text[k] in " \t\n":
                k += 1
            if k < len(text) and text[k] == "[":       # optional arg
                while k < len(text) and text[k] != "]":
                    k += 1
                k += 1
                while k < len(text) and text[k] in " \t\n":
                    k += 1
            if k < len(text) and text[k] == "{":
                k = _match_group(text, k)
            else:
                break
        i = k
    return "".join(out)


def unwrap_command(text, name):
    r"""Replace ``\name{content}`` with ``content`` (keeps the text, drops the macro)."""
    token = "\\" + name
    out, i = [], 0
    while True:
        j = text.find(token, i)
        if j == -1:
            out.append(text[i:])
            break
        after = j + len(token)
        if after < len(text) and (text[after].isalpha() or text[after] == "@"):
            out.append(text[i:after])
            i = after
            continue
        out.append(text[i:j])
        k = after
        while k < len(text) and text[k] in " \t\n":
            k += 1
        if k < len(text) and text[k] == "{":
            end = _match_group(text, k)
            out.append(unwrap_command(text[k + 1:end - 1], name))
            # \texorpdfstring takes a second argument (the PDF form) — drop it.
            k = end
            if name == "texorpdfstring":
                while k < len(text) and text[k] in " \t\n":
                    k += 1
                if k < len(text) and text[k] == "{":
                    k = _match_group(text, k)
            i = k
        else:
            i = k
    return "".join(out)


def sanitise_template_noise(text):
    r"""Strip layout-only template commands; keep the text they wrap."""
    # \gappto\captionsrussian{...} — drop the command, the macro token, and one group.
    text = re.sub(r"\\gappto\s*\\[a-zA-Z@]+\s*", r"\\@gappto@", text)
    text = drop_command(text, "@gappto@", 1)
    for name, nargs in DROP_COMMANDS.items():
        text = drop_command(text, name, nargs)
    for name in UNWRAP_COMMANDS:
        text = unwrap_command(text, name)
    return text


# A template's hand-built title page is prose ("Специальность", "Диссертация на
# соискание…") glued together by macros that live in the preamble we discard, so
# it renders as debris. It is dropped ONLY when --title supplies a replacement —
# never silently, because a chapter could legitimately be called "title".
# Contents/list-of-figures files need no special case: they are just
# \tableofcontents / \listoffigures, which DROP_COMMANDS already removes.
TITLE_INCLUDES = {"title", "titlepage", "titul"}


def expand_inputs(text, base_dir, seen=None, depth=0, skip=frozenset()):
    r"""Recursively inline ``\input``/``\include`` files, stripping comments as we go.

    A thesis or book keeps its chapters in separate files, and figures live
    inside them. Inlining first means the comment stripper and the figure
    rasteriser see the *whole* document, not just the master file.
    """
    if seen is None:
        seen = set()
    if depth > 16:
        return text

    def repl(m):
        name = m.group(2).strip()
        path = base_dir / name
        if not path.suffix:
            path = path.with_suffix(".tex")
        if path.stem.lower() in skip:
            return ""
        key = str(path.resolve()).lower()
        if not path.exists() or key in seen:
            return ""
        seen.add(key)
        body = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        return "\n" + expand_inputs(body, base_dir, seen, depth + 1, skip) + "\n"

    return re.sub(r"\\(input|include)\{([^}]*)\}", repl, text)


VERBATIM_ENVS = ("verbatim", "lstlisting", "minted", "Verbatim", "alltt")
MATH_ENVS = ("equation", "align", "gather", "multline", "eqnarray", "displaymath",
             "alignat", "flalign", "math", "aligned", "split")

# Languages whose babel/polyglossia option makes ``<<...>>`` a quote ligature.
# Outside them, ``<<`` is far more likely to be a shift operator or a comparison.
GUILLEMET_LANGS = ("russian", "ukrainian", "bulgarian", "french", "francais",
                   "spanish", "italian", "portuguese", "catalan", "greek")

# Regions whose contents must never be rewritten as prose: math and code.
_PROTECTED = [
    r"\\begin\{(?:%s)\*?\}.*?\\end\{(?:%s)\*?\}" % ("|".join(VERBATIM_ENVS),
                                                    "|".join(VERBATIM_ENVS)),
    r"\\begin\{(?:%s)\*?\}.*?\\end\{(?:%s)\*?\}" % ("|".join(MATH_ENVS),
                                                    "|".join(MATH_ENVS)),
    r"\\verb\*?(.).*?\1",
    r"\\lstinline(.).*?\2",
    r"\$\$.*?\$\$",
    r"\\\[.*?\\\]",
    r"\\\(.*?\\\)",
    r"\$(?:\\.|[^$\\])*\$",
]
_PROTECTED_RE = re.compile("|".join(_PROTECTED), re.DOTALL)


def map_outside_protected(tex_text, fn):
    """Apply ``fn`` to the prose only, leaving math and code regions untouched."""
    chunks, last = [], 0
    for m in _PROTECTED_RE.finditer(tex_text):
        chunks.append(fn(tex_text[last:m.start()]))
        chunks.append(m.group(0))
        last = m.end()
    chunks.append(fn(tex_text[last:]))
    return "".join(chunks)


def uses_guillemet_ligature(source):
    r"""Does this document's language make ``<<...>>`` mean « … »?"""
    for m in re.finditer(r"\\usepackage\[([^\]]*)\]\{(?:babel|polyglossia)\}", source):
        if any(lang in m.group(1).lower() for lang in GUILLEMET_LANGS):
            return True
    for m in re.finditer(r"\\(?:setmainlanguage|setdefaultlanguage)\{([^}]*)\}", source):
        if m.group(1).strip().lower() in GUILLEMET_LANGS:
            return True
    return False


def convert_guillemets(tex_text):
    r"""Turn LaTeX's ``<<``/``>>`` quote ligature into real « » characters.

    Under babel's russian/french/… option ``<<...>>`` typesets as guillemets, and
    pandoc does not apply that ligature — the reader would see a literal
    ``<<белый ящик>>``. Only ever called for such a document, and only on prose:
    inside math or code ``<<`` is a shift operator or a comparison
    (``$a << b$``, ``std::cout << x``) and rewriting it would silently corrupt
    the source.
    """
    if "<<" not in tex_text:
        return tex_text
    return map_outside_protected(
        tex_text, lambda s: s.replace("<<", "«").replace(">>", "»"))


def number_equations(tex_text):
    r"""Number display equations and resolve ``\eqref``/``\ref`` to those numbers.

    Pandoc cannot number display equations, so an ``\eqref{eq:x}`` has nothing to
    resolve against and is emitted as the literal text ``[eq:x]`` — an internal
    artifact in the reader's face. Numbering the ``equation`` environments here
    (as LaTeX would: starred ones are skipped) lets the reference become a real
    number, and appends the number to the formula so it can be found.
    """
    numbers = {}
    counter = [0]

    def number_row(row):
        """One numbered line: strip its label, remember the number, show it."""
        counter[0] += 1
        n = counter[0]
        for lm in re.finditer(r"\\label\{([^}]*)\}", row):
            numbers[lm.group(1)] = n
        row = re.sub(r"\\label\{[^}]*\}", "", row)
        if r"\nonumber" in row or r"\notag" in row:
            counter[0] -= 1                        # LaTeX skips these
            return re.sub(r"\\(nonumber|notag)", "", row)
        return row.rstrip() + f"\\qquad({n})"

    def number_env(m):
        env, body = m.group(1), m.group(2)
        if env in ("equation", "multline"):        # one number for the block
            body = number_row(body.strip())
        else:                                      # align/gather: one per row
            rows = re.split(r"(\\\\)", body)
            body = "".join(number_row(p) if i % 2 == 0 and p.strip() else p
                           for i, p in enumerate(rows))
        return f"\\begin{{{env}}}{body}\\end{{{env}}}"

    # Starred environments (equation*, align*) are unnumbered in LaTeX — skip them.
    numbered = "|".join(("equation", "align", "gather", "multline", "eqnarray",
                         "alignat", "flalign"))
    tex_text = re.sub(r"\\begin\{(%s)\}(.*?)\\end\{\1\}" % numbered,
                      number_env, tex_text, flags=re.DOTALL)

    def resolve(m):
        cmd, key = m.group(1), m.group(2)
        if key not in numbers:
            return m.group(0)          # not an equation ref — pandoc resolves it
        n = numbers[key]
        return f"({n})" if cmd == "eqref" else str(n)

    tex_text = re.sub(r"\\(eqref|ref)\{([^}]*)\}", resolve, tex_text)
    if numbers:
        print(f"equations numbered: {counter[0]} ({len(numbers)} referenceable)")
    return tex_text


def materialise_nomenclature(tex_text, source=""):
    r"""Build the list of abbreviations that ``\printnomenclature`` would print.

    The ``nomencl`` package collects ``\nomenclature{term}{definition}`` entries
    scattered through the document and typesets them where ``\printnomenclature``
    sits. Pandoc knows neither command, so the whole section — in a thesis, every
    abbreviation the reader needs — silently vanishes from the .docx. The entries
    are in the source, so emit them as a definition list instead.

    Same class of problem as ``glossaries``/``acronym``/``makeindex``: a package
    that *generates* content at typeset time produces nothing under pandoc.
    """
    entries = []
    out, i = [], 0
    token = "\\nomenclature"
    while True:
        j = tex_text.find(token, i)
        if j == -1:
            out.append(tex_text[i:])
            break
        out.append(tex_text[i:j])
        k = j + len(token)
        sort_key = ""
        if k < len(tex_text) and tex_text[k] == "[":       # optional sort key
            end = tex_text.find("]", k)
            sort_key = tex_text[k + 1:end]
            k = end + 1
        args = []
        for _ in range(2):
            while k < len(tex_text) and tex_text[k] in " \t\n":
                k += 1
            if k < len(tex_text) and tex_text[k] == "{":
                end = _match_group(tex_text, k)
                args.append(tex_text[k + 1:end - 1])
                k = end
        if len(args) == 2:
            entries.append((sort_key, args[0], args[1]))
        i = k
    tex_text = "".join(out)

    if not entries:
        return tex_text

    m = re.search(r"\\renewcommand\*?\{\\nomname\}\{([^}]*)\}", source)
    title = m.group(1) if m else "Nomenclature"
    entries.sort(key=lambda e: e[0])                       # the key LaTeX sorts on
    items = "\n".join(rf"\item[{term}] {definition}" for _, term, definition in entries)
    block = (f"\\section*{{{title}}}\n"
             f"\\begin{{description}}\n{items}\n\\end{{description}}\n")

    if re.search(r"\\printnomenclature", tex_text):
        # lambda replacement: `block` is full of backslashes that re.sub would
        # otherwise read as escape sequences.
        tex_text = re.sub(r"\\printnomenclature(\[[^\]]*\])?",
                          lambda _m: block, tex_text, count=1)
    else:                                                  # no print command: append
        tex_text = tex_text.replace(r"\end{document}",
                                    block + "\\end{document}", 1)
    print(f"nomenclature: {len(entries)} entries materialised as '{title}'")
    return tex_text


def clean_bib(bib_path, work_dir):
    r"""Copy a .bib with ``%``-commented lines removed.

    Biber tolerates ``%`` comment lines in a .bib file, so real bibliographies
    routinely carry commented-out entries. Pandoc's BibTeX parser does not, and
    aborts the whole conversion with "unexpected %". Dropping whole comment
    lines (never a ``%`` inside a field value) makes the file parseable without
    changing any entry.
    """
    text = bib_path.read_text(encoding="utf-8", errors="replace")
    kept = [ln for ln in text.splitlines() if not ln.lstrip().startswith("%")]
    if len(kept) == len(text.splitlines()):
        return bib_path                      # nothing to do; use the original
    out = work_dir / bib_path.name
    out.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return out


MINIMAL_PREAMBLE = r"""\documentclass[12pt]{article}
\usepackage[T1,T2A]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[russian,english]{babel}
\usepackage{graphicx}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{hyperref}
"""


def needs_flattening(raw):
    r"""Is this a multi-file document sitting on a template preamble?

    Two signals, either of which is decisive:

    * the preamble ``\input``s other files — that is a template loading its style
      chain, and pandoc will try to *interpret* all of it, which is what makes it
      consume unbounded memory;
    * the body ``\include``s chapters — the content (and its figures) is not in
      this file at all.

    Detected automatically because the failure it prevents is brutal: pandoc
    grinding through gigabytes of RAM until it is killed, with no hint as to why.
    """
    split = re.search(r"\\begin\{document\}", raw)
    preamble = raw[:split.start()] if split else raw
    body = raw[split.end():] if split else ""
    preamble_inputs = re.search(r"\\input\{", strip_comments(preamble))
    body_includes = re.search(r"\\include\{", strip_comments(body))
    return bool(preamble_inputs or body_includes)


def flatten_document(raw, tex_dir, title=None, author=None):
    r"""Rebuild a template-heavy multi-file document as one pandoc-safe file.

    Documents built on large templates (memoir-based thesis templates, book
    classes) load their preamble from a chain of style files full of TeX
    programming. Pandoc tries to interpret all of it and can spend unbounded
    memory doing so. None of it matters for Word output — page geometry, fonts,
    and GOST layout do not survive the conversion anyway. So the preamble is
    replaced with a minimal one and only the document *body* is kept, with all
    ``\input``/``\include`` files inlined.
    """
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", raw, re.DOTALL)
    if not m:
        raise ValueError("no \\begin{document} ... \\end{document} found")

    # Carry over the author's own math operators (\DeclareMathOperator) from the
    # discarded preamble — without them, any formula using \argmin, \tr, … falls
    # back to raw TeX in Word. Other template macros are deliberately NOT carried
    # over: thesis templates redefine \alpha, \le, … for national typography, and
    # those definitions break pandoc's math reader.
    preamble_src = expand_inputs(strip_comments(raw[:m.start()]), tex_dir)
    operators = re.findall(r"\\DeclareMathOperator\*?\{[^}]*\}\{[^}]*\}", preamble_src)
    ops = "\n".join(operators)
    if operators:
        print(f"math operators carried over: {len(operators)}")

    skip = TITLE_INCLUDES if title else frozenset()
    body = expand_inputs(strip_comments(m.group(1)), tex_dir, skip=skip)
    body = sanitise_template_noise(body)
    # Title/author go through the LaTeX source, not pandoc's --metadata: on
    # Windows a non-ASCII value passed on the command line gets mangled by the
    # console codepage before pandoc ever sees it.
    head = ""
    if title or author:
        head = (f"\\title{{{title or ''}}}\n\\author{{{author or ''}}}\n"
                "\\date{}\n")
        body = "\\maketitle\n" + body
    return (MINIMAL_PREAMBLE + ops + "\n" + head + "\n\\begin{document}\n" + body
            + "\n\\end{document}\n")


# --------------------------------------------------------------------------- #
# Step 4: pandoc
# --------------------------------------------------------------------------- #
def check_pandoc():
    if not shutil.which("pandoc"):
        sys.exit("Error: pandoc not found on PATH. Install pandoc >= 2.x.")
    v = subprocess.run(["pandoc", "--version"], capture_output=True, text=True)
    print(f"Using {v.stdout.splitlines()[0]}")


def write_metadata_file(metadata, work_dir):
    """Write pandoc metadata as UTF-8 YAML.

    Passed on the command line, a non-ASCII value (a Russian toc-title, say) is
    mangled by the Windows console codepage before pandoc sees it. A file is
    read as UTF-8 regardless.
    """
    path = work_dir / "metadata.yaml"
    lines = ["---"]
    for key, value in metadata.items():
        escaped = str(value).replace('"', '\\"')
        lines.append(f'{key}: "{escaped}"')
    lines.append("---")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_pandoc(clean_tex, bibs, csl, resource_dir, output, toc=False, metadata=None,
               timeout=900):
    cmd = [
        "pandoc", str(clean_tex),
        "--standalone",
        "--wrap=preserve",
        f"--resource-path={resource_dir}",
        "-o", str(output),
    ]
    if toc:
        cmd += ["--toc", "--toc-depth=3"]
    if metadata:
        meta_file = write_metadata_file(metadata, clean_tex.parent)
        cmd += [f"--metadata-file={meta_file}"]
    if bibs:
        cmd += ["--citeproc"]
        for b in bibs:
            cmd += [f"--bibliography={b}"]
        if csl:
            cmd += [f"--csl={csl}"]
    print("Running:", " ".join(cmd))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        sys.exit(
            f"pandoc timed out after {timeout}s. This usually means it is trying to "
            "interpret a heavy template preamble — rerun with --flatten."
        )
    if r.returncode != 0:
        print("STDERR:", r.stderr, file=sys.stderr)
        sys.exit(f"pandoc failed with exit code {r.returncode}")
    if r.stderr.strip():
        print("pandoc warnings:\n" + r.stderr.strip()[:2000])


# --------------------------------------------------------------------------- #
# Step 5: verify the output
# --------------------------------------------------------------------------- #
def verify(output):
    """Report embedded media and native equations in the produced .docx."""
    with zipfile.ZipFile(output) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        doc = z.read("word/document.xml").decode("utf-8", "ignore")
    n_math = doc.count("<m:oMath")
    n_img = doc.count("<a:blip")
    size_mb = output.stat().st_size / 1024 / 1024
    print("\n--- verification ---")
    print(f"output          : {output}")
    print(f"size            : {size_mb:.2f} MB")
    print(f"embedded media  : {len(media)} file(s)")
    print(f"inline images   : {n_img} <a:blip> reference(s)")
    print(f"native equations: {n_math} <m:oMath> block(s)")
    return {"media": len(media), "images": n_img, "equations": n_math,
            "size_mb": round(size_mb, 2)}


# --------------------------------------------------------------------------- #
def convert(tex_path, output=None, bib=None, csl=None, dpi=300, keep_clean=False,
            flatten=None, toc=False, metadata=None, refs_title="References"):
    tex_path = Path(tex_path).resolve()
    if not tex_path.exists():
        sys.exit(f"Error: {tex_path} not found.")
    tex_dir = tex_path.parent

    check_pandoc()

    output = Path(output).resolve() if output else tex_path.with_suffix(".docx")
    work_dir = output.parent / f"{tex_path.stem}_tex2docx_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    raw = tex_path.read_text(encoding="utf-8", errors="replace")

    # 1/2: clean copy
    metadata = metadata or {}
    if flatten is None:                    # auto: decide from the source itself
        flatten = needs_flattening(raw)
        if flatten:
            print("detected a multi-file document on a template preamble "
                  "-> flattening (pass --no-flatten to override)")
    if flatten:
        clean = flatten_document(raw, tex_dir,
                                 title=metadata.pop("title", None),
                                 author=metadata.pop("author", None))
        n_files = len(re.findall(r"\\(input|include)\{", raw))
        print(f"flattened: inlined \\input/\\include from the master file "
              f"({n_files} direct references), minimal preamble substituted")
    else:
        clean = strip_comments(raw)
    # The whole source, \input chain included: some things a rule needs to know
    # (the document language, \nomname) live in a file the master only includes.
    expanded = expand_inputs(raw, tex_dir)
    clean = materialise_nomenclature(clean, expanded)
    clean = relocate_caption_labels(clean)
    clean = number_equations(clean)
    # The <<…>> ligature only exists for certain languages; look for it in the
    # *original* source (with its \input chain), since flattening throws the
    # template preamble — and its \usepackage[russian]{babel} — away.
    if uses_guillemet_ligature(expanded):
        clean = convert_guillemets(clean)
    clean = ensure_references_heading(clean, refs_title)

    # 3: figures
    clean, converted, kept, missing = process_graphics(clean, tex_dir, work_dir, dpi)
    print(f"figures: {kept} raster kept, {converted} vector rasterised to PNG"
          + (f", {len(missing)} unresolved" if missing else ""))
    if missing:
        for mss in missing:
            print(f"  ! figure not found: {mss}", file=sys.stderr)

    # bibliography — one or many (biblatex documents often use several)
    if bib:
        bibs = [Path(b).resolve() for b in bib]
    else:
        bibs = find_bibliography(raw, tex_dir)
    for b in bibs:
        if not b.exists():
            sys.exit(f"Error: bibliography {b} not found.")
    bibs = [clean_bib(b, work_dir) for b in bibs]
    print(f"bibliography: {', '.join(str(b.name) for b in bibs) if bibs else 'none found'}")

    clean_tex = work_dir / f"{tex_path.stem}.clean.tex"
    clean_tex.write_text(clean, encoding="utf-8")

    # 4: pandoc
    run_pandoc(clean_tex, bibs, csl, tex_dir, output, toc=toc, metadata=metadata)

    # 5: verify
    stats = verify(output)

    if not keep_clean:
        shutil.rmtree(work_dir, ignore_errors=True)
    else:
        print(f"kept intermediates in {work_dir}")
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tex", help="source .tex file")
    ap.add_argument("-o", "--output", default=None, help="output .docx path")
    ap.add_argument("--bib", default=None, action="append",
                    help="bibliography .bib; repeat for several (auto-detected if omitted)")
    ap.add_argument("--flatten", dest="flatten", action="store_true", default=None,
                    help="force flattening: inline every \\input/\\include and replace the "
                         "template preamble with a minimal one. Auto-detected for "
                         "multi-file documents on a template; this only overrides.")
    ap.add_argument("--no-flatten", dest="flatten", action="store_false",
                    help="never flatten, even if the document looks like a thesis")
    ap.add_argument("--toc", action="store_true",
                    help="add a Word table of contents")
    ap.add_argument("--toc-title", default=None,
                    help='heading for the contents (default: pandoc\'s "Table of '
                         'Contents"; use e.g. "Оглавление" for a Russian document)')
    ap.add_argument("--refs-title", default="References",
                    help='heading placed above the reference list '
                         '(e.g. "Список литературы")')
    ap.add_argument("--title", default=None, help="document title (overrides the source)")
    ap.add_argument("--author", default=None, help="document author")
    ap.add_argument("--csl", default=None,
                    help="CSL style file (default: pandoc author-date); pass a "
                         "numeric CSL to match numbered [1] citations")
    ap.add_argument("--dpi", type=int, default=300,
                    help="rasterisation DPI for vector figures (default: 300)")
    ap.add_argument("--keep-clean", action="store_true",
                    help="keep the intermediate clean .tex and rasterised PNGs")
    args = ap.parse_args()
    metadata = {}
    if args.title:
        metadata["title"] = args.title
    if args.author:
        metadata["author"] = args.author
    if args.toc_title:
        metadata["toc-title"] = args.toc_title
    convert(args.tex, args.output, args.bib, args.csl, args.dpi, args.keep_clean,
            flatten=args.flatten, toc=args.toc, metadata=metadata,
            refs_title=args.refs_title)


if __name__ == "__main__":
    main()
