---
name: report
description: Use when asked to assemble a human-readable report, summary, write-up or overview of results on a topic — for the operator who wants to go through an agent's results systematically, or for an outside reader (a colleague, student, co-author, reviewer) who has not seen the conversation. Also when the user says "собери отчёт", "сделай репорт", "pdf отчёт с результатами", "саммари по результатам", "опиши, как устроено", "чтобы человек понял", "для внешнего читателя".
---

# Report

## Overview

A report is read by someone who was not inside the agent's work. Pick the mode by one question: **will the reader have seen this conversation?**

- **Yes → operator report.** The reader knows the project but not what the agent read, ran and concluded. Goal: they understand the result and make the decision at hand. It is a decision document, not a record of the work.
- **No, or unsure → external report.** The reader has nothing but the document. Goal: they understand the subject and can act on it without asking anyone.

**Both modes produce the same kind of file: a LaTeX source compiled to a PDF, with every figure inside the document.** A report is read page by page, next to its figures; a `.md` with figure paths in the text is not a report. Write `.md` only if the user asked for markdown by name — and even then embed each figure with `![…](relative/path.png)`, never leave it as a path.

## Step 1. Facts before prose

1. **Name the central object from the primary source, in one sentence, before writing.** For "how X works" that is the function users actually call (find it through callers, examples, tests), not the helpers it calls. For results it is the latest run the project relies on, not a superseded one.
2. **Every number has a file behind it.** When a summary note and the analysis tables disagree, the tables win; say so in the fact sheet. Keep a fact sheet beside the report: claim → file and line/table/log. A claim without a source is removed or marked as the agent's judgement.
   - Report on results: no reruns of the analysis. Arithmetic on existing tables is allowed and marked "derived" in the fact sheet.
   - Report on how something works: the numbers and examples come from a script saved next to the report; its output is the source.
3. **For every "A beats B" claim, check that B is a fair baseline** (same neurons, same data, same denominator). A comparison inherited from the analysis files is not checked just because it is in a file.
4. **Figures are rebuilt by a script saved next to the report**, from those same files, into `figures/` beside the `.tex`: vector `.pdf` for plots, `.png` (≥150 dpi) for images and heatmaps, always with `bbox_inches="tight"` so labels are not cut off. Every results section and the worked example get a figure; a section without one says why (a single number, a table is clearer).

## Step 2. The shape

**Operator report** — 3–5 pages of body text, in this order:
1. **Что решить** — the decision the operator is making: the options, your recommendation, what happens by default. No decision pending → one line on what this result changes in their picture.
2. **Итог** — 3–5 numbered conclusions. Each is a bold one-line claim with the **one** number the decision rests on ("12 of 100 neurons") — or a pair, when the first means nothing without the second ("78 of 550, with 5 of 100 false finds"). Other numbers that make a conclusion trustworthy go to its figure or to Ограничения. Items 1–2 fit on the first page.
3. **Почему этому можно верить** — one paragraph: what was checked and how, in plain words. Terms the conclusions need are defined here, only those.
4. **По выводам** — a short section per conclusion that needs more than its line: one figure, a sentence or two. Skip a conclusion that its line already covers.
5. **Ограничения** — only those that could change the decision.
6. **Файлы** — paths to the data and scripts, one short list.

What stays out:
- **Superseded work.** Retracted checks, earlier versions, dead ends, the history of how the result was reached. If a conclusion the operator already saw is now reversed, one line in Итог: "прежний вывод X снят: …".
- **Numbers not needed for the decision.** Every number in the text answers "does the operator need it to decide or to trust the conclusion?"; if not, it goes to the fact sheet, not the PDF.
- **The fact sheet itself.** It is a separate file beside the PDF (`facts.*`), never a section of the report.

The operator's own principles (their `CLAUDE.md`: conclusion first, what is needed from them, plain fractions, no filler) apply to the report as written rules; if they define a report format, it overrides this one. Project names are fine; run ids and paths only in Файлы.

**External report:**
1. Title and one paragraph: what this is, for whom, what the reader can do after reading.
2. The subject in the order the reader needs it: what it does → what can be set → what comes out → a worked example with a figure → how well it works → for code, the neighbouring functions and how they differ. Every term the reader needs is defined at first use.
3. **Limitations and pitfalls, at the end**, only those of the central object, each checked against the source.
4. **Code and reproduction**, a separate last section: where it lives, the call, defaults, how to rebuild every figure.

It describes the subject as it is now. It never mentions our versions ("in the previous draft"), people, tasks, stages or run ids from our work, and it gives local paths only in the reproduction section. Names of functions the reader will call are fine anywhere. Timings and other machine-dependent numbers say so.

## Step 2b. The document

Start from this skeleton (compiles with pdfLaTeX, Cyrillic included):

```latex
\documentclass[11pt,a4paper]{article}
\usepackage{cmap}              % Cyrillic text stays copyable and searchable in the PDF
\usepackage[T2A]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[russian]{babel}   % drop for an English report
\usepackage[margin=2cm]{geometry}
\usepackage{graphicx,booktabs,xurl,hyperref}   % xurl: long Windows paths break at the margin
\graphicspath{{figures/}}
\begin{document}
...
\begin{figure}[htbp]\centering
  \includegraphics[width=0.85\linewidth]{result_1.pdf}
  \caption{What the reader should see in this figure, in one or two sentences.}
  \label{fig:result1}
\end{figure}
...
\end{document}
```

