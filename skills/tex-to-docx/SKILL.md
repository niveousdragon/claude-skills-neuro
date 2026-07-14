---
name: tex-to-docx
description: Use when converting a LaTeX (.tex) manuscript to a Word (.docx) file for a co-author, reviewer, or editor who does not use LaTeX — figures (including PDF/EPS), citations, cross-references, tables, and math must survive intact, and no LaTeX comments, TODO notes, or author annotations may leak into the output.
---

# tex-to-docx

## Overview

Turn a LaTeX manuscript into a Word file a non-LaTeX reader can open with
nothing lost. Core principle: **pandoc with `--citeproc` does the heavy lifting;
a preprocessing pass fixes the two things pandoc alone gets wrong** — vector
figures Word cannot render, and comments/annotations that must never reach the
reader.

The bundled [`tex2docx.py`](tex2docx.py) is the whole skill. Run it; it self-verifies.

## When to use

- Sending a paper to a co-author/editor/journal that wants `.docx`.
- The reader has no LaTeX experience and must see rendered figures, equations,
  numbered citations, and a reference list — not raw `\cite{}` / `$...$`.
- You need a **clean** copy: `%` comments, `% TODO`, and agent/author notes
  stripped so they are invisible in the final document.

Not for: producing a PDF (compile the LaTeX instead), or Word→LaTeX (reverse).

## Quick reference

```bash
# a paper (single file)
python tex2docx.py paper.tex                    # -> paper.docx next to the source
python tex2docx.py paper.tex --csl vancouver.csl   # numbered citations

# a thesis or book (many files, heavy template)
python tex2docx.py dissertation.tex --flatten --toc \
    --toc-title "Оглавление" --refs-title "Список литературы" \
    --title "…" --author "…" --csl gost.csl -o thesis.docx
```

| Flag | Purpose |
|------|---------|
| `-o/--output` | Output `.docx` path (default: source name with `.docx`) |
| `--bib` | Bibliography; auto-detected from `\bibliography`/`\addbibresource` (incl. inside `\input`ed files). Repeat for several databases |
| `--csl` | Citation style file; default is pandoc author-date. Pass a numeric CSL for `[1]`-style references |
| `--flatten` / `--no-flatten` | Force flattening on/off. **Auto-detected** for multi-file documents on a template — see below |
| `--toc` / `--toc-title` | Add a Word table of contents, with an optional localised heading |
| `--refs-title` | Heading above the reference list (e.g. `"Список литературы"`) |
| `--title` / `--author` | Title block (used instead of a template title page) |
| `--dpi` | Rasterisation DPI for vector figures (default 300) |
| `--keep-clean` | Keep the intermediate clean `.tex` and rasterised PNGs for inspection |

## Flattening: theses and books on a big template

**This is automatic.** If the preamble `\input`s other files, or the body
`\include`s chapters, the document is flattened and you are told so. Force it
with `--flatten`, or turn it off with `--no-flatten`.

It is automatic because the failure it prevents is brutal and gives no clue what
went wrong: pandoc tries to *interpret* a template preamble full of TeX
programming and grinds through gigabytes of RAM until it is killed. (A real
memoir-based thesis template took pandoc to 18 GB.) The second failure is quiet
and worse: without flattening, a master file that only `\include`s chapters
converts to a `.docx` with **no chapters and no figures** in it, and nothing
warns you.

Flattening inlines every `\input`/`\include` recursively — so the comment
stripper and the figure rasteriser see the *whole* document — and swaps the
template preamble for a minimal one. Nothing is lost by that: page geometry,
fonts, and national layout do not survive into Word anyway.

What is carried across, and what is deliberately not:

- **Carried:** the author's `\DeclareMathOperator` definitions, so `\argmin` and
  friends still render as math rather than raw TeX.
- **Not carried:** template macros that redefine `\alpha`, `\le`, … for national
  typography. They break pandoc's math reader — this is why the whole preamble
  is not simply harvested.
- **Dropped only if you replace it:** a template's hand-built title page is prose
  glued together by preamble macros, so it renders as debris. It is dropped only
  when `--title` supplies a replacement — never silently, since a chapter could
  legitimately be named `title.tex`.

## What the script guarantees

1. **Clean copy first.** It strips every `%` comment (honouring escaped `\%`)
   and drops pure-comment lines, then feeds *that* copy to pandoc. No comment,
   TODO, or author note survives into the `.docx`. It also relocates any
   `\label` sitting *inside* a `\caption{...}` to just after the caption —
   pandoc would otherwise print the label as literal text (e.g.
   `[tab:comparison]`) in the reader-facing caption. Numbering is preserved, so
   `\ref` still resolves to "Table 1" / "Figure 1".
