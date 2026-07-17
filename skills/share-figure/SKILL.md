---
name: share-figure
description: Use when packaging a generated figure, plot, or chart to hand to a collaborator, reviewer, or supervisor - bundling the image with its generating code, the exact input data, and provenance so the recipient can reproduce it from scratch. Use when the user says "собрать картинку для отправки", "отправить с кодом и данными", "чтобы можно было воспроизвести", "share this figure", "prepare figure for sending", or prepares any reproducible figure handover.
---

# Share Figure — Reproducible Figure Bundle

## Overview

A figure you send is not an image. It is a **self-contained bundle** that lets the
recipient regenerate the figure on their own machine and get the same result. The
deliverable is *reproduction*, not a picture.

**Core principle: the bundle is not done until a clean copy reproduces the figure.**
Copy the bundle to an empty directory, run it in a fresh shell, and confirm the output
matches the reference image. "The script runs" is not the gate — "the figure comes out
the same" is.

## The bundle IS these parts

```
<figure-name>_share/
  README.md          # what it is, provenance, how to run, expected output
  MANIFEST.txt       # every file: relative path, size, sha256
  make_figure.*      # ONE self-contained script (any language; see rules)
  environment.*      # dependency snapshot (lockfile / freeze / env export)
  data/              # the EXACT inputs make_figure reads, nothing else
  figure/            # the reference image(s) the recipient must reproduce
```

Assemble every part. A bundle missing `data/`, the reference `figure/`, or provenance
is incomplete — say so rather than shipping it.

## Rules

1. **One self-contained script.** `make_figure.*` must run using only publicly available
   dependencies plus what ships in the bundle. It must **not** import project-internal
   modules the recipient does not have (private packages, repo helpers, notebook globals)
   unless you **vendor** the functions it needs into the bundle (copy them into the script
   or into a `bundle_lib.*` beside it). A stray `import <private_module>` in a handed-over
   script is the #1 repro-killer — the recipient does not have your repo.

2. **Relative paths only.** No `C:\Users\...`, `/home/...`, or network mounts. Put a
   single `DATA_DIR = <bundle>/data` reference at the top and read everything under it.

3. **Ship the exact data the script reads — do not guess which parts matter.** When the
   real input is large, you cannot eyeball which columns/fields/arrays the script actually
   touches. Two valid options:
   - **Default:** ship the real input the script already loads.
   - **Slim only after proof:** if the input is too large to send, export a reduced input,
     adapt the loader, then **verify the slimmed bundle reproduces the identical figure**
     before choosing it. Never slim on a guess — dropping a used field yields a wrong or
     crashing figure.

4. **Reproduction is the completion gate.** From a clean copy of the folder, in a fresh
   shell, run the documented command. Confirm it regenerates the figure and that it
   matches `figure/<name>.<ext>` — compare visually AND by hash/array where the plot is
   deterministic. Only after this passes is the bundle done.

5. **Capture provenance in README.** Source data path(s) on the origin machine, the
   identity of the dataset (which experiment/run/date/version), the code version
   (`git rev-parse HEAD` or a tag), and the exact parameters/thresholds used. Without
   this the recipient cannot tell what they are looking at.

6. **Environment snapshot, not a rebuild promise.** Include a dependency snapshot
   (`pip freeze` / `conda list` / lockfile / `renv.lock` / `package-lock.json`) and call
   out any version-fragile or hard-to-install libraries — their APIs can differ across
   releases and a mismatch silently changes the figure. Note in README that the
   environment may not rebuild cleanly on a different OS; the snapshot is primarily for
   diagnosing a mismatch, not a guarantee the recipient can recreate it verbatim.

7. **Keep console output encoding-safe.** Use plain ASCII status markers (`[OK]` /
   `[FAILED]`) rather than emoji/unicode in the script's stdout — non-UTF-8 consoles
   (e.g. Windows cp1251) crash on unicode.

8. **Confirm it is OK to send, and how.** The data may be unpublished or sensitive —
   check with the user before sending it outside the group. Large data goes out-of-band
   (drive/transfer link) with its sha256 from MANIFEST, not zipped inline. Small bundles:
   zip the folder.

## Quick Reference

| Concern | Do this |
|---|---|
| Script imports a private/internal module | Vendor the needed functions into the bundle |
| Hardcoded absolute paths | Single `DATA_DIR` at top, relative reads only |
| Which parts of the input to include | Ship the real input; slim only after verifying identical output |
| "It runs" vs "it reproduces" | Run from a clean copy; compare output to `figure/` reference |
| Env won't rebuild on recipient's OS | Ship a dependency snapshot; treat it as diagnostic, not a rebuild |
| Large / sensitive data | Confirm with user; send out-of-band with sha256, not inline |
| Provenance | README: data path, dataset id, code version/commit, params |

## Common Mistakes

| Mistake | Why it fails | Fix |
|---|---|---|
| Send just the image | Recipient can't check or rebuild it | Full bundle with code + data + reference |
| Leave `import <private module>` in script | Recipient has no repo | Vendor functions into the bundle |
| Guess which fields are used and slim to those | May drop a field the script reads -> wrong or crashing figure | Ship real input, or verify slimmed reproduces |
| Verify by running in the origin folder | Origin has the repo, absolute paths, warm caches — hides breakage | Run from a clean copy in a fresh shell |
| Treat "no error" as success | Script can run and still draw a different figure | Compare output to reference image/hash |
| Ship an env export and assume it rebuilds | Fragile deps rarely rebuild cross-platform | Snapshot for diagnosis; recipient uses own env |
| Emoji/unicode in console output | UnicodeEncodeError on non-UTF-8 consoles | ASCII markers only |
