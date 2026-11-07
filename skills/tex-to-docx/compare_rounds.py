#!/usr/bin/env python3
"""Word comparison of the first and the last version of a paper, every change signed
with the round it came from.

Input is a round log: one line per saved version ("snapshot") of the paper, oldest
first, with its date and the caption of the round that produced it:

    # path to .tex | date | caption [| aux: path]
    submission/paper.tex      | 07.05.2026 | submitted
    rounds/2026-11-05/paper.tex | 05.11.2026 | agent, 05.11: cuts for the 10-page limit
    rounds/2026-11-06/paper.tex | 06.11.2026 | author's decision, 06.11

Every snapshot goes through one pipeline: LaTeX's own numbers written in from its
.aux (aux_numbers.py), tex2docx, the reference list under its heading, picture
descriptions made neutral and local paths removed. Word compares the first and the
last; round_labels.py then signs each change with its round. Checks run before
anything is handed over and are printed as a block.

Usage:
    python compare_rounds.py rounds.txt -o OUTDIR [--csl style.csl] [--pairs]

Requires Microsoft Word (Windows, pywin32) for the comparison itself.
"""
import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import aux_numbers  # noqa: E402
import round_labels  # noqa: E402
import tex2docx  # noqa: E402

UNDETERMINED_LIMIT = 0.05


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---------------------------------------------------------------- round log
def read_log(path):
    path = Path(path).resolve()
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        f = [x.strip() for x in line.split("|")]
        if len(f) < 3 or not re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}", f[1]):
            sys.exit("[FAILED] %s, line %d: need 'path | dd.mm.yyyy | caption'" % (path.name, n))
        tex = (path.parent / f[0]).resolve()
        if not tex.exists():
            sys.exit("[FAILED] %s, line %d: %s not found" % (path.name, n, tex))
        opt = {"aux": None, "dir": None}
        for extra in f[3:]:
            key, _, val = extra.partition(":")
            if key.strip() in opt and val.strip():
                opt[key.strip()] = (path.parent / val.strip()).resolve()
        rows.append({"tex": tex, "date": f[1], "caption": f[2], "aux": opt["aux"],
                     "base": opt["dir"] or tex.parent})
    if len(rows) < 2:
        sys.exit("[FAILED] the round log needs at least two snapshots")
    return rows


def find_aux(row, build_dir):
    """The .aux of this snapshot's PDF build: given, next to the .tex, in a build*/ folder,
    or made by latexmk into our own folder (the source folder is not written to)."""
    if row["aux"]:
        return row["aux"]
    tex = row["tex"]
    cands = [tex.with_suffix(".aux")] + sorted(tex.parent.glob("build*/" + tex.stem + ".aux"),
                                                key=lambda p: p.stat().st_mtime, reverse=True)
    cands.append(build_dir / (tex.stem + ".aux"))          # built by an earlier run
    for c in cands:
        if c.exists() and c.stat().st_mtime >= tex.stat().st_mtime - 1:
            return c
    build_dir.mkdir(parents=True, exist_ok=True)
    log("no fresh .aux for %s; building it with latexmk" % tex.name)
    base = row["base"]
    env = dict(os.environ, BIBINPUTS=str(base) + os.pathsep, TEXINPUTS=str(base) + os.pathsep)
    r = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-outdir=" + str(build_dir), str(tex)],
                       cwd=base, env=env, capture_output=True, text=True, errors="replace")
    aux = build_dir / (tex.stem + ".aux")
    if not aux.exists():
        sys.exit("[FAILED] latexmk made no .aux for %s:\n%s" % (tex, r.stdout[-2000:]))
    return aux


# ---------------------------------------------------------------- one snapshot
def move_references(docx_path):
    """citeproc appends the entries at the very end; put them under the References heading."""
    import docx
    doc = docx.Document(str(docx_path))
    heads = [p for p in doc.paragraphs if p.style.name.startswith("Heading")
             and p.text.strip().lower() in ("references", "bibliography", "список литературы", "литература")]
    entries = [p for p in doc.paragraphs if p.style.name == "Bibliography"]
    if len(heads) == 1 and entries:
        anchor = heads[0]._p
        for p in entries:
            anchor.addnext(p._p)
            anchor = p._p
        doc.save(str(docx_path))


