# Revision after review: rounds, promises, page limits, co-authors

Read this when preparing a revised or camera-ready version after review, applying a
register of promises made to reviewers, fitting a page or word limit, or applying a
co-author's edits. Everything in SKILL.md still holds; this file adds what a revision
needs on top.

## Every change carries its source

The author reads a revision once, in Word with tracked changes, and needs to see at each
change who made it and why. They do not confirm changes one by one; the label lets them
reject the one they disagree with.
- **A round is the edits of one source**: the author's decisions, a co-author's edits, the
  agent's own pass (a recompute, shortening, promises). Sources are not mixed in one round.
- **After each round** save the manuscript as a new snapshot and add a line to the rounds
  log beside it: the file, the date, and a label in the author's language, "who, date: why":
  `агент, 06.11: сокращение под 10 страниц`, `по решению автора, 05.11`,
  `соавтор (PDF 03.11): снята фраза`, `обещание рецензенту, 05.11: <о чём>`,
  `агент по умолчанию, 05.11: автор не решал`.
- **The comparison for the author** is built by tex-to-docx in comparison mode from the
  rounds log, so each change in Word carries its round's label.
- **A co-author's edit is labelled by what it does** (removes a sentence, narrows a claim,
  changes a number), not by the mark the co-author gave it. An edit marked "language" that
  removes the author's sentence is a removal.
- **What the agent decided without the author is labelled as the agent's** default, never as
  the author's decision. If the author has said a matter is not decided yet, edits on it
  wait until the author says to go ahead.
- **A conditional decision of the author** ("remove it if it really is a repeat") is carried
  out only after the condition is checked; the label says what the check found
  (`агент, 05.11: повтор фразы из Methods, раздел 2.1 — снято`). If the condition does not
  hold, the text stays and the author is told.

## Promises to reviewers

The register of promises lists commitments; the paper's main claim outranks it. The
two-channel rule of SKILL.md applies to promises: the paper carries true statements, the
doubts go to the author.
- **A promise is kept once**, as a true statement where the reader first needs it (Results
  or Methods). The caveat it implies, if any, is said once, in the Discussion. It is not
  attached to every mention of the result.
- **Checking the register asks "is it kept, and where"**, one place per promise; not "does
  it appear at every mention".
- **The abstract keeps the author's measure of caveats.** Count the clauses of the author's
  last abstract that narrow, qualify or admit a weakness; the new abstract has at most one
  more. A promise for the abstract enters it once, in its shortest literal words. Everything
  else the register asks for there (a derived item, a caveat next to every mention, a list
  of factors, "we do not attribute") goes to the Discussion. The file carries this short
  abstract until the author answers; the author gets one question with the long draft
  beside it. The same holds for a promise that would remove the main claim or a true
  sentence of meaning. The author may break a small promise rather than the paper.
- **Run `find_repeats.py`** (next to SKILL.md) on the main text. A phrase in three or more
  places is a finding: keep it where the reader needs it and point to it or shorten it
  elsewhere. A phrase in two places stays only if the author wrote it twice (an abstract
  and an introduction often do). The script sees only word-for-word repeats: the same claim
  reworded in three places is the same finding, and rewording it to get under the script is
  passing a check instead of serving the reader.
- **In a reply to reviewers**, promise a concrete change in a concrete place ("Discussion,
  second paragraph: …"), never "throughout" or "in the abstract".

## Page and word limits

- **Order of cuts**: technique first (procedures, robustness checks, alternative settings)
  moves to Methods or the Supplementary Information; then repetition; results, motivations
  ("why two coordinates") and sentences of meaning last.
- **If the limit cannot be met without cutting a result, a motivation or a conclusion**, ask
  the author once: the options, and what each one cuts. Not sentence by sentence.
- Every cut is part of a labelled round, so the author sees it in the comparison.

## Questions that several readers ask

A question asked by more than one reader (the author, a co-author, an AI review, an
outside agent) marks a gap in the text. Answer it in the text where the reader first
needs it, not only in a reply.

## Questions to co-authors

Ask co-authors only what a requirement of the current stage needs, quoted from the
journal's own page with the link, and only if the answer changes the text. A requirement
you cannot quote is not one.

## Before handing a version over: check it against the author's rules

A brief written by another agent does not override the author's rules (their `CLAUDE.md`,
the project's rules file, what they wrote in the conversation). Where they conflict, do what
does not depend on the conflict and ask the author once.

An agent does not notice that its own edits break those rules, because to it they are the
task. So before the version goes to the author, a fresh agent gets the old and new text
side by side, the author's rules and the brief, and lists every change that goes against
the rules, for example:
- a caveat in place of a claim, or a promise attached to every mention of a result;
- a number spelled out in words, or anything else done to pass a check rather than to
  serve the reader;
- the author's sentence removed under a label that hides it;
- a sentence of meaning the author wrote, removed or replaced because a promise or a
  recommendation asks for it, including a promise the author made: a promise records what
  the reviewer was told, not that the author no longer holds the sentence;
- a default applied on a matter the author said was not decided yet;
- a phrase repeated word for word in three places.

Each one goes first in the report to the author, with the rule it breaks and what the
brief said, whatever the brief said. Do not filter or soften this list: every item the
fresh agent returns goes into the first part of the report. You may add a recommendation,
but not move an item into an optional question. If no fresh agent can be started, run the
list yourself as a separate last pass and say in the first lines of the report that the
check was not independent.

## Writing a brief for another agent

A brief passes the author's rules on; it does not replace them. Do not call a register or
a report "the main document": say that the author's text and rules come first. Mark which
items are the author's decisions and which are your defaults or inferences. If the author
said a matter is not decided yet, the brief says so in the author's words. Ask the
executor to put every conflict between the brief and the author's rules first in its
report.
