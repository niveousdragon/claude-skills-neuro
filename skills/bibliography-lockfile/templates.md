# Enforcement templates

Two layers on top of the generator. The hook is executed by the harness, not the
model — an agent cannot decide to ignore it. The project-rule text is auto-loaded
into every session (CLAUDE.md is read from the cwd and all parent directories, so
place a copy at the highest directory your agents start from).

## 1. PreToolUse hook — `.claude/settings.json` in the project root

Blocks Write/Edit on any `.bib` before it is applied. Runs with cwd = the directory
the session started in, so it covers sessions started in this project. Known limit:
writes via shell (`echo > refs.bib`) are not caught — the hook closes the normal
path, the CLAUDE.md rule and the `--compare` gate cover the rest.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [
          { "type": "command", "command": "python tools/bibgen/hook_guard.py" }
        ]
      }
    ]
  }
}
```

If a `.claude/settings.json` already exists, merge the `hooks` block into it instead
of replacing the file.

## 2. Project rule — append to `CLAUDE.md`

```markdown
## Bibliography: generated only, never hand-written

Every `.bib` in this project is a GENERATED artifact. To add or change a reference:

1. add an identifier (`doi:` / `arxiv:` / `pmlr:` / `openalex_title:`) to
   `tools/bibgen/sources.yaml` — never write BibTeX text by hand;
2. run `python tools/bibgen/bibgen.py` (authors come from publisher metadata);
3. gate before any submission: `python tools/bibgen/bibgen.py --compare <bib>` —
   zero mismatches, zero FAILED.

FORBIDDEN: typing or editing author fields in any `.bib`; expanding initials into
full names from memory; accepting model-generated BibTeX without a registry source.
A manual author field is allowed only as `authors_override` in sources.yaml with a
`verified:` stamp (date + how the byline was checked). Direct `.bib` edits are also
blocked by a PreToolUse hook (`.claude/settings.json`).
```

## 3. Optional hard layers

- **git pre-commit**: run `bibgen.py --compare` and fail the commit on mismatch —
  covers humans and shell writes too (requires the `.bib` to be git-tracked).
- **CI**: the same compare as a required check on push/PR.
