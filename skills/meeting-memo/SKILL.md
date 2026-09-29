---
name: meeting-memo
description: Use when turning a recorded meeting, call or discussion (Telemost, Zoom, Teams, a phone voice memo; .webm, .mp4, .m4a, .wav) or its raw auto-transcript into a written summary, memo, minutes or action list without losing details. Use when the user says "расшифруй встречу", "сделай саммари встречи", "мемо по записи", "протокол созвона", "итоги встречи", "транскрибируй видео", "что решили на созвоне", "meeting notes", "summarize this recording".
---

# Meeting Memo — from a recording to a memo people can act on

## Overview

A meeting memo is read by people who were there and want the decisions, and by people
who were not and must act on them. Auto-transcripts are rough: no speaker labels, names
misheard, phrases cut. **Core principle: every claim in the memo can be checked against
the recording in under a minute**, and whatever the transcript does not settle is listed
for a human rather than silently guessed.

## Step 1. Get a transcript

1. Look for an existing transcript next to the recording and in the project folder.
   Telemost and other tools may have saved `… — транскрипт.txt` / `.srt` and
   `… — чат.txt`. The chat often holds links and correctly spelled names — read it, but
   check its message dates: a chat file can carry over from an earlier meeting.
2. No transcript: run `python transcribe.py RECORDING OUT_STEM --prompt "names, terms"`
   (the script lives beside this file). It uses faster-whisper `large-v3-turbo`,
   writes `OUT_STEM.txt` with `[hh:mm:ss]` per line plus `.srt`, flushing as it goes.
   - On a CPU it takes **1–1.5 times the length of the recording** (1 h of audio ≈
     1–1.5 h).
     Anything over a few minutes is a background job that outlives your turn, never a
     foreground shell. Say how long it will take.
   - `--prompt` with the participants' names and the project's terms (from Step 2)
     noticeably improves spelling of names and acronyms. Gather it before launching.
   - Needs `pip install faster-whisper`; the model (~1.6 GB) downloads on first run.
3. Test on one minute before the full run (`clip_timestamps=[300, 360]`): wrong
   language, silence or a decoding error show up there, not an hour later.

## Step 2. Gather context before writing

The transcript alone does not tell you who "Константин Владимирович / Владимир
Владимирович" is. Before writing, look for:
- earlier memos and transcripts of the same series (same folder, project notes);
- the document the meeting is about (application draft, paper, plan). Page and
  section numbers said aloud tell you which version the speakers had in front of them;
  compare against that version, not only the latest;
- the participant list: invitation, chat, project files.

Resolve names from this context. Record every correction you made (misheard → real
name) for the check list in the memo. When the sources disagree with each other (one
memo says "Александр", this recording says "Алексей" throughout), do not pick: write
the initials and put both variants on the check list.

## Step 3. Read the whole transcript, then write

Read all of it in chunks, not the first third. Make a topic map first: topic → time
range. Then write the memo in this shape, in the language of the meeting:

1. **Header** — date, start time, duration, subject; participants with roles, noting
   that attribution is restored from forms of address, not from speaker labels. If
   anyone set conditions on the recording ("не выкладывайте в сеть"), state them here
   and keep the memo and transcript out of shared or public places.
2. **Decisions** — numbered, one line each, first. Deadlines with date **and weekday**,
   checked against the calendar.
3. **Topic sections** in order of importance, each with its time range. Inside: who
   holds which position, arguments on both sides, what was agreed, what remained open.
   Numbers, dates, names of papers and tools — kept exactly. A formulation worth taking
   into a text word for word is quoted with its timecode.
4. **What it means for the document** — only if the meeting was about a document in
   work: where the decisions contradict or change its current version, by section.
   Your own inferences that nobody voiced are allowed here, each marked as yours
   ("вывод составителя, на встрече не звучал").
5. **Actions** — table: who / what / when.
6. **Open questions.**
7. **What to check against the recording** — misheard names and how you resolved them,
   merged or cut-off turns, inaudible spots, each with a timecode.

Size follows the content, not the template: a section with nothing to say is
dropped, a 20-minute call can fit on one page. Decisions, actions and the check list
are never dropped.

Every factual line carries a timecode `[mm:ss]` or range `[mm:ss–mm:ss]` (`hh:mm:ss`
past an hour).

Interpersonal friction (reproaches, who failed to show up) goes in only as its facts
and practical result — what had been agreed, what was missed, what was agreed so it does
not happen again — without the reproaches. The memo gets circulated.

## Step 4. Completeness pass

Walk the transcript again in 5-minute windows. For each window: is it reflected in the
memo, or consciously dropped (greetings, "вы меня слышите", repetition)? A window with
substance and no trace in the memo is a gap — fill it. Check every number and date in
the memo against its timecode.

Save the memo as Markdown next to the recording (`Мемо встречи ДД.ММ.ГГГГ — <тема>.md`)
unless told otherwise; `.docx` via pandoc if the user circulates Word files.

## Common mistakes

| Mistake | Consequence |
|---|---|
| No timecodes | Nobody can verify a disputed line without re-listening to the hour |
| Summarising without project context | Leader and participants unnamed or misnamed |
| Guessing a misheard name silently | A wrong name in a circulated memo |
| Consensus invented where the talk ended open | People act on a decision that was not made |
| Running transcription in the foreground | The run dies with the turn, hour of CPU lost |
| Reading only the start of a long transcript | The decisions at the end are missing |
