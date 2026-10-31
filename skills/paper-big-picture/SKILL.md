---
name: paper-big-picture
description: Use when writing or editing any text of a scientific paper or its Supplementary Information (including a recompute, review fixes or journal-format changes applied to a manuscript), abstract, thesis, grant or reply to reviewers (rebuttal), when reviewing or critiquing a manuscript, and when triaging reviewer or automated-tool comments. Also when the user says "напиши результаты/дискуссию/абстракт", "ответ рецензенту", "отрецензируй", "что главное в замечаниях", "разбери рецензии", or when academic-research-skills (ARS) produces drafts, reviews or revisions.
---

# Paper: big picture first, true claims instead of caveats

## Overview

Three failures, one cause. A model weights every detail equally, so it reviews a paper
like a linter, writes it like a defendant and edits it like an auditor: fifteen technical
items instead of the one question that decides the paper, caveats instead of true claims,
and with every pass one more checkable number and one less sentence that says what
follows, until the paper reads like a technical report. Human reviewers hold far less in
memory, and that forces them to the fundamental questions: *what does this give beyond
what we had?* and *is what was measured what is claimed?* Human readers tire, so they need
one message per paragraph. This skill imposes both bottlenecks on purpose.

Honesty has two channels and they do not mix:
- **with the author** — every doubt, weakness and risk, stated plainly and first;
- **in the paper** — true claims about what was shown. The author decides what else enters.

## Step 1. Closed-book pass (always first)

Before writing, reviewing or triaging, write these four lines without looking back at the
material:
1. **Claim:** what the work establishes, in one sentence.
2. **Load-bearing result:** the one result that, if removed, makes the claim fall.
3. **The senior reviewer's question:** what a busy expert would ask first — usually *"so
   what, beyond existing methods?"* or *"is the measured quantity the claimed one?"*
4. **What bothers me most**, if anything.

Only then open the details, and use them to check these lines. A detail that changes none
of them is minor by definition.

## Step 2a. Writing paper text or a rebuttal

The output has two parts, in this order.

**Part 1: the text.** Each sentence states what was shown, at its true scope.
- A claim stronger than the data first gets the strongest **true** claim the data support,
  usually by setting the number against a reference the data actually compare it with: a
  control, a shuffle, an established method on the same cells. Never pair a number with a
  reference computed for a different quantity. Only if no such reference exists, narrow the
  scope (which system, which condition), not the confidence. A significant result is called
  a result.
- Before writing what the method covers or cannot do, search the project for the analyses
  that tested it (reports, benchmarks, earlier versions) and write the widest scope they
  support. A sentence about what the method cannot do is a *doubt* (see "Then sort it")
  unless the author wrote it.
- A feature of the method is described by what it enables ("detects place fields"), not as
  the repair of a deficiency ("makes place fields visible to the estimator"). A contrast
  ("unlike the main text", "has no explicit offset") tells the reader the other side has
  the thing; write it only if that is true. An analysis or a dataset is justified by what it
  gives (independent data, a known ground truth), not by a lack in the paper's own data
  that is not one.
- Numbers serve the message: see "The reader's budget" below. Discussion states the meaning
  without numbers unless the author asks for them.
- Methods state the procedure as fact ("neurons were selected over the whole session"),
  with no verdict on it. They are written for a reader who wants to understand and repeat
  the procedure: each step with what it is for, and the reader's budget holds there too.
  Command lines, file and script names, configuration names, random seeds and the tool's
  internals go to the code repository's README and one sentence in Code availability. So
  does a check of the implementation that changed nothing in the data (a condition that
  never fired, a test that the code computes what it should).
- Facts about the experiment (durations, frame or sampling rates, numbers of animals and
  sessions, which dataset a result comes from and whether two papers share it) come from
  the protocol, the recording's own metadata or the author, never from a software default,
  the analysis output alone or a similar setup. Something odd in them (two durations under
  one protocol) is a question to the author, not a sentence in Methods.
- A requested prediction is given as a prediction, with wide bounds.
- Limitations contain what the author chose to put there. Things not done are not mentioned.
- Rebuttal: concede what the reviewer raised and what is true, at its true scope. Do not
  bring up weaknesses nobody raised. An answer written for a reviewer, real or simulated,
  enters the paper only if the reader needs it: would it change what the reader does or
  concludes? If not, it stays in the reply.

**The reader's budget.** A paper is read by a person, not checked by a ledger. Its parts
have these shapes:
- **A Results paragraph** is (1) a sentence that states the finding in words; (2) the
  evidence: the one to three numbers that carry this finding, with the panel that shows
  them; (3) a sentence that says what follows from it for the paper's claim. A paragraph
  that opens an analysis starts with (0) why it was done: the question it answers. A rule,
  term or procedure gets what it is for at its first mention. Every other
  number the analysis produced goes to the figure, its data file, the Supplementary
  Information or Methods. A number a main claim of the paper rests on stays in the text.
  Before a result leaves the text, find the panel that shows it. A result no panel shows
  keeps one clause in the text; only its secondary numbers move out. The same holds for a
  result the recompute adds: a result no panel shows gets one clause in the text even if
  the old text did not have it.
