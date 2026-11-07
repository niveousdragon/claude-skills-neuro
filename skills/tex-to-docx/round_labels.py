"""Give every tracked change of a Word comparison the round it came from.

Word compares only two files, the first version and the last, and writes one
author on every change. The rounds in between are known only from the saved
versions ("snapshots") of the paper. Here each word of the first version is
followed forward through the snapshots to the round that removed it, and each
word of the last version backward to the round that added it. A deleted
stretch in the Word file then takes the round of most of its words, an
inserted one likewise; that round's caption ("агент, 06.11: сокращение под
10 страниц") becomes the author of the change and its date the date of the
change, so the reader sees who and why right in Word's balloon.

Pure Python on the XML of the .docx files: no Word needed, so it is tested
without it.
"""
import difflib
import re
import zipfile
from collections import Counter, defaultdict

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
PARTS = ("word/document.xml", "word/footnotes.xml", "word/endnotes.xml")
UNKNOWN = "источник не определён"
TOKEN = re.compile(r"\w+|[^\w\s]")


def q(ns, tag):
    return "{%s}%s" % (ns, tag)


TEXT_TAGS = {q(W, "t"), q(W, "delText"), q(M, "t")}
SPACE_TAGS = {q(W, "tab"), q(W, "br"), q(W, "cr")}
TEXT_REV = {q(W, "ins"): "ins", q(W, "moveTo"): "ins", q(W, "del"): "del", q(W, "moveFrom"): "del"}
MARK_REV = {q(W, "ins"): "ins", q(W, "del"): "del"}


def _revision(el, para):
    """The tracked change an element of text belongs to, or None."""
    a = el.getparent()
    while a is not None and a is not para:
        if a.tag in TEXT_REV:
            return a
        if a.tag == q(M, "r"):                    # a run of an equation marks it inside its properties
            for rpr in a.findall(q(W, "rPr")):
                for child in rpr:
                    if child.tag in MARK_REV:
                        return child
        a = a.getparent()
    return None


class Part:
    """One XML part of a .docx read as text, word by word, in the 'old' and 'new' views.

    In a file without tracked changes both views are the same text. In a tracked file
    the old view is what "reject all" leaves and the new view what "accept all" leaves;
    every word remembers the tracked change it sits in.
    """

    def __init__(self, xml):
        self.root = etree.fromstring(xml)
        self.revs = []                  # tracked changes with text, in document order
        self.rev_kind, self.rev_para, self.rev_text, self.rev_before, self.rev_style = [], [], [], [], []
        index = {}
        chunks = []                     # (para, text, rev index or -1)
        for pi, p in enumerate(self.root.iter(q(W, "p"))):
            seen = []                   # text of this paragraph so far, as "accept all" shows it
            style = p.find("%s/%s" % (q(W, "pPr"), q(W, "pStyle")))
            style = style.get(q(W, "val"), "") if style is not None else ""
            for el in p.iter():
                if el.tag in TEXT_TAGS:
                    text = el.text or ""
                elif el.tag in SPACE_TAGS and el.getparent().tag in (q(W, "r"), q(M, "r")):
                    text = " "
                else:
                    continue
                rev = _revision(el, p)
                r = -1
                if rev is not None:
                    if id(rev) not in index:
                        index[id(rev)] = len(self.revs)
                        self.revs.append(rev)
                        kind = TEXT_REV.get(rev.tag) or MARK_REV.get(rev.tag)
                        self.rev_kind.append(kind)
                        self.rev_para.append(pi)
                        self.rev_text.append("")
                        self.rev_before.append("".join(seen)[-40:])
                        self.rev_style.append(style)
                    r = index[id(rev)]
                    self.rev_text[r] += text
                if r < 0 or self.rev_kind[r] == "ins":
                    seen.append(text)
                chunks.append((pi, text, r))
            chunks.append((pi, "\n", -1))
        self.views = {v: self._tokens(chunks, v) for v in ("old", "new")}

    def _tokens(self, chunks, view):
        drop = "ins" if view == "old" else "del"
        text, owner, para = [], [], []
        for pi, t, r in chunks:
            if r >= 0 and self.rev_kind[r] == drop:
                continue
            text.append(t)
            owner.extend([r] * len(t))
            para.extend([pi] * len(t))
        s = "".join(text)
        toks = []
        for m in TOKEN.finditer(s):
            revs = {owner[i] for i in range(m.start(), m.end()) if owner[i] >= 0}
            toks.append((m.group(), para[m.start()], revs))
        return {"text": s, "tokens": toks}

    def words(self, view="new"):
        return [(t, p) for t, p, _ in self.views[view]["tokens"]]


