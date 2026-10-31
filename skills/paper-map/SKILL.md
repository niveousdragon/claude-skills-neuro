---
name: paper-map
description: Use when the argument of a LaTeX manuscript must be laid out, checked or kept intact - its main claims, what each rests on, the Discussion and the literature it answers to - and when anything a paper rests on is about to change - a reviewer's point, a revision, a threshold, a rate, an excluded animal, a re-run, a regenerated file - and someone must know what the change touches. Also when the user says "карта статьи", "граф аргумента", "ДНК статьи", "на чём держится вывод", "что заденет эта правка", "где в статье это число", "свяжи текст статьи с данными и кодом", "не разошлись ли текст и данные".
---

# Paper map: the argument of a paper, tied to its text and to its sources

## Overview

A paper is written to show a few main claims: its DNA. A paper map is the graph of that argument. Every
result is a node linked to the main claim it serves (why it was obtained), to the Methods and sources it
was computed from (how), to the Discussion positions that place it in the field, to the figures that show
it, to the prior work it extends, confirms or contradicts, and to other results. The map is a YAML file
beside the LaTeX manuscript; anchors (LaTeX comments, invisible in the PDF) tie each node to its places in
the text. `paper_map.py`, next to this file, checks the map and answers two questions: what holds each
main claim, and what does a change touch.

The map holds the paper together: every claim knows what it rests on and what rests on it, so a revision,
a re-run or a reviewer's point reaches every place it has to, and the text, the numbers and their sources
do not drift apart. Judging the argument - whether it convinces, what a reviewer will attack - is the work
of paper-big-picture; the map gives it the facts.

Two layers. The argument (main claims, results, Discussion, literature) is the point. The provenance
layer (methods, parameters, runs, files, code) makes it verifiable. Build the argument first.

The format, field by field, is in `MAP_FORMAT.md` next to this file. Read it before building.

## The main claims belong to the author

- Propose the main claims and put them to the author before building further: they are what the paper
  is written for. Record the author's agreement in `confirmed`.
- Never add, drop or reword a main claim, in the map or in the text, without the author's agreement.
- The conditions you put on supports (`holds_while`: what a claim needs from a number) are your reading
  of the argument. They go to the author together with the main claims.
- A sentence that restates a main claim is a mention of it. A restatement that adds scope or strength
  ("routine across all substrates") is a separate Discussion node with `restates` and `adds`, and its
  addition needs support of its own. This is where papers oversell.
- In a background run with no author at hand: build on the proposed claims, leave them unconfirmed, and
  put them first in the report as the question to the author.

## When to use

- Writing, revising or answering reviewers: what rests on what, and what a change touches.
- Before an analysis is re-run, a parameter or an inclusion criterion changes, or a source is regenerated.
- An audit of the paper: paper-claim-audit uses the map as its ledger.
- Not for a single number ("where does 34% come from"): open the script. Not for a paper without LaTeX
  source: anchors need it.

## The tool

Python 3 with `pyyaml`. Run it by its path, from the folder of this skill:

```
python <skill folder>/paper_map.py place-anchors MAP.yaml          anchored copy of the paper
python <skill folder>/paper_map.py check MAP.yaml --out R.txt      integrity, coverage, argument, findings, levels
python <skill folder>/paper_map.py argument MAP.yaml --lang ru     the page for the author: submission verdict, claims, what breaks them
python <skill folder>/paper_map.py impact MAP.yaml ID [ID ...]     what a change touches: claims at stake first
python <skill folder>/paper_map.py trace MAP.yaml ID               what a node rests on, down to files and code
python <skill folder>/paper_map.py strip IN.tex OUT.tex            remove anchors, for co-authors
```

Do not edit the tool to make a check pass. If it misreads something, note it beside the map and work
around it in the map.

## Building a map

1. **Fix the version and start the clock.** Manuscript file and date; code repository and commit; run
   folders. Write the start time into a file now: the cost of the map is measured from file timestamps.