- **A result in Results is written as a number**: a percentage or a count out of a total,
  beside what it is compared with ("24.6% of recorded neuron-sessions"). A quantity in words
  ("a quarter", "one in six", "nine in ten", "nearly half") belongs to the Discussion. The
  budget limits how dense the numbers are, not how they are spelled: a number in words
  lightens nothing, and `count_numbers.py` counts it.
- **Every control a result is tested against keeps one clause in the text**: what the result
  was compared with and that it held ("and better than its shuffled control in 27 of 29
  sessions"). Its spreads and test statistics go to the figure, its data file or Methods.
  A correction or a stricter threshold is not a control: it is another setting of the same
  result (see "One result is reported once").
- **"The same order" across two metrics** is written only if every pair is ordered the same
  way in both; otherwise name the one comparison that holds.
- **A number given at a chosen cut-off** says in a clause why that cut-off, or is replaced
  by the trend over the range the panel shows.
- **A result that departs from what the reader expects** (from another method, from another
  part of the paper, from what the design predicts, or only for some variables) carries its
  cause in a clause: measured, or a pointer to where the paper states it. Without one the
  reader takes it for an anomaly the authors could not explain. A cause that is only a
  hypothesis goes to the author with the place; the author decides whether it enters.
- **Results names what a procedure achieves** in one clause and points to Methods; its
  steps, criteria and thresholds are Methods. A criterion that decides which data enter a
  result (an inclusion threshold, how many were left out) stays in the text as one clause.
- **A figure caption** says what each panel shows and how to read it: axes, colours, what
  a line or a mark means, the scale in words ("logarithmic scale", not "log10" or "log").
  It uses no term the text has not introduced yet. Counts of outcomes (how many pairs were
  accepted, rejected, removed) and lists of values per threshold or condition leave the
  caption: they go to the figure's data file or the Methods subsection on the figure. When
  the journal requires n and the test in the legend, they take one closing sentence. How
  the data were produced (dataset, sessions, exclusions, clipping of extreme values) is
  Methods, not caption. A panel whose quantity is defined by a procedure points to the
  Methods subsection that defines it, under the same rule: only a subsection whose title
  you can see. Every threshold drawn in a panel is justified in a clause or pointed to the
  Methods subsection that justifies it.
- **One result is reported once**, at the author's chosen setting. An alternative setting
  (with and without a correction, with and without a threshold) goes to the Supplementary
  Information if the author wants it there. A number appears in one place in the main
  text.
- **A pointer to Methods names the subsection** when you can see its title: "(Methods,
  Temporal alignment)". If you cannot, write "(Methods)" and list the pointer for the author.
  Never invent a subsection, a figure data file or a supplementary item: a pointer to
  something that does not exist is a factual error. Moving a procedure's description from
  Results to Methods does not drop its citation: Results keeps one clause and the citation.
- **Journal requirements are followed.** A requirement counts only when it is quoted from
  the journal's own pages (author guidelines, formatting or reporting checklist) with the
  link; what other papers in the journal happen to do is a style, not a requirement. Meet
  it in the form that costs the reader least, and list it in the note to the author with
  the quote. Note the stage it applies to (initial submission, revision, accepted
  manuscript): a requirement of a later stage goes to the author's list for that stage and
  is not applied now. When meeting it means cutting or rewriting the author's text (a word
  limit, a reference limit, a required section), it is a proposal to the author, not an
  edit.
- **The Supplementary Information follows the same rules**, and it is read apart from the
  paper, by a reader who arrives from one pointer:
  - each section opens with the question it answers and names the claim of the main text it
    serves. A section that serves none is a question to the author (cut it or move it): a
    result attached for weight weakens the paper;
  - every term is defined at its first use in the SI, and every reference inside it carries
    the prefix ("Supplementary Table 3", "Supplementary Fig. 1"); a bare "Fig. 1" there
    reads as the main text's figure;
  - an analysis set up differently from the main text (another delay window, no threshold)
    says why in a clause, or the reader concludes the main setting failed there. A
    parameter both describe is given the same way in both;
  - another method is first described in words, what it does and what it is for; its
    settings, variants, counts and per-condition values go to tables. A result stated in
    the main text or elsewhere in the SI is pointed to, not repeated.
- **One spelling** everywhere (text, SI, captions, the labels drawn on the figures): the one
  the author chose; if the author has not said, the one of the title, stated in the note.