def neutralise(docx_path):
    """Picture descriptions become 'Figure N' and the build machine's paths go.

    Pandoc writes the caption and the figure's absolute path into each picture's
    properties; when either differs between versions Word shows an unchanged picture
    as deleted and inserted, and the path would carry the folder layout of this
    machine to the reader."""
    tmp = docx_path.with_suffix(".tmp.docx")
    n = [0, 0]

    def doc_pr(m):
        n[0] += 1
        return '<wp:docPr%s descr="Figure %d"' % (m.group(1), n[0])

    def pic_pr(m):
        n[1] += 1
        return '<pic:cNvPr%sdescr="Figure %d"' % (m.group(1), n[1])

    with zipfile.ZipFile(docx_path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                xml = data.decode("utf-8")
                xml = re.sub(r'<wp:docPr([^>]*?) descr="[^"]*"', doc_pr, xml)
                xml = re.sub(r'<pic:cNvPr([^>]*?)descr="[^"]*"', pic_pr, xml)
                data = xml.encode("utf-8")
            elif item.filename == "docProps/custom.xml":
                data = re.sub(rb'<property [^>]*name="(?:bibliography|csl)">.*?</property>', b"", data, flags=re.S)
            zout.writestr(item, data)
    tmp.replace(docx_path)
    with zipfile.ZipFile(docx_path) as z:
        leaks = [nm for nm in z.namelist() if nm.endswith((".xml", ".rels"))
                 and re.search(rb"[A-Za-z]:[/\\]+Users", z.read(nm))]
    return leaks


def build_snapshot(i, row, out, csl, final):
    stem = "%02d_%s" % (i, row["tex"].stem)
    aux = row["aux_found"]
    prepared = out / "prepared" / (stem + ".tex")
    problems = aux_numbers.prepare(row["tex"], aux, prepared, base=row["base"], final=final)
    raw = row["tex"].read_text(encoding="utf-8", errors="replace")
    bibs = tex2docx.find_bibliography(tex2docx.expand_inputs(raw, row["base"]), row["base"])
    docx_path = out / "snapshots" / (stem + ".docx")
    docx_path.parent.mkdir(parents=True, exist_ok=True)
    tex2docx.convert(prepared, docx_path, bib=[str(b) for b in bibs] or None, csl=csl)
    move_references(docx_path)
    leaks = neutralise(docx_path)
    if leaks:
        problems.append("local paths left in " + ", ".join(leaks))
    return docx_path, aux, problems


# ---------------------------------------------------------------- Word
def word():
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    w = win32com.client.DispatchEx("Word.Application")   # own instance: a shared one stalls at SaveAs2
    w.Visible = False
    w.DisplayAlerts = 0
    return w


def word_compare(w, old, new, out, author):
    d1 = w.Documents.Open(str(old), False, True)
    d2 = w.Documents.Open(str(new), False, True)
    # new document, word level; formatting, case, white space, tables, headers, footnotes,
    # text boxes, fields, comments and moves all compared
    res = w.CompareDocuments(d1, d2, 2, 1, True, True, True, True, True, True, True, True, True, True, author)
    n = res.Revisions.Count
    res.SaveAs2(str(out), 16)
    res.Close(False)
    d1.Close(False)
    d2.Close(False)
    return n


def same(a, b):
    """Same words and signs in the same order, up to Word's letter forms in equations. Spaces
    are not compared: where Word joins two paragraphs, the XML keeps no trace of the break,
    and the check in Word itself compares the text character by character."""
    return (round_labels.TOKEN.findall(round_labels.same_glyphs(a))
            == round_labels.TOKEN.findall(round_labels.same_glyphs(b)))


def norm(t):
    return re.sub(r"\s+", " ", t.replace("\r", " ").replace("\x07", " ").replace("\x0c", " ")).strip()


def word_checks(w, tracked, first, last, pdf, tmp):
    """'Accept all' against the last version and 'reject all' against the first, in Word
    itself; then the tracked file as Word lays it out, with the changes shown, as PDF."""
    res = {}
    for act, side in (("AcceptAllRevisions", last), ("RejectAllRevisions", first)):
        c = Path(tmp) / (act + ".docx")
        shutil.copy(tracked, c)
        d = w.Documents.Open(str(c))
        getattr(d, act)()
        got = norm(d.Content.Text + " ".join(f.Range.Text for f in d.Footnotes))
        d.Close(False)
        d = w.Documents.Open(str(side), False, True)
        want = norm(d.Content.Text + " ".join(f.Range.Text for f in d.Footnotes))
        d.Close(False)
        diff = [(a, b) for a, b in zip(want, got) if a != b]
        res[act] = {"equal": got == want, "same_glyphs": same(got, want), "len": (len(want), len(got)),
                    "differing": len(diff),
                    "pairs": sorted({(a, b) for a, b in diff})[:10]}
    d = w.Documents.Open(str(tracked), False, True)
    res["revisions"] = d.Revisions.Count
    res["pages"] = d.ComputeStatistics(2)
    # PDF with the changes and their balloons shown (wdExportDocumentWithMarkup = 7)
    d.ExportAsFixedFormat(str(pdf), 17, False, 0, 0, 1, 1, 7)
    d.Close(False)
    return res


def render_pages(pdf, folder, pages):
    import fitz
    folder.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf))
    out = []
    for p in pages:
        if 0 <= p < len(doc):
            png = folder / ("page_%02d.png" % (p + 1))
            doc[p].get_pixmap(dpi=80).save(str(png))
            out.append(png)
    return out, len(doc)