def align(a, b):
    """Matched words of two texts: {index in a: index in b}.

    Paragraphs first (fast, and a moved paragraph does not drag the words of its
    neighbours with it), then word by word inside the paragraphs that differ.
    """
    def paras(words):
        out, cur, last = [], [], None
        for i, (t, p) in enumerate(words):
            if p != last and cur:
                out.append(cur)
                cur = []
            cur.append(i)
            last = p
        if cur:
            out.append(cur)
        return out

    pa, pb = paras(a), paras(b)
    ka = [" ".join(a[i][0] for i in g) for g in pa]
    kb = [" ".join(b[i][0] for i in g) for g in pb]
    match = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ka, kb, autojunk=False).get_opcodes():
        if op == "equal":
            for ga, gb in zip(pa[i1:i2], pb[j1:j2]):
                match.update(zip(ga, gb))
            continue
        ia = [i for g in pa[i1:i2] for i in g]
        ib = [j for g in pb[j1:j2] for j in g]
        sm = difflib.SequenceMatcher(None, [a[i][0] for i in ia], [b[j][0] for j in ib], autojunk=False)
        for x, y, n in sm.get_matching_blocks():
            for d in range(n):
                match[ia[x + d]] = ib[y + d]
    return match


def fates(snapshots):
    """For each word of the first snapshot, the round that removed it (None: it stayed);
    for each word of the last, the round that added it (None: it was there from the start).
    Round k is the step from snapshot k-1 to snapshot k."""
    steps = [align(snapshots[k - 1], snapshots[k]) for k in range(1, len(snapshots))]
    died = [None] * len(snapshots[0])
    alive = {i: i for i in range(len(snapshots[0]))}
    for k, step in enumerate(steps, 1):
        nxt = {}
        for i, pos in alive.items():
            if pos in step:
                nxt[i] = step[pos]
            else:
                died[i] = k
        alive = nxt
    born = [None] * len(snapshots[-1])
    alive = {j: j for j in range(len(snapshots[-1]))}
    for k in range(len(steps), 0, -1):
        back = {v: u for u, v in steps[k - 1].items()}
        nxt = {}
        for j, pos in alive.items():
            if pos in back:
                nxt[j] = back[pos]
            else:
                born[j] = k
        alive = nxt
    return died, born


def caption_of(votes, rounds, share=0.25):
    """Caption and date for a change whose words came from rounds `votes` (Counter k -> words).
    Every round with at least a quarter of the words is named, oldest first; the date is the
    latest of them, when the change took its final form."""
    total = sum(votes.values())
    ks = sorted(k for k, n in votes.items() if n >= share * total)
    return " + ".join(rounds[k][0] for k in ks), rounds[ks[-1]][1]


def label_part(tracked_xml, snapshot_xmls, rounds, default=(UNKNOWN, None)):
    """Label the tracked changes of one XML part. `rounds[k]` = (caption, date) for k >= 1.

    Returns the new XML and one record per tracked change."""
    snaps = [Part(x).words() if x is not None else [] for x in snapshot_xmls]
    died, born = fates(snaps)
    part = Part(tracked_xml)
    votes = defaultdict(Counter)
    for view, snap, fate, kind in (("old", snaps[0], died, "del"), ("new", snaps[-1], born, "ins")):
        toks = part.views[view]["tokens"]
        m = align([(t, p) for t, p, _ in toks], snap)
        for i, (_, _, revs) in enumerate(toks):
            for r in revs:
                if part.rev_kind[r] == kind and i in m and fate[m[i]] is not None:
                    votes[r][fate[m[i]]] += 1
    n = len(part.revs)
    caption, how = [None] * n, [""] * n
    for r in range(n):
        if votes[r]:
            caption[r] = caption_of(votes[r], rounds)
            how[r] = "по словам"
    # A change whose words no snapshot explains (Word matched the two versions a little
    # differently from the chain, or the change is only a space) takes the caption of the
    # nearest explained change in the same paragraph: usually its other half.
    by_para = defaultdict(list)
    for r in range(n):
        by_para[part.rev_para[r]].append(r)
    for r in range(n):
        if caption[r] is None:
            near = [s for s in by_para[part.rev_para[r]] if how[s] == "по словам"]
            if near:
                s = min(near, key=lambda s: abs(s - r))
                caption[r], how[r] = caption[s], "по соседней правке"
            else:
                caption[r], how[r] = default, "не определён" if default[0] == UNKNOWN else "единственный раунд"
    records = []
    for r, rev in enumerate(part.revs):
        cap, date = caption[r]
        _set(rev, cap, date)
        records.append({"kind": part.rev_kind[r], "text": part.rev_text[r], "before": part.rev_before[r],
                        "style": part.rev_style[r], "caption": cap,
                        "date": date, "how": how[r], "para": part.rev_para[r],
                        "words": sum(votes[r].values()), "rounds": dict(votes[r])})
    # Everything else Word marked with an author (paragraph marks, formatting, table rows)
    # follows the text changes of its paragraph, or the nearest one before it.
    rev_index = {id(x): r for r, x in enumerate(part.revs)}      # part.revs keeps these proxies alive
    paras = list(part.root.iter(q(W, "p")))
    p_index = {id(p): i for i, p in enumerate(paras)}

    def para_of(el):
        while el is not None and el.tag != q(W, "p"):
            el = el.getparent()
        return p_index.get(id(el)) if el is not None else None

    first_in_para = {}
    for r in range(n):
        first_in_para.setdefault(part.rev_para[r], caption[r])
    last, extra = default, 0
    for el in part.root.iter():
        if id(el) in rev_index:
            last = caption[rev_index[id(el)]]
        elif isinstance(el.tag, str) and q(W, "author") in el.attrib:
            _set(el, *(first_in_para.get(para_of(el)) or last))
            extra += 1
    return etree.tostring(part.root, xml_declaration=True, encoding="UTF-8", standalone=True), records, extra