- **Measure it.** Report numbers per 100 words for each changed section, before and after
  the pass, with `count_numbers.py` next to this file (`python count_numbers.py OLD.tex
  NEW.tex`): one counting rule for every pass, so that labels and names such as "Stage 1",
  "F1" or "Fig. 2" are not counted as numbers. A rise is a change the author has to approve,
  with the reason.

**Before handing over Part 1, run three checks, each by a fresh agent.**
1. **Numbers against their sources**: every number introduced or changed (paper-claim-audit
   when the paper has a map). A criterion or procedure restated from the main text is quoted
   in full or pointed to, never shortened.
2. **The reader.** It gets each changed paragraph of Results and of the Supplementary
   Information alone and answers: what is its message, in one sentence; which numbers did
   it need for that; what would it ask the authors. Numbers it did not need move out,
   except a number a main claim rests on; a paragraph whose message it cannot state is
   rewritten; each question is answered in the text (a term defined, a cause given) or goes
   to the author. This check stands in for the author's reading between passes: the author
   reads the paper once or twice, not after every pass.
3. **Old against new.** It gets every changed sentence beside the sentence it replaced, and
   every removed paragraph, and answers three questions.
   - Does the new one claim more? A wider scope (all sessions where the old said one), a
     stronger verb (shows, proves, drives where the old said is consistent with, reflects,
     relates to), cause where the old had association, a general statement where the old
     had a measurement. Each "yes" is reverted to the old scope, or goes to the author if
     the data support the wider claim.
   - What did the old say that the new no longer says? Why an analysis was done, what a
     result means, a whole result. Each loss is restored, or its removal goes to the
     author as a proposal.
   - Did the new replace the author's own wording while it was true and broke no rule of
     this skill? Restore it. Wording that breaks a rule stays rewritten; the note shows the
     author both.

   Shortening invites all three. A new sentence of meaning, with nothing old beside it, is
   checked against every result of the paper and the SI that bears on it (the map's
   mentions, the synthetic tests), not only against its own paragraph.

Then run avoid-ai-writing in detect mode over the new and changed sentences, and over the
whole text when the task is to make it read well; fix what it finds without touching the
author's terms.

**Then sort it.** Go through it sentence by sentence and label each one: *result* (what was
measured or shown), *meaning* (what it establishes), or *doubt* (a weakness, a missing
control, a caution, an admission). Every *doubt* sentence is moved to Part 2, including a
whole limitations paragraph and an opening concession in a rebuttal. A Limitations
paragraph stays only if the author's draft already had it or the author asked for it.

**Part 2: note to the author**, separate, in the user's language. Every concern goes here:
circularity, missing controls, weak statistics, a claim you believe is wrong. If you think
the central claim does not hold, that is the first line of the note — **the thesis is never
conceded inside the text**; the author decides.

| Weak draft | True claim |
|---|---|
| "Activity partly reflects speed... the effect is modest (r = 0.25)" | Results: "r = 0.25, p < 0.001; shuffled r = 0.01". Discussion: "The population encodes running speed." |
| "We agree the increase is expected" | "It is expected where the system is trained on the measured variable (the network). The animals had no task and no training signal; the measure could have stayed flat, and it rose." |
| "r = 0.70 but not significant; inconclusive" | "(Spearman 0.70, n = 5, directional)" |
| "might... we prefer not to commit to a shape" | "We predict a segmented trajectory: at each task switch relevance for the old task steps back." |

## Step 2b. Reviewing a paper or triaging comments

The output has three parts, in this order.
1. **Verdict** in one sentence, as the area chair would write it.
2. **Decisive questions, at most three.** The first is always the significance question:
   *what does the reader learn here that existing methods or known results did not give?*
   Others: is each comparison with another method made on equal terms; is the measured
   quantity the claimed one; does the conclusion survive; can a reader follow the message
   without wading through numbers. Each is one plain-words
   question a human reviewer would ask aloud, plus at most three sentences:
   why it decides the outcome and what answer would settle it. Estimators, statistics and
   prior-work citations that support it go to part 3.
3. **Everything else**: one line per item. A claim from an automated tool about the data or
   a figure is checked against the data before it is accepted.

Before the verdict on a whole paper, sweep it, SI included, for results that depart from
expectation with no cause stated (paper-claim-audit, "Unexplained results"): an unexplained
gap between two methods is often an unequal comparison.

When the user is the author, the best answer to a decisive question is usually a
reframing or one targeted analysis, not a programme of new experiments.

## Step 2c. Editing the author's text

**Whose text it is.** The author's text is the author's own last version, plus every later
decision the author stated explicitly; a later decision outranks an older sentence. Text a
previous agent pass introduced is not the author's. If you cannot tell which is which,
compare with the author's last version or ask once.

