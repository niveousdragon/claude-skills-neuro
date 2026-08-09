# Audit dimensions

Twelve dimensions. Walk **all** of them. Each ends in findings or an explicit
`checked — nothing above threshold`. Anything skipped is named in the coverage statement.

This list is fixed on purpose. Ad-hoc exploration is what makes two audits of one codebase
disagree; a fixed partition is what makes run N+1 comparable to run N. Every dimension below
earned its place: in baseline testing, each was the *only* source of at least one finding, and
several produced the highest-severity item in the whole audit while other runs missed it entirely.

The probe commands are illustrative, not prescriptive — adapt them to the language and layout.
Thresholds are starting points; raise them on a large codebase, lower them on a small one.

---

## 1. Contract drift — documents that describe a system you don't have

The cheapest high-value class. Every project states contracts somewhere: CLAUDE.md/AGENTS.md,
ARCHITECTURE, CONVENTIONS, ADRs, schema comments, README quickstart, docstrings on public entry
points. Code drifts; documents don't follow. New contributors — human or agent — then build on a
promise the system doesn't keep.

**Probes**
- List every structural claim the docs make ("X is the single source of truth", "all Y live in
  directory Z", "the DB is a rebuildable index over files", "no global state"). Check each one.
- Documented commands, flags, and directories: do they exist? `ls`, `grep` for the entry point.
- Documented invariants: find the code that enforces them. If nothing enforces it, it is a wish.
- Frozen or versioned contracts (schema, wire formats, plugin APIs): does the code still honour
  the frozen version, or has it quietly diverged?

**Report threshold:** any claim that is false today. State the document, the line, and the reality.
A false contract in a *frozen* document is release-blocking regardless of how small it looks.

---

## 2. State and lifecycle ownership

Long-lived systems accumulate state machines that were never written down. The question is not
"is there a state machine" but "how many places can move an entity between states, and do they
agree".

**Probes**
- For each core entity, find every write to its status/state column or field.
  `grep -n "SET status\|\.status *=\|state *=" ` and count distinct writers.
- Is there one transition table / guard function, and does every writer go through it? Writers
  that bypass it are the finding — especially raw updates that also skip event logging.
- State values as bare literals vs a shared enum: count occurrences of each literal across the
  whole tree, including templates, client scripts, and stylesheets. Wide scatter means a renamed
  state breaks silently in places no type checker sees.
- Sets like "open states" / "terminal states" written out more than once — compare them. Drift
  between two such lists is a bug that has probably already happened; check git log for the fix.
- Who can *end* a lifecycle (finalize, close, cancel, kill)? More than one owner means racing
  finalizers with different error text.

**Report threshold:** more than one writer without a shared guard; or the same state set spelled
out in two places.

---

## 3. Boundaries and layering

**Say which cycle measure you used.** Baseline audits reported "zero cycles", "one cycle of seven
modules", and "42 cycles" for the same codebase — all defensible, all measuring different things.
State it: top-level imports only, or including function-local; SCCs, or elementary cycles;
which packages were in scope.

**Probes**
- Import direction between areas (census §6). Which arrows should not exist? A lower layer
  importing an upper one, or a port/adapter layer importing the core it's supposed to invert.
- Function-local / deferred imports: count them, then classify. Which genuinely break a cycle, and
  which are cargo-cult? A deferred import of a leaf utility module cannot be breaking anything.
  Cycles hidden inside functions are still cycles; they just fail at call time instead of import
  time.
- Cross-module reaches for private names (`_foo` imported from another module, `friend` access,
  reflection into internals). Each one means the module boundary is fictional and the private name
  is a de facto public API with no contract.
- Redundant re-imports: a name imported at module top *and* again inside a function.

**Report threshold:** any arrow that contradicts the documented layering; any private name crossing
a module boundary; deferred imports where the majority are not cycle-breaking.

---

## 4. Duplication and drift across parallel surfaces

Systems grow surfaces: desktop and mobile, CLI and API, v1 and v2, web and worker. Each new
surface is usually built by copying the last one. The debt is not the duplication — it is that the
copies **have already diverged**, and nobody knows which divergences are features.

**Probes**
- Census §7 and §8 give exact and near-exact clones. Extend by hand: for each shared behaviour
  (auth, upload, path safety, error handling, an action like approve/reject), find every
  implementation.
- For each cloned behaviour, **diff the copies and list the differences**. This is the actual
  deliverable of this dimension. Differences are either bugs or undocumented features; both need a
  decision.
- Direction of dependency between surfaces: does the newer surface import the older one's
  internals? That makes the older surface's privates load-bearing.
- Client-side: a shared script/stylesheet included *and* partially reimplemented inline in one
  surface's template.

**Report threshold:** any behaviour implemented 3+ times, or 2+ times with an observable
difference. Report the differences, not just the count.

---

## 5. Data access and schema contracts

**Probes**
- Where does query text live? Count query sites per module. A presentation module holding a large
  share of the system's queries means there is no data layer, whatever the docs say.
- Composite keys: for each multi-column primary key, check that *every* query filters on all
  columns. Half-key lookups silently cross tenants/projects/namespaces.
- Foreign keys without indexes; hot filter columns without indexes. Cross-reference against the
  actual query sites, not against intuition.
- Typed models (ORM classes, dataclasses, pydantic, structs): are they instantiated on the read
  path, or does data move as raw tuples/dicts while the models only document intent? Grep for
  instantiations outside the model module and outside tests.
- Unbounded reads on hot paths: full table scans, `SELECT *` with no limit, N+1 loops, the same
  table scanned several times in one function.
- Tables that grow without bound and have no retention path.

**Report threshold:** any half-key query; any unindexed hot filter; models with zero production
instantiation while documented as the contract.

---

## 6. Process, resource and concurrency ownership

Frequently the source of the highest-severity findings, and the least likely to be found by
reading code alone — the failures are platform-specific.

**Probes**
- Every place a subprocess is spawned: compare the spawn options side by side (process group /
  session, environment, stream handling, timeouts, output limits). Divergence here means one path
  has protections the other silently lacks.
- Every place a process is killed: is it the same function everywhere? A bare signal to a single
  pid where a tree kill is needed leaves orphans holding resources.
- Platform branches: if the code targets more than one OS, which paths are only exercised on the
  developer's OS? Cross-check against what CI actually runs.
- Locks and transactions on read/poll paths: does rendering a page take a write lock? Check what
  a periodic poll actually executes.
- Identifier reuse (pids, handles, tokens) stored and acted on later without revalidation.
- Fire-and-forget background work: who observes failure?

**Report threshold:** any divergence between two spawn or kill sites; any write lock on a path
that runs on a timer.

---

## 7. Dead, unwired and vestigial

Agent-written and fast-moving codebases accumulate this fastest, because adding is always cheaper
than removing and no session is ever assigned the removal.

**Probes**
- Census §9 gives candidates. Verify each: decorator registration, dynamic dispatch, entry points,
  template-side references, and subprocess invocation by name all hide real usage. Do not report a
  candidate you have not chased.
- The subtler and more valuable case: code that *is* reachable but whose output nobody consumes.
  An optional parameter no caller ever passes; a computed field never read; a table written and
  never queried; a snapshot taken on every run for a feature that was never wired up. Grep for
  each producer's consumers, not just for the producer's callers.
- Shims and compatibility layers: find the callers they were written for. Gone? So is the shim.
- Config options no code path branches on; feature flags permanently on or off.

**Report threshold:** anything with no consumer. Note explicitly whether the *cost* is still being
paid (work done every run for an unreachable payoff) — that upgrades the severity.

---

## 8. Configuration and flag surface

Every knob is a branch that must keep working, and a combination someone will eventually hit.

**Probes**
- Census §10 counts env vars and flags. Are they read through one accessor, or directly scattered?
  Direct reads bypass defaults, validation, and precedence.
- Settings written at runtime: read-modify-write of a whole config file is a lost-update race as
  soon as two surfaces can save. Check for locking.
- Configuration carried through global mutable state (process env, module globals, singletons) —
  especially where the project claims not to have global state.
- Defaults duplicated as literals across the tree instead of one constant.

**Report threshold:** any setting with more than one writer and no lock; any value read both
through an accessor and directly.

---

## 9. Migration, upgrade and persistence safety

**The path existing users take on release day.** In baseline testing this dimension produced the
single most dangerous finding of the entire audit, and two of three runs never looked at it. Never
skip it before a release.

**Probes**
- Are migrations transactional? A failure mid-sequence that leaves partial changes committed and
  the version marker unadvanced re-runs the same steps next start and fails permanently.
- Are they idempotent / re-runnable? `IF NOT EXISTS`, column checks. Any hand-rolled guard already
  present is evidence this failure mode has occurred.
- Destructive steps (drop, rename, rebuild with constraints off) — what happens if they're
  interrupted?
- Two sources of truth for the schema: a full create script for fresh installs, plus an
  incremental path for upgrades. Is there a test that builds both and compares them? Without one
  they diverge silently and users get different schemas depending on when they installed.
- Rebuild/repair commands: do they actually restore what they claim? Enumerate what is only in the
  mutable store and has no other representation — that is the true blast radius of data loss.
- Rollback: can a user downgrade after upgrading?

**Report threshold:** any non-transactional or non-idempotent migration; any divergence between
fresh-install and upgrade schemas; any rebuild command whose coverage is narrower than documented.

---

## 10. Enforcement gates

What the project claims to enforce vs. what runs automatically.

**Probes**
- CI configuration: what actually runs, on what trigger, on which platforms? Compare to the
  project's stated definition of done.
- Type checking / linting scope: which directories are covered? Cross-reference with the churn ×
  size hotspots from census §3. Gates pointed at the calm part of the codebase are backwards.
- Config that promises strictness (`strict = true`) narrowed by the command actually invoked.
- Formatter declared but never applied.
- Tests that exist but never run in CI: green depends on someone remembering.

**Report threshold:** any gap between declared and enforced; any hotspot outside the strictest
gate. One entry per gate, never one per instance.

---

## 11. Client / presentation layer (skip if none)

**Probes**
- Update architecture first, monolith second. Count polling endpoints and intervals; compute
  requests per minute at rest. Frequent full re-renders destroy client state (scroll, focus,
  drafts, expansion), and the patches for that pile up in layers — suppression logic, hand-rolled
  diffing, preserve attributes, post-swap handlers. When you find those layers, the finding is the
  update model, not the patches.
- One monolithic script/stylesheet: check whether it is genuinely coupled or merely
  unsplit. Count globals it must expose because markup calls them by name.
- Ownership of cross-cutting client concerns (scroll, focus, theme, i18n): count independent
  policies and the magic numbers each one chose. Many thresholds for one concept means each was
  tuned in isolation against one complaint.
- Localisation: count the mechanisms. More than one means half the UI cannot be translated and
  every label change requires knowing which mechanism owns that string.
- Inline styles/scripts in templates that also load the shared asset.

**Report threshold:** two or more mechanisms for one cross-cutting concern; a patch stack over an
update model.

---

## 12. Test-suite structure

Tests are code and accrue the same debt — but here the debt is measured in *false confidence* and
*resistance to change*.

**Probes**
- Tests that assert on source text (grep the stylesheet, match a string in a script) rather than
  behaviour. They pass while the behaviour is broken and they block harmless refactors.
- One-file-per-bug sprawl: many tiny files named after incidents. Individually reasonable, but the
  suite stops being navigable and coverage becomes unknowable by inspection.
- Version-named grab bags (`test_v3_features`) that will rot.
- Coverage of the areas the census flags as hotspots — is the churniest code the least tested?
- Acceptance/integration tests that stopped at an old milestone while features kept shipping.
- Broad exception swallowing in production code that makes failures untestable and invisible.

**Report threshold:** any test asserting text instead of behaviour; hotspots with no behavioural
coverage.
