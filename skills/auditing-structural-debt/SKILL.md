---
name: auditing-structural-debt
description: Use when auditing a whole codebase for architectural decay rather than reviewing a diff for correctness — accumulated tech debt, duplication, coupling, god modules, dead code, complexity growing with no deliberate simplification. Use before a major release, before someone else inherits an analysis pipeline or it ships alongside a paper, on a fast-built or agent-written codebase, or when asked about DRY/SOLID violations, tangled boundaries, or whether the system is getting harder to change.
---

# Auditing structural debt

## Overview

Diff review asks *is this change correct?* This audit asks *what has the accumulation of correct
changes done to the system?* Every commit that produced the debt already passed review. That is
why the debt is invisible to every per-change tool you have.

**A finding is not a principle violation. It is a priced prediction about the next change.**
"Violates SRP" is a sermon — unfalsifiable, unactionable, and true of all code. "Adding a task
state requires edits in six files; the last two additions each missed one and shipped a bug" is a
finding: checkable, rankable, and it names its own fix.

This audit **diagnoses only**. It never edits code. Remediation is a separate, deliberate task
with its own plan and tests. Stay inside the repository under audit — its code, its history, its
documents. Live user data outside it (working directories, real databases, credentials) is off
limits unless the user asks; if you touch anything outside the repo, say so in the coverage
statement. Scratch scripts go in a temp directory, never in the tree you are auditing.

## Why this exists

Lehman's second and seventh laws of software evolution say that as a system evolves its complexity
rises and its quality declines — **unless work is done to hold them back**. That clause is the
whole point. It is not a claim about badly written code; it holds for systems where every single
change was correct. And it describes *work*, which means it needs an owner, a trigger, and an
artifact. Where it has none of the three, the laws stop being tendencies and become guarantees.

Feature work has all three by default: someone asks for it, a spec says what it is, a test proves
it landed. Complexity reduction has none of them, and its success looks like nothing happening,
slightly faster. Work with no visible artifact does not get scheduled — so the ratio of what is
added to what is removed stays exactly where it is. That ratio is the disease in one number.

Fast-built and agent-written codebases hit this harder, and not because the code is worse; it is
often better commented and better tested than average. It is that every session is locally optimal
and globally blind. A session sees its task, not the other six hundred commits. Adding is
verifiable on the spot; removing requires knowing what else depends on the thing — exactly the
knowledge a fresh context does not have. The safe move is always accretion, and it is taken every
time, by everyone, correctly.

**What "simpler" means here.** Not fewer lines, not fewer files, and emphatically not more
abstraction. The operational definition (Ousterhout): complexity is whatever makes a system hard
to understand and to change, and it is *incremental* — no single commit causes it, which is
precisely why no single-commit review can catch it. Its symptoms are change amplification (a small
change touches many places), cognitive load (how much you must hold in your head to change one
thing safely), and unknown unknowns (you cannot tell which places a change must touch). The Cost
field measures the first, the dimensions hunt the second, the coverage statement is an honest
admission about the third.

**Audit accidental complexity only.** Brooks' distinction holds: some difficulty is the problem
domain and cannot be designed away. A state machine with eleven states may be irreducible. An
audit that reports essential complexity as debt burns the reader's attention and teaches them to
skip the next report.

**The honest claim.** This audit does not make a system good and pays nothing down. It makes debt
visible, priced and attributable, so that *not* paying it becomes a decision someone made rather
than the default that happens while nobody is looking. Smaller than "architectural review" usually
implies — and the only claim a ledger can actually keep.

Fuller grounding, including where these ideas fail and when not to run this at all:
`philosophy.md` in this directory.

## When to use

- Before a major release, milestone, or version bump.
- On a codebase built fast — by agents, by a small team under deadline, by many parallel sessions.
- Complexity is visibly growing and nobody's job is reducing it (Lehman's 2nd and 7th laws).
- Asked for a "systemic", "architectural", or "tech debt" review, or about DRY/SOLID/coupling.
- On research or analysis code: before another person inherits the pipeline, before it is published
  alongside a paper, or when each new experiment costs more to add than the last one did.
- Recurring: quarterly, or every N releases, to measure whether debt is shrinking.

**Not for:** reviewing a diff or PR (use a code-review tool), hunting a specific bug (use
systematic debugging), or style/lint issues (see *Gates, not lists* below).

## The failure this prevents