2. **Figures Word can render.** `\includegraphics` targets in `.pdf`/`.eps`/`.ps`
   are rasterised to PNG (PyMuPDF, falling back to `pdftoppm`); every graphics
   path is rewritten absolute so figures resolve regardless of pandoc's cwd.
   Raster figures (`.png`, `.jpg`, …) pass through untouched.
3. **Citations resolved.** `--citeproc` + the `.bib` builds real reference
   entries and an end-of-document reference list — no bare `\cite{}` keys.
4. **Native math, with numbered equations.** Pandoc emits Word OMML equations.
   Pandoc cannot *number* display equations, so an `\eqref{eq:x}` would surface
   as the literal text `[eq:x]`. The script numbers them as LaTeX would —
   `equation`/`multline` get one number, `align`/`gather` one per row, starred
   environments and `\nonumber` rows get none — and resolves the references.
5. **Readable punctuation.** LaTeX's `<<…>>` quote ligature becomes real « », but
   **only** for a language where that ligature exists (babel/polyglossia russian,
   french, …) and **only** in prose. Inside math or code `<<` is a shift operator
   or a comparison (`$a << b$`, `cout << x`), and rewriting it there would
   silently corrupt the document.
6. **Parseable bibliographies.** `%`-commented lines are stripped from a copy of
   each `.bib`: biber tolerates them, pandoc's parser aborts on them.
7. **Self-verifies.** After conversion it reports embedded media count, inline
   image references, and native-equation count so you can confirm nothing dropped.

## Requirements

- **pandoc ≥ 2.x** on PATH (`pandoc --version`).
- **PyMuPDF** (`pip install pymupdf`) for figure rasterisation. If absent, the
  script falls back to `pdftoppm` (bundled with MiKTeX/poppler) for PDFs.

## Verifying a conversion worked

The script prints a verification block. A healthy conversion shows embedded
media ≈ the number of figures and a nonzero equation count for a math paper.
To double-check any `.docx` by hand:

```python
import zipfile
z = zipfile.ZipFile("paper.docx")
media = [n for n in z.namelist() if n.startswith("word/media/")]
doc = z.read("word/document.xml").decode("utf-8", "ignore")
print("figures:", len(media), "equations:", doc.count("<m:oMath"))
```

Then open the `.docx` and spot-check: figures visible, equations rendered,
citations replaced by author/number + a reference list, no `%`/TODO text.

## Common mistakes

| Symptom | Cause / fix |
|---------|-------------|
| Figure box empty in Word | Vector figure not rasterised — install PyMuPDF; check the `figures:` line reports it as "rasterised". |
| `figure not found` warning | `\includegraphics{name}` path unresolved — run from a dir where relative paths resolve, or fix the path in the source. |
| Bare `[@key]` / `\cite` in output | No `.bib` found — pass `--bib`. |
| Citations author-year but journal wants `[1]` | Pass a numeric `--csl` (e.g. a Nature/IEEE CSL). |
| A sentence truncated at a `%` | Genuine unescaped `%` in the source; it should be `\%`. The cleaner honours `\%` and only cuts true comments. |
| Custom macro renders as raw command | Define it with `\newcommand` in the preamble (pandoc expands those); pandoc cannot expand macros pulled from external `.sty`/`.cls` files. Content of unknown custom environments still passes through. |
| Citation style is author-year but journal wants numbered | Pass a numeric `--csl`. A `vancouver.csl` (numbered, eLife/biomed style) ships next to this skill: `--csl vancouver.csl`. For a Russian thesis use a GOST CSL. |
| pandoc hangs / eats gigabytes of RAM | A template preamble it is trying to interpret. Flattening is auto-detected; if you passed `--no-flatten`, drop it. |
| Whole chapters or most figures missing | Multi-file document that was not flattened — force `--flatten`. |
| `[eq:foo]` in the text | An `\eqref` to a display equation in an environment the numberer does not know. `equation`, `align`, `gather`, `multline`, `eqnarray` are covered. |
| Title page renders as debris | A template title page whose macros lived in the discarded preamble. Pass `--title`/`--author`; it is then dropped and replaced. |
| `Error reading bibliography … unexpected "%"` | Commented-out entries in the `.bib`; the script strips them from a working copy automatically. |