def _set(el, caption, date):
    el.set(q(W, "author"), caption)
    if date:
        el.set(q(W, "date"), date)
    elif q(W, "date") in el.attrib:
        del el.attrib[q(W, "date")]


def iso(date):
    """'05.11.2026' -> Word's date of a change (noon, so that no time zone moves the day)."""
    d, m, y = date.split(".")
    return "%s-%s-%sT12:00:00Z" % (y, m.zfill(2), d.zfill(2))


def label_docx(tracked, snapshots, rounds, out, default=None):
    """Write OUT: TRACKED with every change carrying the caption and date of its round.

    `snapshots`: the .docx of every version, first to last, made by one pipeline.
    `rounds[k]` for k >= 1: (caption, 'dd.mm.yyyy') of the step from snapshot k-1 to k.
    Returns the records of all text changes and the count of other marked elements."""
    rounds = [None] + [(c, iso(d)) for c, d in rounds[1:]]
    default = (default[0], iso(default[1])) if default else (UNKNOWN, None)
    zs = [zipfile.ZipFile(s) for s in snapshots]
    records, extra = [], 0
    with zipfile.ZipFile(tracked) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        names = set(zin.namelist())
        captions = set()
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in PARTS:
                snap = [z.read(item.filename) if item.filename in z.namelist() else None for z in zs]
                data, recs, ex = label_part(data, snap, rounds, default)
                for rec in recs:
                    rec["part"] = item.filename
                records += recs
                extra += ex
                captions |= {r["caption"] for r in recs}
            zout.writestr(item, data)
    for z in zs:
        z.close()
    if "word/people.xml" in names:
        _people(out, captions)
    return records, extra


def _people(path, captions):
    """Word lists the authors of changes in people.xml; list the captions instead of the
    placeholder the comparison was run with."""
    import shutil
    import tempfile
    tmp = tempfile.mktemp(suffix=".docx")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/people.xml":
                root = etree.fromstring(data)
                for p in list(root):
                    root.remove(p)
                for c in sorted(captions):
                    p = etree.SubElement(root, q(W15, "person"))
                    p.set(q(W15, "author"), c)
                    info = etree.SubElement(p, q(W15, "presenceInfo"))
                    info.set(q(W15, "providerId"), "None")
                    info.set(q(W15, "userId"), c)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            zout.writestr(item, data)
    shutil.move(tmp, path)


def same_glyphs(text):
    """Text with the letter forms Word chooses inside equations undone: after a comparison Word
    writes a mathematical italic or bold letter (U+1D400...) for a plain one and a hyphen for the
    minus sign, which changes no character a reader sees as different."""
    import unicodedata
    return unicodedata.normalize("NFKC", text).replace("−", "-")


def views_text(docx):
    """The text 'reject all' and 'accept all' leave, read from the XML (spaces collapsed)."""
    out = {"old": [], "new": []}
    with zipfile.ZipFile(docx) as z:
        for name in PARTS:
            if name in z.namelist():
                p = Part(z.read(name))
                for v in out:
                    out[v].append(p.views[v]["text"])
    return {v: re.sub(r"\s+", " ", " ".join(t)).strip() for v, t in out.items()}
