---
name: paper-big-picture
description: Use when writing or editing any text of a scientific paper, abstract, thesis, grant or reply to reviewers (rebuttal), when reviewing or critiquing a manuscript, and when triaging reviewer or automated-tool comments. Also when the user says "напиши результаты/дискуссию/абстракт", "ответ рецензенту", "отрецензируй", "что главное в замечаниях", "разбери рецензии", or when academic-research-skills (ARS) produces drafts, reviews or revisions.
---

# Paper: big picture first, true claims instead of caveats

## Overview

Two failures, one cause. A model weights every detail equally, so it reviews a paper like
a linter and writes it like a defendant: fifteen technical items instead of the one
question that decides the paper, and caveats instead of true claims. Human reviewers hold
far less in memory, and that forces them to the fundamental questions: *what does this give
beyond what we had?* and *is what was measured what is claimed?* This skill imposes that
bottleneck on purpose.

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
- A claim stronger than the data becomes a narrower **true** claim: change the scope (which
  system, which condition), not the confidence. A significant result is called a result.
- Numbers and statistics go in Results as measurements. Discussion states the meaning,
  numbers optional.
- Methods state the procedure as fact ("neurons were selected over the whole session"),
  with no verdict on it.
- A requested prediction is given as a prediction, with wide bounds.
- Limitations contain what the author chose to put there. Things not done are not mentioned.
- Rebuttal: concede what the reviewer raised and what is true, at its true scope. Do not
  bring up weaknesses nobody raised.

**Before handing over Part 1, sort it.** Go through it sentence by sentence and label each
one: *result* (what was measured or shown), *meaning* (what it establishes), or *doubt*
(a weakness, a missing control, a caution, an admission). Every *doubt* sentence is moved
to Part 2, including a whole limitations paragraph and an opening concession in a rebuttal.
A Limitations paragraph stays only if the author's draft already had it or the author asked
for it.

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
   Others: is the measured quantity the claimed one; does the conclusion survive. Each is
   one plain-words question a human reviewer would ask aloud, plus at most three sentences:
   why it decides the outcome and what answer would settle it. Estimators, statistics and
   prior-work citations that support it go to part 3.
3. **Everything else**: one line per item. A claim from an automated tool about the data or
   a figure is checked against the data before it is accepted.

When the user is the author, the best answer to a decisive question is usually a
reframing or one targeted analysis, not a programme of new experiments.

## Precedence over other skills

This skill overrides academic-research-skills (ARS) and any template it uses:
- unresolved review items are reported to the author; they are not written into
  "Acknowledged Limitations";
- quotas of weaknesses or limitations ("3-5", "at least 2-3 improvements") are ignored;
- the "use hedging language when evidence is weak" fallback is replaced by Step 2a.

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