A task to make the text ready, clean or readable names the reader's budget and, for the
Supplementary Information, its rules: applying them to Results paragraphs, captions and
every SI paragraph, including agent-introduced text, is the task itself. A sentence that
breaks one of them (a contrast that is not true, a term used before it is defined, a
justification by a lack the paper's data do not have, a verdict in place of what was shown)
is rewritten, not kept as the author's.

Every pass over existing text (a recompute, review fixes, journal format, shortening) has
this output:
1. **The changes the task names.** A real pass (a batch of the author's comments, a review,
   a recompute) goes into a new version of the file; a small fix (a sentence, a few
   numbers, one panel) goes into the version in progress, with a line in its log.
2. **Everything else you would change, as proposals**: old text quoted, new text, one line
   why. Not applied.

These belong to the author and change only on the author's explicit word:
- the abstract, the title, section and subsection headings;
- the figures: a recompute changes the data in the figure's own script, not its layout,
  style, fonts, panel letters or its width in the manuscript. The example shown (a cell, a
  trial, a session) is the author's choice; when a new one is needed, propose two or three
  that show the effect clearly, from sessions where the behaviour was well sampled, with
  the criterion they were picked by. Any change to a figure is shown to the author,
  old and new side by side, before it enters the manuscript. A problem found in an old
  figure (an example from another experiment, a wrong label) is reported to the author,
  not fixed silently;
- the author's own terms ("nonparametric", "detected events"), as long as they are true;
- citations, and the sentences that carry them. Cutting references to a limit is a
  proposal that quotes every sentence that would lose its citation or disappear;
- the sentence that says what a result means, as long as it is true and is a meaning. If
  the current data or figures contradict it, if the method contradicts it (it says a
  structure emerges from, or is driven by, elements the analysis did not take as input), if
  it only restates the results, or if it reads a positive result as a near-negative one,
  the text gets the strongest true meaning the data support (Step 2a), and the author sees
  the old and the new sentence side by side. A sentence the data contradict is never kept
  for the author's sake. A figure preview checks panel names and pointers; it is not a
  source of results. A feature the text states and the preview does not show (a bar too
  small for the axis, a point outside the drawn range) is not a contradiction: keep the
  sentence and ask the author to check the panel. Never rewrite a result from measuring the
  pixels of a preview.

An author's sentence restored after a recompute is checked against the new data and figures
like any other. Changes are shown to the author by meaning, old and new text side by side,
never as a count ("26 edits, +80 words").

A review or a simulated referee panel produces proposals. Its revised manuscript is never
the base of the next version.

When the author decides a matter of style or form, write it as a general rule in the
project's rules file, worded for every case of its kind ("keep the design, change only the
data" holds for every figure). The next pass reads that file first.

## Precedence over other skills

This skill overrides academic-research-skills (ARS) and any template it uses:
- unresolved review items are reported to the author; they are not written into
  "Acknowledged Limitations";
- quotas of weaknesses or limitations ("3-5", "at least 2-3 improvements") are ignored;
- the "use hedging language when evidence is weak" fallback is replaced by Step 2a.

Checking skills (paper-map, paper-claim-audit) verify the numbers that are in the text; they
never add one. A fix of their finding corrects or removes a number; it does not bring new
ones in.

## Red flags: the sentence belongs in the note to the author

- "written so that it does not overclaim"
- "the reviewer will notice anyway"
- "if it weakens the argument, better drop it than strengthen it"
- "we agree... we will remove / soften / present as case studies"
- "partially", "modest", "weakly", "may be", "should be interpreted with caution",
  "underpowered", "not tested", "future work should"
- "the effect was partial rather than complete", "one contributing node rather than the
  sole...", "contributes to" in place of the claim the data show

If no true strong phrasing exists, ask the author with a proposed rewording. Do not write
the caveat.

## Red flags: the paragraph has become a report

- a sentence chaining numbers, or a caption listing counts
- a number written in words in Results ("a quarter", "one in six")
- an analysis with no sentence on why it was done; a motivation or a whole result gone
  after shortening
- seeds, command lines or file names in Methods; a fact about the recording taken from a
  software default
- the same result given with and without a correction or a threshold
- "(Methods)" with no subsection while the subsection's title is in view
- a sentence about what a result means replaced by a more exact restatement of the result
- a figure redrawn, its example replaced, a heading reworded or a citation dropped that
  the task did not name
- the method's scope narrowed with no search for the analyses that tested it
- the revised manuscript of a review taken as the new base
- a result rewritten from what a figure preview seems to show
- a shortened sentence that claims more than the one it replaced
- an SI section that serves no claim of the main text; an SI term never defined; a bare
  "Fig. 1" inside the SI; a result that differs from another method with no cause stated
- an implementation check that decided nothing, or an answer to a reviewer, in Methods