# ---------------------------------------------------------------- checks on text
EMPTY_REF = re.compile(r"\?\?|\[(?:sec|fig|tab|eq|app|supp|thm|lem)[:\-][^\]\s]*\]"
                       r"|(?:Figures?|Figs?\.|Tables?|Sections?|§|Supplementary|Appendix|Eqs?\.)\s*(?=[,;:.)\]]|and\b)")
RENUMBER_BEFORE = re.compile(r"(?:Figures?|Figs?\.|Tables?|Sections?|§|Eqs?\.|Equations?|Appendix|Supplementary"
                             r"(?: Fig\.| Figure| Table| Section)?)[\s\u00a0~]*S?$")


def empty_refs(text):
    return [text[max(0, m.start() - 40):m.end() + 20] for m in EMPTY_REF.finditer(text)]


def renumberings(records):
    """Changes that only swap one number of a heading, figure, table, equation or section for
    another: a deletion and an insertion side by side, both a bare number, standing right after
    "Figure", "Table", "Section", "§", "Eq." ... or at the start of a heading. A changed value
    ("p = 0.053" -> "0.086", a number in a table cell) is not numbering and is not counted."""
    out = []
    for a, b in zip(records, records[1:]):
        if a["part"] == b["part"] and a["para"] == b["para"] and {a["kind"], b["kind"]} == {"del", "ins"}:
            ta, tb = a["text"].strip(), b["text"].strip()
            bare = re.fullmatch(r"S?[\d.]+[.:]?", ta) and re.fullmatch(r"S?[\d.]+[.:]?", tb)
            heading = a.get("style", "").lower().startswith("heading") and not a["before"].strip()
            if ta != tb and bare and (heading or RENUMBER_BEFORE.search(a["before"])):
                out.append((a["before"][-25:], ta, tb, a["caption"]))
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log", help="round log: 'path | dd.mm.yyyy | caption' per snapshot, oldest first")
    ap.add_argument("-o", "--out", required=True, help="output folder")
    ap.add_argument("--csl", default=None, help="one citation style for all versions (default: author-date, "
                    "so that a new reference does not renumber every citation after it)")
    ap.add_argument("--pairs", action="store_true", help="also write one Word file per round")
    ap.add_argument("--name", default=None, help="name of the tracked file (default: from the last .tex)")
    ap.add_argument("--reuse", action="store_true", help="keep the Word files of snapshots already built in OUT "
                    "(only the captions changed in the log)")
    args = ap.parse_args()
    rows = read_log(args.log)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    name = args.name or rows[-1]["tex"].stem + "_rounds_tracked"
    tracked = out / (name + ".docx")
    raw = out / (name + "_unsigned.docx")

    snaps, problems = [], []
    for i, row in enumerate(rows):
        reused = args.reuse and (out / "snapshots" / ("%02d_%s.docx" % (i, row["tex"].stem))).exists()
        if not reused or i == len(rows) - 1:      # the last one gives the numbers of all
            row["aux_found"] = find_aux(row, out / "build" / ("%02d_%s" % (i, row["tex"].stem)))
    final = aux_numbers.read_aux(rows[-1]["aux_found"])[0]
    for i, row in enumerate(rows):
        log("snapshot %d: %s" % (i, row["tex"]))
        d = out / "snapshots" / ("%02d_%s.docx" % (i, row["tex"].stem))
        if args.reuse and d.exists():
            snaps.append(d)
            log("  reused %s" % d.name)
            continue
        d, aux, probs = build_snapshot(i, row, out, args.csl, final)
        snaps.append(d)
        problems += ["snapshot %d: %s" % (i, p) for p in probs]
        log("  aux %s; %s" % (aux, "[OK]" if not probs else "[FAILED] " + "; ".join(probs)))

    rounds = [None] + [(r["caption"], r["date"]) for r in rows[1:]]
    w = word()
    try:
        if raw.exists():
            raw.unlink()
        log("Word compares snapshot 0 with snapshot %d" % (len(rows) - 1))
        n = word_compare(w, snaps[0], snaps[-1], raw, "compare")
        log("  %d revisions" % n)
        records, extra = round_labels.label_docx(raw, snaps, rounds, tracked)
        raw.unlink()
        with tempfile.TemporaryDirectory() as tmp:
            pdf = out / (name + ".pdf")
            wc = word_checks(w, tracked, snaps[0], snaps[-1], pdf, tmp)
        pair_files = []
        if args.pairs:
            for k in range(1, len(rows)):
                pf = out / ("%s_round%d.docx" % (name, k))
                for f in (pf, raw):
                    if f.exists():
                        f.unlink()
                word_compare(w, snaps[k - 1], snaps[k], raw, rows[k]["caption"])
                # one round: every change takes its caption and its date
                round_labels.label_docx(raw, [snaps[k - 1], snaps[k]], [None, rounds[k]], pf, default=rounds[k])
                raw.unlink()
                pair_files.append(pf)
    finally:
        w.Quit()

    # checks on the XML: the two views of the tracked file against the two ends
    v = round_labels.views_text(tracked)
    first, last = round_labels.views_text(snaps[0])["new"], round_labels.views_text(snaps[-1])["new"]
    texts = [round_labels.views_text(s)["new"] for s in snaps]
    holes = {i: empty_refs(t) for i, t in enumerate(texts)}
    text_recs = [r for r in records if r["text"].strip()]
    unknown = [r for r in text_recs if r["caption"] == round_labels.UNKNOWN]
    by_neighbour = [r for r in text_recs if r["how"] == "по соседней правке"]
    renum = renumberings(records)
    pages, n_pages = render_pages(out / (name + ".pdf"), out / "pages", [0, 1, 4, 9, 19, 29])

    with open(out / (name + "_changes.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["n", "part", "paragraph", "kind", "text", "caption", "how", "words by round"])
        for i, r in enumerate(records, 1):
            wr.writerow([i, r["part"].split("/")[-1], r["para"], r["kind"], r["text"][:300], r["caption"], r["how"],
                         " ".join("%d:%d" % kv for kv in sorted(r["rounds"].items()))])

    counts = {}
    for r in text_recs:
        counts[r["caption"]] = counts.get(r["caption"], 0) + 1
    lines = ["=== checks: %s" % tracked.name,
             "snapshots: %d; Word revisions: %d (text changes %d, other marks %d)"
             % (len(snaps), wc["revisions"], len(text_recs), extra),
             "signed: %d of %d text changes (%d of them by the neighbouring change); %s: %d (%.1f of 100)"
             % (len(text_recs) - len(unknown), len(text_recs), len(by_neighbour), round_labels.UNKNOWN,
                len(unknown), 100.0 * len(unknown) / max(1, len(text_recs))),
             "accept all = last snapshot (XML): %s, up to Word's letter forms in equations: %s; "
             "reject all = first snapshot (XML): %s, up to letter forms: %s"
             % (v["new"] == last, same(v["new"], last), v["old"] == first, same(v["old"], first))]
    for act in ("AcceptAllRevisions", "RejectAllRevisions"):
        r = wc[act]
        lines.append("%s in Word: %s; up to letter forms in equations: %s (lengths %s, %d characters differ%s)"
                     % (act, "equal" if r["equal"] else "DIFFER", "equal" if r["same_glyphs"] else "DIFFER",
                        r["len"], r["differing"],
                        ", pairs " + ascii(r["pairs"]) if r["pairs"] else ""))
    lines.append("empty references per snapshot: %s" % {i: len(h) for i, h in holes.items()})
    for i, h in holes.items():
        for s in h[:3]:
            lines.append("    %d: %s" % (i, ascii(s)))
    lines.append("number-only changes (renumbering): %d %s" % (len(renum), ascii(renum[:5])))
    lines.append("preparation problems: %d" % len(problems))
    lines += ["    " + p for p in problems]
    lines.append("pages in Word with changes shown: %s; rendered: %s" % (n_pages, ", ".join(p.name for p in pages)))
    lines.append("captions:")
    lines += ["    %4d  %s" % (n, c) for c, n in sorted(counts.items(), key=lambda kv: -kv[1])]
    share = len(unknown) / max(1, len(text_recs))
    if share > UNDETERMINED_LIMIT and not args.pairs:
        lines.append("[NOTE] more than %d of 100 changes unsigned: rerun with --pairs for one file per round"
                     % int(UNDETERMINED_LIMIT * 100))
    if pair_files:
        lines.append("one file per round: " + ", ".join(p.name for p in pair_files))
    ok = (not problems and same(v["new"], last) and same(v["old"], first) and not any(holes.values()) and not renum
          and share <= UNDETERMINED_LIMIT)
    lines.append("[OK]" if ok else "[FAILED] see above")
    report = "\n".join(lines)
    (out / (name + "_checks.txt")).write_text(report + "\n", encoding="utf-8")
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
