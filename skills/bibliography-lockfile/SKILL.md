---
name: bibliography-lockfile
description: Use when a project cites papers in BibTeX and entries are added or edited by hand, when setting up bibliography management for a paper, or after a reviewer or venue citation checker flags hallucinated, fabricated, or incorrect author lists in references.
---

# Bibliography Lockfile

## Overview

Treat the bibliography like a lockfile: humans and agents edit only a **registry of
identifiers** (`sources.yaml`); every `.bib` is **generated** from publisher metadata
(Crossref / arXiv / PMLR / OpenAlex). An author name never passes through anyone's
hands or memory — so fabricated co-authors and wrongly expanded initials become
impossible by construction, not caught after the fact.

Origin: a real conference submission where hand-typed entries produced fabricated
co-author names — plausible-sounding people who do not exist — and an official flag
from the venue's automated reference checker, with a default-reject presumption.

## When to Use

- Setting up or inheriting any paper project with a `.bib`
- Asked to "add a reference" / "fix the bibliography"
- A checker, reviewer, or audit found wrong authors in a citation
- **Not needed:** a throwaway note citing 2-3 DOIs — `curl -LH "Accept: application/x-bibtex" https://doi.org/<DOI>` is enough

## Deployment (once per project)

1. Copy `bibgen.py` and `hook_guard.py` from this skill into `tools/bibgen/`.
2. Create `tools/bibgen/sources.yaml` from `sources.example.yaml`. REQUIRED: one
   entry for **every citation key the project uses**, not only the keys you are
   adding — the generated file replaces the whole `.bib`, and any key missing from
   sources.yaml is silently lost at step 4.
3. Run `python bibgen.py --compare <path to the project .bib>` (run from
   `tools/bibgen/`, or pass an absolute path — the compare argument is resolved
   from your cwd). This is the meaningful check: it diffs generated authors against
   the current hand-written state. Read every DIFF line; an ONLY-IN-REFERENCE line
   means a key is missing from sources.yaml — go back to step 2. ONLY-IN-GENERATED
   lines for the keys you are adding are expected on this first pass.
4. Only after the compare is clean, copy `refs.generated.bib` over the project's
   `.bib`.
5. REQUIRED once per project, deadline or not: add the PreToolUse hook and the
   project-rule block from `templates.md` (`.claude/settings.json`, `CLAUDE.md`) —
   two minutes now is what protects the next deadline.
6. Gate before every submission: re-run the same `--compare` — 0 FAILED,
   0 mismatches; it also catches any hand edit made after step 4.

**If bibgen is not deployed in the current project — deploy it here (step 1). Never
wander into a different project or reuse another project's install to comply.**

## Source Types (sources.yaml)

| Key | Source | Use for |
|---|---|---|
| `doi:` | Crossref (publisher-deposited) | anything with a DOI — first choice |
| `arxiv:` | arXiv API | preprints |
| `pmlr:` | proceedings.mlr.press page | ICML/AISTATS papers without DOI |
| `openalex_title:` | OpenAlex, exact-title match required | NeurIPS/ICLR/JMLR without DOI |
| `manual: true` | hand entry | ONLY with `verified:` stamp (date + how checked) |

Prefer `doi:` whenever a DOI exists — it carries the most complete fields. If a
work surely has a DOI you don't know, look it up (e.g.
`api.crossref.org/works?query.bibliographic=<title>`) instead of settling for
`openalex_title:`, which is the fallback for venues that genuinely lack DOIs.
`openalex_title:` entries come back leaner (often no volume/pages/doi) and may carry
the aggregator's title quirks: add missing venue fields via `override:`, or find the
DOI instead. Venue fields the source lacks (booktitle, pages) go in a visible
`override:` block. A hand-written author field is allowed only as `authors_override`
+ `verified:` stamp — the generator refuses otherwise.

## The Iron Rule

**Author names are never typed, recalled, or expanded from initials.** They come from
a publisher record or they do not go in.

| Excuse | Reality |
|---|---|
| "Deadline — I'll just type it, verify later" | "Verify later" is the exact rationalization that shipped fabricated authors in a real submission. Fetching the DOI takes 10 seconds. |
| "I remember this paper's authors" | Memory keeps the first and last authors and invents the middle ones; initials get expanded into wrong full names. |
| "The record only has initials, I'll expand them" | Wrong-expansion is the #1 failure class. Keep initials or add `authors_override` with a `verified:` stamp. |
| "An aggregator/LLM gave me the entry" | Unverified generated entries are the incident, not the fix. Only `doi:`/`arxiv:`/`pmlr:` sources or exact-title OpenAlex. |

## Red Flags — STOP

- You are typing `author = {` by hand into any `.bib`
- You are expanding "J. S." into a full name without a byline in front of you
- You found no DOI and are about to guess fields instead of using `manual:`+`verified:`

## Files

`bibgen.py` (generator + `--compare` gate), `hook_guard.py` (PreToolUse block on .bib
edits), `sources.example.yaml`, `templates.md` (hook config + project-rule text).