2. **Main claims.** Read the Abstract, the end of the Introduction and the conclusion; write each main
   claim as a `dna` node with all its mentions. A broad claim ("the framework makes X routine", "the
   effect holds across systems") rests on many demonstrations: split it into the components the paper
   demonstrates one by one, each a `statement` that supports the claim, so that every demonstration has a
   place to attach. Mark selling restatements as above.
3. **Every result answers "why was it obtained?"** Link it with `supports` to the main claim or the
   component it serves; `says` tells how (a demonstration, a control, a robustness check, a comparison).
   Put `holds_while` where the support depends on a number: a control below a level, an effect above
   zero, a fraction above a half. A result that serves nothing: look for the link yourself first; what
   remains goes to the author with your proposal for each - the link is unclear, the result should go,
   or it should be strengthened.
4. **The Discussion returns to the main claims and the literature.** Its main thoughts (not every
   sentence) rest on a main claim or a component and relate to prior work with `relates`: `confirms`,
   `extends`, `contradicts`, `contrasts`, `uses`, `motivates`. A caveat or a limitation is linked to
   every claim it limits, so that a change of any of them reaches it. The questions of the Introduction
   are answered by results (`answered_by`); its claims about the field relate to the works it cites.
5. **How each result was computed: the lower layer.**
   - Every parameter the producing code uses is a `param` node, named in the text or not. One quantity is
     one node across all parts. Its sources are the places whose value reaches a result: the default
     where nothing overrides it, each override, each literal in a script.
   - Each analysis run is a `method` node that `uses` every parameter it was called with; each result
     computed from the run `uses` the run node.
   - `uses` by the counterfactual rule: if X changed, would this value change? Answer from the code.
   - A quantity in physical units converted with another parameter (a duration with a sampling rate, a
     distance with a pixel size, a figure axis in seconds) `uses` that parameter.
   - `checks` for two values that must agree and are not computed from each other; never `supports`.
   - A source's `value` holds only the numbers the source gives for this node; an explanation goes to
     `locator`. A disagreement that is not a number (another estimator, other sessions, the training set
     where the text says the test set) goes to `disagrees` on that source, not to `note`: it is a finding
     and reaches the argument page. A place you know but cannot open (a library outside the allowed
     folders, data on another machine) is a source with `unavailable` and the reason.
6. **Every mention.** The Abstract, each Results sentence, captions, figure panels (`figure`, `panel`,
   `shows`), the Discussion repeating a number, Methods restating a parameter. A result reported as a
   bound ("p < 0.001") gets `bound`; numbers in words get `verbal: true` with digits in `states`. A data
   or code availability statement is a claim, not a `skip`.
   - A sentence often carries more than one claim. A claim asserted in passing inside another result's
     sentence is a mention of its own node there too: two anchors on one sentence are fine.
   - A claim made inside a description of a method ("the pipeline produces compression through the
     dimensionality of the probe") is a `statement` of its own, not part of the method node.
   - Passing mentions are where maps miss. Before an edit that rewords a claim, also search the text for
     its key words.
7. **Anchor and check until clean.** `place-anchors`, then `check`. Clean means no integrity errors and
   no paragraph without an anchor. `check` reads the whole document, the appendix after the references
   included; sections left out on purpose, or mapped only in part, go to `coverage_exclude` (anchors
   inside them are still checked). It does not follow `\input`: when the Supplementary Information or a
   part of the paper lives in its own file, map a merged copy, or every restatement of a main-text
   result in the SI stays outside the map. Findings (MISMATCH, SCOPE, CONFLICT, BROKEN, INCONSISTENT,
   OVERSTATED) and the ARGUMENT section are for the author: keep them. In the Abstract, Results,
   Discussion and captions, a number outside the quote of every mention is a missed mention, or not a
   claim at all (a figure number). Two parameters set on the same line to the same value are usually one
   parameter written twice: merge them; if they are different parameters, say so in `distinct_from`.
   Never delete a true source to silence a warning.
8. **Read the argument page and try the links.** `argument` writes the page the author reads first: each
   main claim, its verdict, what breaks it, what the data say against its support, what it rests on, the
   Discussion and literature around it, and the questions only the author can answer. `--lang` translates
   the frame of the page; claims appear as written in the map, so write the argument layer in the
   author's language. For every parameter that more than one analysis uses, run `impact`: every result of
   those analyses must be in RECOMPUTE.
9. **Record the cost**: start and end from file timestamps, beside the map.

Split the work by figure: each helper writes one part file (`parts:` in the map). Before the helpers
start, the lead writes the main claims and their components, and the shared part: datasets, analysis
runs, shared parameters. Helpers attach their results to these and never define their own copy. A whole
paper takes hours: where the harness offers background workers that outlive the turn, build it in one.

## Using a map

- **Show the author the argument page first**, and after every revision.
- **Before an edit, a re-run or an answer to a reviewer:** `impact` on the nodes that change. It starts
  with the main claims at stake and whether their supports still hold; then what to recompute, rewrite
  and re-read, and every place in the code that sets a changed value. Confirm each place before editing
  it or dropping it.
- **An edit of the paper is an edit of the text and the map together.** It is done when `check` is clean
  again. Re-pin a sha256 only after checking the new value.
- **When the paper moves to a new version:** work on a copy of the map. For each changed piece of the diff,
  run `impact` on the nodes whose mentions sit in the changed text while the map still points at the old
  version; update claims, values and quotes, add nodes for new claims, remove the nodes whose claims are
  gone. Then point `paper` at the new version, `place-anchors` and `check` until clean. Places `impact` names
  that the diff did not touch go to the author as possibly missed. In `disagrees` and `locator`, refer to
  anchors rather than line numbers: line numbers go stale with every version.
- **After sources change:** `check` marks them STALE and lists what depends on them as RE-CHECK.
- **A finding goes to the author, not into the text.** OVERSTATED, a number missing from a mention,
  a sentence of meaning without its own support: each is a question to the author. Fixing a finding
  corrects or removes a number; it never adds a number to the text and never narrows the sentence
  that says what follows. The map checks truth, not readability: an edit that follows it is read
  again under paper-big-picture.
- **Levels of the findings.** `check` gives every finding a default level - CRITICAL, HIGH, MEDIUM, by what
  the reader loses (MAP_FORMAT.md, Levels) - and a verdict on submission. Your reading goes into `triage`:
  each finding checked or a guess, a moved level with its reason, your own findings from reading as
  `NOTE`. How the levels are verified and shown to the author: paper-claim-audit, Step 3.
- **"Where does this come from":** `trace`. **For co-authors:** `strip`.

## Common mistakes

| mistake | fix |
|---|---|
| main claims decided or reworded by the agent | proposed, then confirmed by the author in `confirmed` |
| a broad claim left with a few wordy supports | components, each with the demonstrations that serve it |
| a selling restatement mapped as a main claim | `restates` + `adds`; the addition needs its own support |
| results mapped, but not what each one is for | every result `supports` a claim or a component, or goes to the author as a question |
| a result linked to a claim just to empty the list | leave it unlinked and ask the author |
| the Discussion mapped as free-standing positions | main thoughts rest on a main claim and `relates` to the literature |
| a caveat tied to one claim while it limits two | link it to every claim it limits |
| a claim asserted in passing, or inside a Methods description, left inside another node | a mention of its own node, or a `statement` of its own |
| conditions of supports presented as the author's | they are proposals and go to the author with the main claims |
| each result listing a run's parameters itself, some dropped | a run node that uses them all; results use the run |
| the same parameter defined in two parts | one node in the shared part |
| a duration, a distance or an axis not linked to the rate or size that converts it | `uses` the converting parameter |
| a condition that two values agree written as `supports` | `checks` |
| an explanation written into a source's `value` | numbers only; the explanation goes to `locator` |
| a disagreement in words kept in `note`, where nobody sees it | `disagrees` on the source |
| a true source deleted to silence a warning | different parameters on one line: `distinct_from` |
| only the first mention of a number mapped | every place, including Discussion repeats and figure panels |
| `impact` output taken as the answer | it proposes; each place is confirmed |
| a level moved by feel, or kept in a report beside the map | the four questions; a moved level carries `why` in `triage` |
| text edited and the map left behind | edit both; `check` until clean |
| a finding closed by adding a number or narrowing a sentence of meaning | a question to the author; the text changes only with the answer |
| build time "about an hour" by feel | file timestamps |