Measured on a 39k-line repo: three independent, competent audits of the same code from the same
prompt produced ~55 distinct findings between them and **agreed on about ten**. Each run spawned
its own parallel sub-agents; each verified its own top claims; each was individually good.

- Any one run surfaced roughly **half** of what the three found together.
- The **most dangerous** finding in the whole set — a migration path that could permanently
  corrupt user databases on upgrade — appeared in **one run out of three**.
- Runs stated **contradictory facts with equal confidence** (import cycles: "zero" / "one cycle of
  seven modules" / "42 cycles"). One asserted a module was a live entry point; it was unwired.
- No run left anything a later run could compare against, so debt could not be tracked.

Depth was never the problem. **Coverage, verification, and accumulation** are. Everything below
exists to fix those three.

## Output contract

The audit produces **one ledger file** (default `docs/architecture-debt.md`; ask before creating
it) plus a short summary in chat. The ledger is the deliverable — a report nobody can diff is a
report that lets the same debt be rediscovered forever.

Every entry has exactly these fields, in this order:

```markdown
### SD-014 — task status is written by three modules with no transition table
status: open | accepted | fixed | worse     severity: high | med | low
first-seen: 2026-08-08     last-checked: 2026-08-08     confidence: confirmed | suspected

Cost:      adding or renaming a status requires edits in 6 places; commits dedcf4c and eec2dc6
           were each a fix for one site that was missed. Next state addition repeats this.
Evidence:  core/runs.py:166 (mirrors on run transition), core/tasks.py:103, core/tasks.py:123,
           core/review.py:695 (raw UPDATE, bypasses the log)
Verified:  read all four sites; no transition_task function exists (grep, whole repo)
Remedy:    _set_task_status by analogy with _set_run_status; route the four writers through it.
           ~1 session. Removes the class, not the instances.
Leave it:  each new state costs ~1 missed-site bug. Acceptable if states are now stable.
```

Field rules:

- **ID** — `SD-nnn`, assigned once, never reused, never renumbered. This is what makes runs
  comparable.
- **Cost** — the next change that becomes expensive or dangerous *because of this structure*.
  Prefer an incident that already happened (git log and code comments are full of them). If you
  cannot name a cost, you do not have a finding.
- **Evidence** — at least two `file:line` sites, or one measurement plus the command that produced
  it. A single site is a bug report, not structural debt.
- **Confidence** — `confirmed` means *you personally re-read the source and it says what the claim
  says*. Everything else is `suspected`. Never launder a sub-agent's claim into `confirmed`.
- **Verified** — never blank, on any entry. On a `confirmed` entry it says what you re-read or
  re-ran. On a `suspected` entry it says what remains unchecked and what would settle it, so the
  next audit can close it in minutes instead of rediscovering it.
- **Leave it** — the cost of doing nothing. Some entries should end up `accepted`; a ledger where
  everything is `open` has not triaged anything.

**Two tiers, one ID space.** Write full entries for everything you recommend and everything marked
`high`. When an audit turns up more findings than that, the rest go in a compact table rather than
being dropped or abbreviated ad hoc — same `SD-nnn` IDs, so any row can be promoted to a full entry
later without renumbering:

```markdown
| ID | Title | Sev | Confidence | Evidence anchor | Cost in one line |
|---|---|---|---|---|---|
| SD-021 | pickle is the persistence format with no version marker | high | suspected | `exp_build.py:690`, `:851` | a user re-runs after a fix and silently gets the pre-fix cached object |
```

**Negative results are results — record them separately.** A census signal you chased and cleared,
or a dimension that came back clean, is what makes the *next* audit cheaper. It is not debt, so it
gets no `SD-` id and never mixes with `accepted`:

```markdown
## Not debt — investigated and cleared
- **ND-001** — census §7 flagged `takens_embedding` in three files. Read all three: one
  implementation, one caching adapter, one 2-line method. False positive for duplication; the real
  findings on that path are SD-003 and SD-005. Do not re-chase.
- **Dimension 11 (client layer)** — checked, nothing above threshold: the library ships no UI.
```

`accepted` means *real debt we are deliberately living with*. Cleared signals are a different
thing and belong above, or the two get confused on the next run.

## Process

Work through all six phases. Skipping phase 3 or 6 is what produced the baseline failure.

### 1. Orient

**Establish which code you are auditing, before anything else.** A checkout is not automatically
the code that ships. Compare the working tree against the branch that releases: `git status`, the
version field in the manifest, and `git rev-list --count HEAD..origin/main`. State the answer in
the report, and stamp every finding with whether it survives on the release ref. In testing, an
audit ran against a feature branch 73 commits and two minor versions behind the release branch;
one of its top findings had already been fixed upstream and nobody noticed until a late probe
checked. If the gap is more than a handful of commits, audit the release ref directly rather than
the checkout — `git show <ref>:<path>` and `git grep <pat> <ref> -- <path>` need no checkout and
mutate nothing. (On Windows, prefix those with `MSYS_NO_PATHCONV=1` or the shell mangles the
colon.)

**The same question applies to documents and to evidence, and it is easy to forget there.**
A paper, a spec or a design note can have several editions in flight — a draft in the tree, a
newer one in a worktree or a branch. Find the edition that will actually ship before you audit
one. And when a document cites a measurement, check the *vintage* of the artifact it cites
before comparing the two: an artifact from an older version is not evidence that the text is
wrong, it is evidence that the claim is unbacked. Those are different findings with different
remedies — recompute the number, versus commit the run — and reporting the first when the truth
is the second is the most damaging mistake an audit can make, because it is both alarming and
false.

Read the ledger if one exists — its open entries are your starting frontier, and you must report
their current status (`fixed`, `worse`, still `open`) before adding anything new. Read the
project's own contracts: CLAUDE.md/AGENTS.md, ARCHITECTURE, CONVENTIONS, schema files, ADRs. These
are claims the code may no longer honour, and that gap is one of the cheapest, highest-value
finding classes there is.

### 2. Census — measure before you read

Run `census.sh` (in this skill's directory) from the repo root:

```sh
sh census.sh                              # auto-detects languages, last 6 months
sh census.sh --since "1 year ago" --src src
```

It needs a POSIX shell — on Windows that is Git Bash, which comes with Git. If it will not run at
all, do not skip this phase: every section is an independent shell command, so reproduce the
signals by hand.

Ten mechanical sections: scale, size outliers, churn×size hotspots, growth-vs-pruning per month,
cross-boundary co-change, internal import direction, duplicated symbol names, cloned blocks,
dead-code candidates, configuration surface. Seconds to run on a 40k-line repo, no language
assumptions, degrades outside git.

Read it for what attention alone cannot give you:

- **del/add per month** is Lehman's 2nd law as a number: how much is removed per unit added. Its
  *level* is meaningless on its own — it swings by ~1.6× depending on whether tests and docs are
  in scope, and it varies by project age and phase. There is no pass mark, and inventing one
  produces a verdict the data does not support. What carries signal is the **direction across
  audits at an identical scope**: copy the census `SCOPE LINE` verbatim into the ledger trend row,
  and compare only rows sharing it. A ratio near zero sustained over several windows means
  removal is nobody's job — that is a finding about the *process*, worth stating plainly, not a
  score.
- **Read the monthly shape, not just the window total.** Deliberate simplification is punctuated,
  not steady: ordinary months sit low and occasional campaign months spike, because someone sat
  down and removed a subsystem. A flat low line across every month means no one has ever done
  that. Measured on two projects, the curated one's *median* month barely beat the uncurated one's
  — the spikes were the whole difference. A level alone will mislead you; the shape will not.
- **churn × size** is where debt actually costs money. A 3000-line file nobody touches is not
  urgent; a 900-line file touched weekly is. **Check the commit dates before trusting the
  rank.** Churn counts commits, so a file produced in a burst — one commit per generated
  unit — ranks as a hotspot without being unstable. Measured: the top-ranked file in one
  audit had 200 commits, 194 of them on two consecutive days and six across the three
  months since. Sustained churn means the design is unsettled; burst churn means someone
  ran a generator. Only the first is debt.
- **cross-boundary co-change** finds leaky seams a clean import graph hides. If `core/x.py` and
  `web/app.py` change together in 66% of commits, the boundary between them is decorative.

The census produces *candidates and evidence*, never findings. Nothing enters the ledger without
phase 3.

### 3. Probe every dimension — this is the coverage fix

Ad-hoc exploration is what produced ~50% coverage across baseline runs. Walk **all** of the
dimensions in `dimensions.md`, in order. Each one ends in either findings or an explicit
`checked — nothing above threshold`. A dimension you skipped is a dimension you must name in
phase 6.

The dimensions are independent: if sub-agents are available, dispatch one per dimension in
parallel, each returning entries in the contract format above. They report `suspected`; only you
promote to `confirmed`, in phase 4.

### 4. Verify at the source

For every candidate, open the files and confirm the claim yourself. This is not optional
diligence — in the baseline, an audit confidently classified an unwired module as a live entry
point, and the reader had no way to tell that item from the true ones around it.

- Re-read each cited site. Does it say what the claim says?
- Try to refute the claim before accepting it. What would make it false? Check that.
- Where the claim is a count ("defined 9 times", "42 cycles"), re-run the command and paste it.
  Baseline runs reported three different cycle counts for one codebase because each measured a
  different thing and none said which.
- Anything you did not personally re-read stays `suspected` and is marked as such in the ledger.

### 5. Gate the remedies

Every proposed remedy passes all four gates, or it is rewritten until it does:

1. **Delete before you abstract.** Is the right fix removing the code, the feature, or the
   option? On a codebase with a low deletion ratio this is usually the highest-value move and
   almost never the first one proposed. Unwired features, dead models, shims with no callers, and
   config knobs nobody sets are all deletions, not refactors.
2. **Does the remedy add indirection?** An interface with one implementation and no test double
   is an alias, not an abstraction. A 200-line function split into eight functions each called
   once spreads one linear story across a file. If the after-state is harder to read than the
   before-state, the remedy is the disease.
3. **Would deduplication couple things that change apart?** Two identical blocks are only
   duplication if a change to one *must* change the other. Ask: when requirement X changes, do
   both sites change? If no, they are coincidentally similar — leave them. Rule of three.
4. **Is this a gate, not a list?** See below.

### 6. Cut, and state your coverage

- Rank open entries by (cost × confidence) ÷ effort. Recommend **at most five** for action now.
  Everything else stays in the ledger with a status — visible, triaged, not silently dropped.
- Report the diff against the previous run: entries fixed, new, worsened, and the del/add trend.
  On a first run, say so — this run establishes the baseline.
- End with **what you did not examine**: dimensions skipped, areas not read, claims left
  `suspected`. An audit that does not bound its own coverage reads as complete when it is half.

## Gates, not lists

If a linter, type checker, formatter, or test can detect the problem, the finding is **"this gate
is missing or mis-scoped"** — one entry — not an enumeration of instances.

Baseline runs padded reports with 145 unformatted files, a CI job that doesn't run tests, and a
type checker pointed at the cleanest 60% of the codebase. Those are three ledger entries about
gates. The instances are the gate's job, forever, for free.

Corollary: prefer remedies that make a class of debt *impossible* over remedies that clean up
today's instances. A transition table beats fixing six call sites; a schema check beats an audit.

## Quick reference

| Signal | Where it comes from | What it usually means |
|---|---|---|
| del/add < 0.15 sustained | census §4 | nothing is ever deleted; complexity is monotonic |
| two files co-change > 50% across a boundary | census §5 | the boundary is decorative |
| high churn × high size | census §3 | every feature touches it; every feature conflicts |
| same name defined 3+ times | census §7 | drift risk; copies will diverge under edit |
| doc/contract says X, code does Y | phase 1 | cheapest high-value class; often a release blocker |
| private name imported across modules | dimensions.md | the module boundary is fictional |
| feature documented but never called | census §9 + phase 1 | delete it or wire it; do not leave it |
| N near-copies of one surface | census §8 | next fix lands in one copy of N |

## Common mistakes

| Mistake | Do instead |
|---|---|
| Ranking by size ("this file is 3000 lines") | Rank by cost of the next change. Big and stable is fine. |
| Reporting a principle violation | Name the change that gets expensive, and who already got bitten. |
| Trusting a sub-agent's claim | Re-read the source. Mark `suspected` if you did not. |
| Inventing effort estimates ("2–3 days") | Size in sessions, only after naming the edit sites. |
| One ledger entry per instance | One entry per class, with instances as evidence. |
| Listing everything found | Ledger holds all; recommend ≤5. Triage is the deliverable. |
| Fixing things while auditing | Diagnose only. Mid-audit edits lose the system view and break what wasn't measured. |
| Silent partial coverage | Name every dimension you skipped. |

## Red flags — stop and re-check

- You are proposing a new interface, factory, or base class, and there is exactly one implementation.
- A finding's Cost field restates the Claim in other words.
- You marked something `confirmed` from a sub-agent's report you did not re-read.
- The recommendation list is longer than five items.
- Nothing in the ledger is `accepted` — you ranked, but you did not triage.
- You have not run the census, and you are about to explain what the real problem is.
- You started editing code.
