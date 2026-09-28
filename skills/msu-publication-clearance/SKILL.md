---
name: msu-publication-clearance
description: Use when an MSU (Moscow State University, biology faculty) author needs the export-control clearance for a paper, conference abstract, proceedings, poster, dissertation or autoreferat — "экспертное заключение", "заключение о возможности открытого опубликования", "экспертиза статьи/тезисов", "бланк заключения", "оформи заключение на статью" — or is about to submit, preprint, or present work without one.
---

# MSU publication clearance (экспертное заключение)

## Overview

At MSU any open publication of work done on the job needs an approved
"заключение о возможности открытого опубликования" **before** it leaves the
building. The author fills in only the **yellow-highlighted** text of the
faculty blank; the commission fills in everything else. The bundled
[`fill_clearance.py`](fill_clearance.py) does exactly that and checks the one-page rule.

Sources: rector's orders № 4дсп (30.08.2015) and № 1563 (28.12.2022), the rectorate's
"Разъяснения" to them, the faculty memo "Памятка автору", and the biology faculty's
letter of 19.02.2026.

## 1. Timing — say it first if it is already late

Open publication = **any** of: submitting through a journal website or by e-mail
(even if rejected later), a preprint, a talk, poster or slides, entering the work
into ИАС «Истина», defending a dissertation. The clearance must be approved before
the first of these. Compare the venue's submission deadline and event date with today.
If the user already submitted, or the event is past: still prepare the blank, tell
them plainly it is late, and never suggest backdating — the commission writes the dates.

## 2. Get the current blank

Blanks change; use the one the user downloads now, not an old copy. Where:
biology faculty site → bottom left "Служебные документы и бланки" (password-protected;
the password is in the faculty's letter — never write it into any file). Pick by type:

| Material | Blank | Forms / printed copies |
|---|---|---|
| Journal article (incl. accepted, in press) | "Статья в журнале" | 1 page; 2 copies |
| Conference abstracts (тезисы), proceedings, collection chapter | "Статья в сборнике" | 1 page; 2 copies |
| Dissertation + autoreferat | "Диссертация и автореферат" | 2 pages; 3 copies |

No matching blank (monograph, talk without abstracts, media) → ask the faculty
expert commission, do not improvise a new wording.

## 3. Fill it

```bash
python fill_clearance.py BLANK.docx --list          # see the sample text of each place
python fill_clearance.py BLANK.docx OUT.docx --page "HEADER" "MATERIAL"   # thesis blank: two --page
```

Write HEADER and MATERIAL by copying the sample's grammar word for word:

- kind of material in genitive: "статьи", "тезисов" (then "направляемых", plural);
- **all** authors, "И.О. Фамилия" in Cyrillic and genitive, publication order
  ("Н.А. Поспелова, К.В. Анохина" for Поспелов, Анохин). Gender unclear, or the names
  given only in Latin letters → ask for the Russian spelling (as in Istina), do not guess;
- title exactly as it will be published, in its language, in guillemets with the title
  itself italic: `«*Hippocampal place cells remap*»`. User gave the title in a language
  other than the venue's → ask for the submitted one before printing;
- journal: `в журнале «Journal of Neuroscience», издаваемом Society for Neuroscience`.
  **No volume, issue, year or article number**, even though the rectorate's sample
  once showed one — the faculty confirmed they are not given;
- collection: `направляемых в сборник … конференции «…», проводимой <organiser, full name>`;
- MATERIAL = the kind + authors + title, without the venue.

The script must end with `[OK] … highlight removed` and `[OK] N page(s), one per form`;
with MS Word it also writes OUT.pdf next to OUT.docx for a visual check.
Anything else — stop and show the user; do not edit fonts, margins, or any text outside
the yellow places (not even "в компетенции биологического факультета" for an outside co-author).

## 4. Tell the user what to bring

Check each against the case and list only what applies:

- the blank printed in the copies from the table, on one page each; the material
  printed in the same number of copies;
- poster, slides or other talk material → their printouts too (the talk discloses more
  than the abstract);
- a co-author from another organisation, or a second affiliation of an MSU author →
  a letter from that organisation asking for (or not objecting to) the MSU review and
  not objecting to publication in this venue; otherwise that organisation's own clearance;
- prepared in a publisher's LaTeX/Word template, so the printout looks already published →
  an extra sheet signed by the authors: the template's URL and access date, and that the
  material was not sent or posted anywhere. Already submitted → that last statement is
  false: tell the user to ask the commission, never to sign it;
- the author's phone and each author's Istina IRID written next to their names;
- the commission assigns the number (format xxx.nnnn-YYYY) — after approval, enter number and
  date into Istina;
- rejected and sent to another journal → a **new** clearance for the new journal.

## Common mistakes

| Mistake | Reality |
|---|---|
| Filling commission, dates, signatures | Commission's job; the author changes only yellow text |
| Adding volume/issue/article number | Not given, the faculty confirmed |
| Leaving the highlight "for reference" | Memo: remove before printing |
| Authors in nominative, or only the first author | Genitive, every author, as in the sample |
| Translating the title into Russian | Title as it will be published |
| "Already submitted — fine, just date it earlier" | Say it is late; dates are the commission's |
| Forgetting poster/slides or the outside co-author's letter | Not on the blank, so easy to miss; go through section 4 |
