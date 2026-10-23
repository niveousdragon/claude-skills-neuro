---
name: paper-claim-audit
description: Use when a manuscript, preprint, thesis chapter or revision must be checked against its own sources before submission or resubmission - numbers in the text against scripts and output files, figure descriptions against the figures and data, Methods against the code, and mentions of the same result against each other. Also when the user says "сверь статью с данными", "проверь числа в статье", "откуда это число", "проверь перед подачей", "аудит рукописи", "сходятся ли текст и рисунки", "можно ли подавать", "что из находок критично".
---

# Paper claim audit: every claim against its source, effort fixed in advance

## Overview

An audit fails in two ways. It stops early: "cannot verify" is written where ten minutes of
recomputation would have settled the number. And it ends as an avalanche: twelve items at the
top, so the author cannot tell which three decide the paper. The rules below fix the effort
before the audit starts and the shape of the result before it is written.

Checking claims against sources is the job. Reading the paper and judging whether it is
convincing is a review: for that use paper-big-picture. This skill uses its closed-book pass
and its limit of three: every CRITICAL is shown, and of the HIGH three are explained.

## Step 0. Before opening anything

1. Closed-book pass from paper-big-picture: the claim, the load-bearing result, the senior
   reviewer's question.
2. **Fix the version.** Name the manuscript file and its date. For every source you will use,
   record path, modification time and sha256. A script modified after the manuscript date may
   not be what produced its numbers: mark it "changed after version" and look for the old copy
   (archive folder, git history, a cache written before the date).
3. **Fix the effort**, and write the plan at the top of the findings (what was actually spent
   goes to part 5 of Step 3):
   - one helper per figure (and one for Methods, if long), at most four at a time; what does not
     fit into four you take yourself, with Introduction, Discussion and the cross-checks between
     places;
   - **recompute any number whose recomputation from caches or raw data fits in about 15
     minutes.** "Cannot verify" is allowed only when it would take longer or the source does
     not exist, and the findings say which;
   - the whole paper: every section, every figure panel, every Methods subsection.

Building the map is most of the work: a whole-paper audit takes hours. Where the harness offers
background workers that outlive the turn, run it as one.

## Step 1. The ledger is the paper map

Build it before judging anything. **REQUIRED SUB-SKILL:** paper-map. If the project already
keeps a map of this version, update it instead of starting over; the map outlives the audit and
answers the author's next question, "what does fixing this touch".

Each node is a ledger row:

| ledger field | in the map |
|---|---|
| result | node `claim` and `value` |
| source | `sources`: file with sha256, or commit and path; date from Step 0 |
| value in source | the source's `value`, read from the file, never from memory or from the text |
| population | node `scope`: what it was computed on - which sessions, animals, neurons, threshold, shuffles |
| mentions | `mentions`: every place it appears - Abstract, Results, Discussion, caption, figure panel, Methods - each with the population the text claims there |
| depends on it | `supports` with `holds_while`, and the nodes whose `uses` name it |

