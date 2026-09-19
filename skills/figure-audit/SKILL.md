---
name: figure-audit
description: Use when a figure is being prepared for or checked before journal submission — sizing to a journal column (single, 1.5, double), font sizes at print size, fonts not embedded or Type 3, file format, compression, dpi or file size the journal accepts, text overlapping or cut off, or journal figure rules (Nature, Nature Neuroscience, Cell/Neuron, eNeuro, PLOS, eLife). Also when the user says "подготовь рисунок для журнала", "проверь рисунок перед подачей", "подходит ли рисунок под требования", "в одну колонку / в полторы колонки".
---

# Figure audit

## Overview

Journal figure rules are specific and differ between journals: Nature caps text at 7 pt, but PLOS requires at least 8 pt. Nature says not to outline text, while eNeuro wants vector text converted to outlines, or a TIFF. PLOS rejects a TIFF that is not LZW-compressed. Recalling these from memory gets some of them wrong, and nothing in a finished PNG shows it. This skill replaces memory with a table read from each journal's page, and replaces "looks fine" with a scripted audit of the figure at its printed size.

## Workflow

1. **Get the journal's rules from the table, not from memory.** Run `python figaudit.py journals` in this skill's folder. Each row gives the widths with their column keys, the maximum height, text sizes, fonts, panel-letter case, the file format and dpi, the file-size limit, other rules, and the page they were read from.
   - If the journal is not in the table, find its figure-guidelines page and read the numbers there. Pass them as `width_mm=` and tell the user where they came from.
   - If you cannot reach the page, say so and ask the user. Never fill the gap with a neighbouring journal's numbers.
2. **Copy `figaudit.py` next to the figure script.** The figure must rebuild after this session ends and on a colleague's machine (see `share-figure`).
3. **Build at the final size.** Call `fa.use_style(journal)` first. Then use either of:
   - `fa.subplots(journal, column, height_mm=...)`, which uses constrained layout;
   - your own layout with `figsize=fa.size(journal, column, height_mm=...)`, for example the single master GridSpec from `figure-alignment`.

   If panels must align, `figure-alignment` decides the layout and this skill decides the size, fonts and file. Never build large and scale down: every font and line shrinks with the figure.
4. **Save with `fa.save(fig, stem, journal, column)`.**
   - It writes only the formats the journal accepts, at the journal's dpi (`dpi=` overrides it), with no `bbox_inches="tight"`. TIFFs come out RGB and LZW-compressed.
   - It also writes `<stem>_preview.png` for looking at, never for submission.
   - It prints `FIGURE AUDIT … clean` or a list of problems. `ERROR` means fix and save again, until the audit is clean. `CHECK` means look at the item and decide, then tell the user what you decided.
5. **For a figure made in Prism, Illustrator or R**, audit the exported file instead.
   - A PDF: `python figaudit.py pdf Figure2.pdf --journal nature --column 1`. It checks the width, Type 3 and unembedded fonts, the font family, text sizes, panel-letter case and size, and line widths. It needs `pymupdf`. It does not see colormaps, titles or overlaps; open the file and look at those yourself.
   - A TIFF: `python figaudit.py tiff Fig2.tif --journal plos --column text`. It reads the header only: printed size, dpi, alpha channel, compression and file size. Text cannot be checked from pixels.
   - Without the source, you cannot deliver a fixed file. The result is a numbered list of fixes, each tied to the journal rule it breaks, plus an offer to rebuild the figure if the user sends the script or data.
6. **Hand over.** Report the following to the user:
   - the file to submit, and why that format;
   - the audit result;
   - what you could not check: the journal's page if it was not reachable, a missing font on this machine (say so; do not install fonts without asking), and the content rules below.

## Quick reference (checked 2026-09-19; the script's table is authoritative)

| Journal (`journal`) | `column` keys → width | Text | Submit |
|---|---|---|---|
| `nature` | `"1"` 89, `"1.5"` 120, `"2"` 183 mm | 5–7 pt; panel letters 8 pt bold lowercase a, b | PDF with fonts embedded (Type 42), not outlined |
| `natneurosci` | `"1"` 89 (Portfolio guide; the journal page gives none), `"max"` ≤180 mm | as `nature` | as `nature` |
| `cell` (Neuron, Cell Rep, …) | `"1"` ≤85, `"1.5"` ≤114, `"2"` ≤174 mm | ≥5 pt (not stated) | Arial only, fonts embedded; ≤20 MB |
| `eneuro` | `"1"` ≤85, `"1.5"` ≤116, `"2"` ≤176 mm | ≥5 pt (not stated) | TIFF ≥300 dpi RGB, or EPS with text outlined; no two-bar graphs; no top or right axis lines |
| `plos` | `"text"` 132, `"page"` 190.5 mm (min 66.8) | 8–12 pt, Arial/Times/Symbol | TIFF, LZW, 300–600 dpi, ≤10 MB |
| `elife` | `"min"` ≥100, `"page"` ≥200 mm | — | 300 dpi, RGB |

**Other Nature Portfolio titles.** The Portfolio figure guide, which is row `nature`, applies to all of them. Each title's own author page can add limits: Nature Neuroscience caps the width at 180 mm. Use a title's own row when it has one; otherwise use `nature` and read the title's page.

**Panel letters.** Use lowercase for Nature, where the table says so. Where the table says "not stated", match what the manuscript text uses ("Fig. 2A" → `uppercase=True`).

J Neurosci belongs to the same society as eNeuro, but its page was not reachable when the table was built. Read it before assuming the eNeuro numbers apply.

## What the audit does not check

The audit does not judge:
- whether the statistics are right (n and the unit of analysis, the test used);
- whether every abbreviation is explained in the legend;
- scale bars on micrographs;
- whether the colours still read in greyscale.

Look at these yourself and name them in the hand-over.

## Common mistakes

- Submitting a PDF to a journal that accepts only TIFF or EPS. The format rule is part of the journal's row in the table.
- Saving a TIFF with Pillow's `compression="tiff_lzw"`. On some installations its libtiff crashes Python outright; `fa.save` writes LZW without it.
- Using 6–7 pt text, which is fine for Nature, in a PLOS figure, where 8 pt is the minimum.
- Treating "the script ran" or "I looked at the PNG" as proof. Only the audit line counts.
