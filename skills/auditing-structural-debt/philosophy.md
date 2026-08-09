# Why audit structural debt — the grounding, and its limits

Read this once before deciding to adopt the practice, or when someone asks why the ceremony is
worth it. `SKILL.md` carries the parts that change what you do mid-audit; this file carries the
reasoning, including the arguments against.

---

## 1. What Lehman actually claimed

Manny Lehman derived eight "laws of software evolution" (1974–1996) from long observation of
OS/360 and other long-lived systems. They apply only to **E-type** systems — software embedded in
the real world, which changes that world by existing. They do not apply to **S-type** software,
fully specified by a formal statement (a sorting routine, a parser for a fixed grammar). Knowing
which you have matters: an audit that scolds an S-type component for not evolving is confused.

Four of the eight bear directly on this practice:

- **Law 2 — increasing complexity.** As a system evolves, its complexity increases *unless work is
  done to maintain or reduce it*.
- **Law 7 — declining quality.** Quality declines *unless the system is rigorously maintained and
  adapted* to a changing environment.
- **Law 6 — continuing growth.** Functional content must keep increasing or users become
  dissatisfied. So you cannot answer laws 2 and 7 by freezing the system; growth is not optional.
- **Law 8 — feedback system.** Evolution is a multi-level, multi-loop feedback process. Attempts to
  drive it as a straight pipeline fail. A practice with no feedback loop does not steer anything.

Two more constrain how you *respond*:

- **Law 4 — conservation of organisational stability.** The average effective work rate on a system
  is roughly invariant over its life, largely independent of how many people are assigned. Derived
  by measurement, not argument, and independently of Brooks. Practical reading: you cannot buy your
  way out of accumulated complexity by adding capacity — including by pointing more agents at it.
- **Law 5 — conservation of familiarity.** Growth per release is bounded by how much the team and
  the users can absorb. Practical reading: this is why the audit recommends **at most five** items.
  A remediation programme larger than the absorbable rate is not ambitious, it is fictional.

**Honest status of the laws.** They are descriptive generalisations from a specific era and mostly
from corporate, closed-source development. Open-source studies support them only partly — growth in
Linux has been observed as super-linear, against law 5. Treat them as a well-supported account of
*why* the pressure exists, not as physics. The parts this practice leans on — laws 2 and 7 — are
also the least controversial, because both are tautological in a useful way: they name a force and
a counter-force, and say which wins when nobody applies the counter-force.

---

## 2. The asymmetry that actually causes the decay

The laws describe the pressure. The mechanism is more mundane, and it is organisational rather
than technical.

Adding has an owner, a trigger and evidence. Someone requests a feature; a spec bounds it; a
passing test proves it exists. Removing has none of those. Nobody files a ticket for "this is
harder to change than it should be". Nothing proves a deletion succeeded except an absence.

Then there is risk. Deleting something can break a system in a way traceable to you. Leaving dead
code breaks nothing attributable to anyone. Both humans and agents face that gradient, and both
respond to it identically and rationally. This is why the deletion ratio sits where it does in
almost every fast-moving codebase, and why it is the honest measure of whether the counter-force
exists at all.

For agent-written systems, add one more: a session has no memory of the other six hundred commits.
It can verify that its addition works. It cannot verify that a removal is safe, because the
knowledge of what depends on the thing is exactly what a fresh context lacks. So an agent
codebase accretes not from carelessness but from epistemics — and the fix has to be structural,
not exhortation.

---

## 3. Why an artifact, and why the same artifact every time

Law 8 says evolution is a feedback system. A review that ends in prose ends the loop: nothing
carries to the next cycle, so the next review re-derives the same list from scratch, and nobody
can say whether anything improved. Measured directly: three independent audits of one codebase
agreed on roughly a fifth of their findings, and the most dangerous item appeared in one of three.
Not because any of them was bad — because there was nothing to converge on.

A ledger with permanent IDs closes the loop three ways. It lets a finding be **accepted** — the
single most underrated status, because triage is the deliverable and an audit where everything
stays open has ranked without deciding. It lets a finding be marked **worse**, which is the only
direct evidence that deferral had a cost. And it makes the next audit *differential*: start from
the previous frontier instead of re-rolling the dice.

---

## 4. What simplicity is not

Most damage done in the name of simplification comes from four substitutions:

- **SOLID as ritual.** Interfaces with one implementation, dependency injection with one binding,
  factories producing one type. Each adds a level of indirection and removes nothing. An
  abstraction that never has a second implementation is a rename with extra steps.
- **DRY as textual deduplication.** Two blocks that look alike are duplication only if a change to
  one *must* change the other. Merging code that changes for different reasons couples two
  independent futures and is strictly worse than the repetition.
- **Length as the metric.** A 300-line function that reads top to bottom can be simpler than eight
  30-line functions each called once, which scatter one linear story across a file and force the
  reader to reassemble it.
- **Layers as virtue.** Every boundary you add is a boundary someone must cross, document, keep in
  sync and test through. Boundaries earn their place by isolating change, not by existing.

The test that survives all four: **would a competent stranger predict correctly where a change
goes, and be right?** If yes, it is simple enough, regardless of how it scores against any
principle.

---

## 5. The steelman: audits as theatre

The strongest argument against this practice is that it is expensive, produces a document, and
documents are how organisations simulate action. That failure mode is real and worth naming, so
you can check whether you are in it.

You are doing theatre if: the ledger grows every cycle and nothing changes status; the
recommendations are never scheduled; the report is longer than the work it triggers; findings are
principle violations rather than priced predictions; or the same items reappear with new numbers.

You are not, if: items move to `fixed` and stay there; some move to `accepted` with a stated
reason; the deletion ratio moves in the right direction at a constant scope; and the audit gets
*cheaper* each cycle because the previous ledger narrows the search.

If after two cycles nothing has moved, the practice is not working and should be stopped or
handed to someone with authority to schedule the work. An audit nobody acts on is worse than none:
it converts a real problem into a discharged obligation.

---

## 6. When not to run this

- **On a prototype or a system with an expected short life.** Debt is only debt if you keep paying
  interest. Code that will be deleted next month should be as tangled as it needs to be.
- **Mid-crisis.** During an incident or a hard deadline, the correct move is the narrow fix. Audit
  after.
- **Right after the previous one**, unless a large amount of code has landed since. The signal is
  in the delta.
- **As a substitute for a decision.** If you already know the architecture is wrong and you know
  what it should be, you need a plan, not a diagnosis.
- **On someone else's code you do not own.** A ranked list of another team's failings, unrequested,
  is not a contribution.

---

## 7. The one number

If everything else in this practice is dropped, keep the deletion ratio at a fixed scope, tracked
over time. It answers the only question that matters here: **is anyone doing the work that laws 2
and 7 say must be done?** Everything else in the skill exists to turn that number's answer into
specific, priced, verifiable things a person can choose to do or knowingly decline.