Statements without a number (a figure "shows a gradient along the axis", a treatment "leaves
firing rates unchanged", a preprocessing step "was not applied") are nodes too: their source is
the figure, the numbers of the comparison, the code path.

When the map is clean, run `check`. Its findings - MISMATCH, SCOPE, CONFLICT, BROKEN,
INCONSISTENT, AFTER-VERSION, UNSOURCED - are the first candidates for Step 2, each verified at
the source before it is reported.

## Step 2. Checks, node by node

`check` has done the arithmetic of agreement: text against value, mentions against each other,
sources against value, the conditions of the argument. What remains needs you:

- **Source.** Value in source equals value in text, at the stated precision.
- **Population.** The text's population equals the computed one. A number from one cohort
  presented as both cohorts' is a finding even when the arithmetic is right.
- **Mentions.** All mentions agree with each other, including figure panels and old values
  left in the Discussion.
- **Descriptions.** A description of a figure matches the figure itself and its data; open
  the image.
- **Controls.** A claim about what a control shows matches the control's numbers.
- **Methods against code.** Parameters, thresholds, units, rates, the stages that were
  actually run.
- **Provenance.** A source marked "changed after version" that disagrees with the text is
  reported as a provenance question, not as an error of the text.

Write each confirmed discrepancy into the map: a number into the source's `value`, a
disagreement in words (another estimator, other sessions, another split) into `disagrees` on
that source. Then the argument page shows it under every main claim it weakens.

An earlier verdict by the author or a previous reviewer is not evidence. If the data
contradict it, report the data and quote the earlier verdict beside them.

## Step 3. Levels, then the findings file

**Levels.** Every finding of `check` and every hole of its ARGUMENT section gets a level by the
four questions of paper-map (MAP_FORMAT.md, Levels): CRITICAL - the paper's own data refute a
main claim, or it is left without support that can be checked; HIGH - a statement of the paper
is false; MEDIUM - not false, but not shown; LOW - form only. `check` proposes a default by the
type of the finding. Record your reading in the map's `triage`, so that it survives the next
version of the paper: each finding checked (when, by whom, against what) or a guess, a moved
level with its reason, a finding of your own reading as `NOTE`.

- **No CRITICAL reaches the author without an independent check.** A fresh helper verifies
  each one against the code and the data. It gets the statement of the finding and the paths
  to the manuscript, code and data - not the map and not your triage. Not confirmed: the level
  goes down, with the reason.
- **While the author has not confirmed the main claims, every CRITICAL is preliminary**,
  relative to the proposed claims. A CRITICAL that rests only on a condition you wrote
  (`holds_while`) goes to the author as a question: is this what the claim needs?
- Expect most findings at HIGH: every false number or sentence is one. That is why only three
  of them are explained below.

**The findings file: its parts, in this order.**

1. **Verdict, the first line**, from `check` after triage: "do not submit: N CRITICAL", "can be
   submitted; N HIGH recommended to fix", or "clean"; "preliminary" while the main claims are
   not confirmed.
2. **Every CRITICAL**, however many. Each: one plain sentence of what is wrong and which main
   claim it refutes or leaves without support; the text value, the source value, the source
   path, the key; what the helper opened to confirm it.
3. **HIGH.** The three with the largest consequence for the paper, explained like a CRITICAL
   and checked by a fresh helper the same way. Choose by consequence, not by size of the
   discrepancy. The rest one line each, in the order of the paper: where, text says, source
   says, path, "checked" (and by whom) or "guess".
4. **MEDIUM**, in groups by kind - no source, a scope wider than computed, Methods against the
   code without a change of result, holes in the argument: one line per group, with the count
   and the places.
5. **LOW**: the count here; the list in a separate file beside the findings.
6. **Questions for the author** - framing, choice of method, how a figure looks: matters of
   judgement, stated as questions, never as errors. A CRITICAL resting only on your condition
   goes here.
7. **Not checked** - each item with the reason (longer than 15 minutes, no source, source
   changed after version). Name what the map does not see: a proofreading of the text
   (references to panels, wording) unless it was done. No CRITICAL does not mean a clean paper.
8. **Effort** - helpers used; wall-clock time from timestamps of files or logs, not from
   your own estimate: the map and the audit separately.

Deliver the findings file and the map beside it: the map file, its parts, the anchored copy
and the last `check` report. Do not edit the manuscript or any file outside your output folder.

## Common mistakes

| mistake | fix |
|---|---|
| "Cannot verify: would need recomputation" for a cache-based number | recompute if it fits in 15 minutes |
| value taken from a script written after the version | check modification date; find the source as of the version |
| twelve HIGH explained at the top | three explained; the rest one line each, in the order of the paper |
| a CRITICAL shown without an independent check | a fresh helper checks it against code and data, without the map |
| a CRITICAL against unconfirmed main claims shown as final | preliminary until the author confirms them |
| a level moved without a reason | `why` in the map's `triage` |
| only the first mention checked | every mention of the result, including figure panels and Discussion |
| a contradicting earlier verdict taken as settled | report the data beside the verdict |
| a judgement call reported as an error | move it to questions for the author |
| a ledger table kept beside the map | one ledger: the map |
| a `check` finding reported without opening the source | verify it; the map can be wrong too |
| time "about an hour" by feel | timestamps |
