---
name: paper-claim-audit
description: Use when a manuscript, preprint, thesis chapter or revision must be checked against its own sources before submission or resubmission - numbers in the text against scripts and output files, figure descriptions against the figures and data, Methods against the code, and mentions of the same result against each other. Also when the user says "сверь статью с данными", "проверь числа в статье", "откуда это число", "проверь перед подачей", "аудит рукописи", "сходятся ли текст и рисунки".
---

# Paper claim audit: every claim against its source, effort fixed in advance

## Overview

An audit fails in two ways. It stops early: "cannot verify" is written where ten minutes of
recomputation would have settled the number. And it ends as an avalanche: twelve items at the
top, so the author cannot tell which three decide the paper. The rules below fix the effort
before the audit starts and the shape of the result before it is written.

Checking claims against sources is the job. Reading the paper and judging whether it is
convincing is a review: for that use paper-big-picture. This skill uses its closed-book pass
and its limit of three decisive items.

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

## Step 3. The findings file: its parts, in this order

1. **Decisive, at most three.** The discrepancies that change a main claim or a Discussion
   conclusion. Each: one plain sentence of what is wrong, then the text value, the source
   value, the source path, the node id, "checked" or "guess". Choose by consequence for the
   paper, not by size of the discrepancy. If more than three qualify, keep the three with the
   largest consequence and put the rest first in part 2.
2. **The reviewer will ask** - one line each: where, text says, source says, path.
3. **Questions for the author** - framing, choice of method, how a figure looks: matters of
   judgement, stated as questions, never as errors.
4. **Not checked** - each item with the reason (longer than 15 minutes, no source, source
   changed after version).
5. **Effort** - helpers used; wall-clock time from timestamps of files or logs, not from
   your own estimate: the map and the audit separately.

Deliver the findings file and the map beside it: the map file, its parts, the anchored copy
and the last `check` report. Do not edit the manuscript or any file outside your output folder.

## Common mistakes

| mistake | fix |
|---|---|
| "Cannot verify: would need recomputation" for a cache-based number | recompute if it fits in 15 minutes |
| value taken from a script written after the version | check modification date; find the source as of the version |
| twelve items in the top tier | three; the rest one line each in part 2 |
| only the first mention checked | every mention of the result, including figure panels and Discussion |
| a contradicting earlier verdict taken as settled | report the data beside the verdict |
| a judgement call reported as an error | move it to questions for the author |
| a ledger table kept beside the map | one ledger: the map |
| a `check` finding reported without opening the source | verify it; the map can be wrong too |
| time "about an hour" by feel | timestamps |