- Each figure is referenced from the text (`рис.~\ref{fig:result1}`) next to the claim it supports; the caption says what to look at, not only what is plotted.
- Tables go in `tabular` with `booktabs`, numbers copied from the fact sheet, not retyped. A table can stand in for a figure where exact values matter more than the shape.
- Russian text: quotes as `<<…>>` (prints «…»), not ``` ``…'' ```.
- Build: `latexmk -pdf -interaction=nonstopmode -halt-on-error report.tex` (or `pdflatex` twice, so references resolve).

## Step 3. Gates before hand-off

| Gate | Operator | External |
|---|---|---|
| Every number traced to the fact sheet (a separate file) | yes | yes |
| **PDF builds clean**: the build exits 0; the `.log` has no `undefined` references, no `File ... not found`; every file in `figures/` appears in the log as `<use figures/...>` or `<figures/...>` — a figure built but not included is an error. Count figures by the log, not by `pymupdf` `get_images()`: vector figures are not raster images and it reports 0 | REQUIRED | REQUIRED |
| **Look at the pages**: render every page to PNG (e.g. `pymupdf`: `page.get_pixmap(dpi=80)`) and view them; fix cut-off labels, unreadable fonts, figures pushed to the end, overfull tables | REQUIRED | REQUIRED |
| **Leak scan**: list every name specific to our conversation (people, task numbers, internal stage labels, run ids, nicknames, local paths); search the final text for each; fix every hit outside the reproduction section | — | REQUIRED |
| **Decision reader**: a fresh subagent gets only the PDF and the decision prompt below; every number it marks as not needed is removed from pages 1–2; if it cannot state the decision and your recommendation, rewrite page 1 | REQUIRED | — |
| **Naive reader**: a fresh subagent gets only the path to the final file (the PDF if there is one; the text itself if there is no file) and the naive prompt below; check each error it reports against the source before fixing | only if the report also goes to someone outside the conversation | REQUIRED |
| `avoid-ai-writing` in edit mode on the final text (for Russian text apply its structural patterns: filler, hedging, triads, promotional tone). Where it conflicts with the shape above, the shape wins: bold claims in Итог stay; a Russian dash stays where grammar requires it | yes | yes |
| The text cites literature → the bibliography is built with `bibliography-lockfile`, never typed from memory | if cited | if cited |

Decision-reader prompt: *"Read only the first two pages. Report: (1) the decision the reader of this report has to make, the options, and the author's recommendation, in your words; (2) every number on these pages you did not need to understand the decision or trust the recommendation; (3) anything you would have to read further to decide."* After cutting more than a sentence, run it once more on the new version. A fix after this reader never adds text to page 1 to answer "why" — that goes to По выводам.

Naive-reader prompt: *"You know nothing about the project or who wrote this. Read the document. Report: (1) what it is about and what you would do with it, in your words; (2) every term used before it is explained; (3) every place that refers to something you were not given; (4) every claim that looks wrong or unsupported; (5) what you still cannot do after reading."*

If the fixes after the naive reading were substantial, run it again. If you did not, say so.

## When another agent writes the report

If you hand the report to a worker or subagent, its prompt opens with: who reads it, and the decision they are making (options, your recommendation if you have one). Then the sources — the current results only, not the notes of retracted checks. Do not give it a list of things that "must be mentioned": the shape above decides what goes in. Tell it to use this skill in operator mode.

## Step 4. Hand-off

Deliver the PDF, with the `.tex`, `figures/`, the figure script and the fact sheet beside it, in the folder the user named (else the run's output folder). For Word, convert the same `.tex` with `tex-to-docx`. Tell the user the PDF's path first; if the hand-off message can show images, show the first page or the key figure. Then: which mode, which gates passed, what the naive reader found and what was fixed, which gate was not run, and the one decision needed from them.

## Common mistakes

| Mistake | Instead |
|---|---|
| The report is a `.md` with no figures, or with figure paths in the text | `.tex` → PDF with every figure included (Step 2b); `.md` only on explicit request, with figures embedded |
| Figures built, PDF compiled, but a figure never made it in or its labels are cut off | The build and look-at-the-pages gates |
| The report is built around a helper or an old run because it came up first in the conversation | Step 1.1: name the central object from callers and usage |
| The external text mentions the person, the task, internal stages, "as discussed" | Leak scan; the reader has no access to our conversation |
| Problems open the external document; the limitations list is inflated with neighbouring code | Limitations at the end, only those of the central object |
| A comparison from the analysis files is repeated as is, though its baseline includes the very items being tested | Step 1.3: check the baseline before writing the claim |
| The operator gets numbers for a metric nobody defined ("held-out R² 0.21") | Что считали defines it first: what is held out, what 1 and 0 mean |
| Engineering slang and line numbers instead of meaning | Plain words in the text; line numbers in Файлы |
| "Checked by a naive reader" said about a version it never saw | Say which version was checked |
| 13 pages, eight numbers per conclusion, the operator cannot find what to decide | Что решить first; one number per conclusion; 3–5 pages; the decision reader |
| Retracted checks get their own sections "for honesty" | Superseded work stays out; one line only if it reverses a conclusion the operator saw |
| The fact table is printed at the end of the PDF | Separate file beside the PDF |
| A naive reader asks for more definitions, the operator report grows after each pass | For operator reports the decision reader is the gate; it removes, not adds |
