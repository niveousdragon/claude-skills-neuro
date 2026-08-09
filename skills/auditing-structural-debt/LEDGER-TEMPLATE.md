# Architecture debt ledger

Maintained by the `auditing-structural-debt` audit. Human-owned: change any `status` yourself and
the next audit will respect it. IDs are permanent — never renumber, never reuse.

**Trend** — one line per audit, oldest first. Copy the census `SCOPE LINE` verbatim; rows with
different scopes are not comparable and must not be read as a trend. Direction is the signal,
not the level — there is no pass mark.

| date | scope line | del/add (window) | open | accepted | fixed since last | new | worse |
|---|---|---|---|---|---|---|---|
| 2026-08-08 | all tracked source \| ext=py,js \| since=1 year ago | 0.091 | 12 | 0 | — | 12 | — |

`status` values: `open` (agreed debt, not yet paid) · `accepted` (deliberately living with it —
record why) · `fixed` (verified gone; keep the entry, it is the history) · `worse` (measurably
grown since first seen).

---

### SD-001 — <what the structure is, not which principle it violates>
status: open     severity: high     first-seen: YYYY-MM-DD     last-checked: YYYY-MM-DD
confidence: confirmed

Cost:      <the next change that becomes expensive or dangerous because of this. Name an incident
           that already happened if one exists — git log and code comments usually hold one.>
Evidence:  <file:line, file:line — at least two sites, or a measurement plus its command>
Verified:  <never blank. If confirmed: what you re-read or re-ran. If suspected: what is still
           unchecked and the exact command or file that would settle it.>
Remedy:    <smallest change that removes the cost, not the instances. Size in sessions.>
Leave it:  <what doing nothing costs. If this is cheap, the entry probably belongs in `accepted`.>

---

<!-- Copy the block above per entry. Keep fixed and accepted entries in place: the ledger's value
     is that it accumulates. A finding rediscovered from scratch every quarter is not tracked. -->

---

## Compact entries

Findings that are real but did not make the recommended cut. Same ID space as above — promote a row
to a full entry when it becomes actionable. Never abbreviate a `high` or a recommended item.

| ID | Title | Sev | Confidence | Evidence anchor | Cost in one line |
|---|---|---|---|---|---|
| SD-021 | <what the structure is> | med | suspected | `file.py:120`, `other.py:44` | <what the next change costs> |

---

## Not debt — investigated and cleared

Negative results. These make the next audit cheaper, so they are worth as much as findings. No
`SD-` ids: these are not debt, and they must not be confused with `accepted`, which means real debt
somebody chose to live with.

- **ND-001** — <signal chased, what you found, why it is not debt, "do not re-chase">
- **Dimension N (name)** — checked, nothing above threshold: <one line why>
