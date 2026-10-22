#!/usr/bin/env python
"""Paper map tool: binds a manuscript's claims to its LaTeX text, to the files and code they come
from, and to what rests on them.

  check         MAP.yaml [--out REPORT.txt]   integrity, coverage and findings; exit 0 when the map is clean
  argument      MAP.yaml [--lang ru] [--out]  the page for the author: main claims, verdicts, what breaks them
  impact        MAP.yaml ID [ID ...] [--out]  what a change of the given nodes touches, by action, with lines
  trace         MAP.yaml ID                   everything a node rests on, down to its source files
  place-anchors MAP.yaml                      write the anchored copy of the paper from the original
  strip         IN.tex OUT.tex                remove anchors, e.g. for a co-author's copy

The map format is described in MAP_FORMAT.md next to this file.
"""
import argparse
import datetime as dt
import hashlib
import math
import operator
import os
import re
import subprocess
import sys
from collections import defaultdict, deque

import yaml

# Anchors are LaTeX comments, so the compiled PDF does not change. The space before the
# percent sign keeps the line break acting as a space after the comment swallows it.
ANCHOR_TOKEN = re.compile(r'%@([A-Za-z0-9_.:\-]+)')
ANCHOR_WITH_SPACE = re.compile(r' %@[A-Za-z0-9_.:\-]+')
# Arguments of these commands hold years, labels and file names, not claims.
NON_CLAIM_ARG = re.compile(
    r'\\(?:cite[a-zA-Z]*|ref|eqref|autoref|label|includegraphics|url|href|input|bibliography)\*?'
    r'(?:\[[^\]]*\])*\s*\{[^}]*\}')
SECTION_START = re.compile(r'\s*\\(?:sub)*section\*?\s*\{')
# Definitions of counters, lengths and commands are not prose; an appendix often starts with them.
DEFINITION = re.compile(r'\s*\\(?:(?:re)?newcommand|providecommand|(?:re)?newenvironment|def|let|'
                        r'setcounter|addtocounter|setlength|addtolength)\b')
DEFAULT_EXCLUDED_SECTIONS = ['Acknowledgments', 'Acknowledgements', 'Author contributions',
                             'Competing interests', 'Ethics']
KINDS = {'dna', 'result', 'statement', 'method', 'param', 'assumption', 'intro', 'discussion', 'cite'}
BOUND_OPS = {'>': operator.gt, '>=': operator.ge, '<': operator.lt, '<=': operator.le}
CONDITION_OPS = set(BOUND_OPS) | {'=='}
STATEMENT_KINDS = {'dna', 'discussion', 'intro', 'statement'}
DESCRIPTION_KINDS = {'method', 'param', 'assumption'}
# The questions of the Introduction are reached by almost any change.
FRAMING_KINDS = {'intro'}
# A `uses` step carries the change itself; these steps only put a statement in question.
ARGUMENT_STEPS = {'supports', 'answers', 'relates to', 'is restated by'}
# How a claim of the paper stands to a cited work.
RELATION_TYPES = {'confirms', 'extends', 'contradicts', 'contrasts', 'uses', 'motivates'}

TIERS = [
    ('claims', 'MAIN CLAIMS AT STAKE: put them to the author; never reword one without agreement'),
    ('recompute', 'RECOMPUTE: a number or a figure panel computed from the change'),
    ('rewrite', 'REWRITE: the description of a method or parameter that uses the changed node directly'),
    ('re-read', 'RE-READ: a statement resting on a changed value, one step of the argument away'),
    ('further', 'FURTHER UP THE ARGUMENT: two or more steps away, or the framing of the paper'),
    ('downstream', 'DOWNSTREAM STEPS: methods and parameters fed by the change; their own text probably stands'),
    ('off-text', 'NOT IN THE TEXT: runs, intermediate results and code the change passes through'),
]
MAIN_TIERS = ('recompute', 'rewrite', 're-read')


def read_text(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def write_text(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def strip_anchors(text):
    return ANCHOR_WITH_SPACE.sub('', text)


def normalize_ws(s):
    return ' '.join(str(s).split())


def strip_comment(line):
    m = re.search(r'(?<!\\)%', line)
    return line[:m.start()] if m else line


def number_tokens(text):
    """Number tokens of LaTeX text.

    10{,}000, 10\\,000 and 10,000 read as 10000; 6.6\\times10^{-11} and 10^{-3} as one number each.
    Not numbers: the level of a confidence interval ("95% CI", "95\\%$ CI", "95\\%~CI"), sub- and
    superscripts (\\theta_1, R^2), names with digits (CA1, F28_1D, L3.1, S6.5, d_obj1..4, citation keys
    such as smith2020a) and digits glued to letters (2D); ordinals (85th) are numbers.
    """
    t = NON_CLAIM_ARG.sub(' ', str(text))
    t = re.sub(r'(?<=\d)(?:\{,\}|\\,|,)(?=\d{3}(?!\d))', '', t)
    t = re.sub(r'\d+(?:\.\d+)?\s*(?:\\,)?\s*\\?%(?:[\s$~]|\\,)*(?:CI|confidence)', ' ', t)
    # Powers of ten are set aside first, so that the clean-up below cannot split them.
    kept = []

    def keep(value):
        kept.append(value)
        return f' \x00{len(kept) - 1}\x00 '

    t = re.sub(r'(\d+(?:\.\d+)?)\s*(?:\\times|\\cdot)\s*10\^\{?\s*([-+]?\d+)\s*\}?',
               lambda m: keep(f'{m.group(1)}e{m.group(2)}'), t)
    t = re.sub(r'(?<![\d.])10\^\{?\s*([-+]?\d+)\s*\}?', lambda m: keep(f'1e{m.group(1)}'), t)
    t = re.sub(r'(?<![\w.])\d+(?:\.\d+)?[eE][-+]?\d+\b', lambda m: keep(m.group(0)), t)
    # Command names go first, or \approx0.5 would read as a name with digits.
    t = re.sub(r'\\[A-Za-z]+', ' ', t)
    t = re.sub(r'[_^]\{?[-+]?\d+\}?', ' ', t)
    t = re.sub(r'\b[A-Za-z]\w*\d[\w.]*|\b\d+(?!(?:st|nd|rd|th)\b)[A-Za-z]\w*', ' ', t)
    return [kept[int(m.group(1))] if m.group(1) is not None else m.group(0)
            for m in re.finditer(r'\x00(\d+)\x00|\d+(?:\.\d+)?', t)]


def first_token(value):
    toks = number_tokens(value) if value is not None else []
    return toks[0] if toks else None


def signed_first(value):
    """The first number of a value, with its sign: '-0.3 [-0.5, -0.1]' -> -0.3.

    number_tokens reads text, where a dash is usually a range ('29--39'), so it drops signs;
    a value or a bound written in the map starts with its own sign.
    """
    tok = first_token(value)
    if tok is None:
        return None
    x = float(tok)
    return -x if re.match(r'\s*\$?\s*[-−]\s*\d', str(value)) else x


def signed_numbers(value):
    """Each number of a list written in the map, with its sign: '-0.1, 0.2' -> [-0.1, 0.2]."""
    return [signed_first(p) for p in re.split(r';|,\s+', str(value)) if first_token(p) is not None]


def _tolerance(token):
    """Half a unit of the last stated digit: 34 -> 0.5, 0.25 -> 0.005, 6.6e-11 -> 5e-13."""
    mant, _, exp = token.lower().partition('e')
    decimals = len(mant.split('.')[1]) if '.' in mant else 0
    return 0.5 * 10 ** (int(exp or 0) - decimals)


def agrees(token, value_tokens):
    """Two numbers agree when the more precise one rounds to the less precise one."""
    s = float(token)
    for v in value_tokens:
        tol = max(_tolerance(token), _tolerance(v)) * (1 + 1e-9)
        if abs(s - float(v)) <= tol:
            return True
    return False


def condition_holds(m, n, hw):
    """(holds, x, y) for a condition on node n's value, or None when it cannot be evaluated.

    The condition compares the node's value with a number (`value`) or with another node's value
    (`node`, plus an optional `margin`). '==' means agreement at the stated precision, or within
    `tolerance` when one is given.
    """
    if not isinstance(hw, dict) or str(hw.get('op')) not in CONDITION_OPS:
        return None
    x_tok = first_token(n.get('value'))
    if 'node' in hw:
        other = m.by_id.get(str(hw['node']))
        y_val = other.get('value') if other else None
    else:
        y_val = hw.get('value')
    y_tok = first_token(y_val)
    if x_tok is None or y_tok is None:
        return None
    x, y = signed_first(n.get('value')), signed_first(y_val) + float(hw.get('margin', 0))
    op = str(hw['op'])
    if op == '==':
        tol = float(hw['tolerance']) if 'tolerance' in hw else max(_tolerance(x_tok), _tolerance(y_tok))
        return abs(x - y) <= tol * (1 + 1e-9), x, y
    return BOUND_OPS[op](x, y), x, y


def unevaluable_reason(m, n, hw):
    if not isinstance(hw, dict) or str(hw.get('op')) not in CONDITION_OPS:
        return f'op must be one of {sorted(CONDITION_OPS)}'
    if first_token(n.get('value')) is None:
        return 'this node has no numeric value'
    if 'node' in hw:
        if str(hw['node']) not in m.by_id:
            return f'unknown node {hw["node"]}'
        if first_token(m.by_id[str(hw['node'])].get('value')) is None:
            return f'node {hw["node"]} has no numeric value'
        return 'cannot read the values'
    return 'no number or node to compare with'


# "line 34", "lines 21-25", "строка 14": where in a source a value is set.
LINE_REF = re.compile(r'(?:\blines?|строк[аи]?)\s*(\d+)', re.IGNORECASE)


def source_where(s):
    if s.get('file'):
        return str(s['file'])
    if s.get('commit'):
        return f'{s.get("commit")}:{s.get("path")}'
    return f'unavailable: {normalize_ws(s.get("unavailable", ""))}'


def source_line(s):
    m = LINE_REF.search(str(s.get('locator', '')))
    if not m:
        return None
    return os.path.normcase(source_where(s).replace('\\', '/')), m.group(1)


_sha_cache = {}


def sha256_file(path):
    if path not in _sha_cache:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        _sha_cache[path] = h.hexdigest()
    return _sha_cache[path]


_git_cache = {}


def git_object_exists(repo, commit, path):
    key = (repo, commit, path)
    if key not in _git_cache:
        try:
            r = subprocess.run(['git', '-C', repo, 'cat-file', '-e', f'{commit}:{path}'],
                               capture_output=True, timeout=60)
            _git_cache[key] = (r.returncode == 0)
        except (OSError, subprocess.TimeoutExpired):
            _git_cache[key] = None
    return _git_cache[key]


def load_yaml(path):
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


class Map:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.dir = os.path.dirname(self.path)
        raw = load_yaml(self.path)
        if not isinstance(raw, dict) or 'nodes' not in raw:
            sys.exit('[FAILED] the map must be a mapping with keys paper, scopes, nodes '
                     '(see MAP_FORMAT.md)')
        self.paper = raw.get('paper') or {}
        self.scopes = {str(k): v for k, v in (raw.get('scopes') or {}).items()}
        self.skips = list(raw.get('skip') or [])
        self.nodes = list(raw.get('nodes') or [])
        self.load_errors = []
        # Parts let helpers write the map in parallel, one file each; paths in a part are
        # resolved against the main map's folder, like everything else.
        for p in raw.get('parts') or []:
            part_path = self.resolve(p)
            if not os.path.exists(part_path):
                self.load_errors.append(f'part not found: {part_path}')
                continue
            part = load_yaml(part_path) or {}
            for k, v in (part.get('scopes') or {}).items():
                if str(k) in self.scopes and str(self.scopes[str(k)]) != str(v):
                    self.load_errors.append(f'scope {k} is defined differently in {p}')
                self.scopes[str(k)] = v
            self.skips += part.get('skip') or []
            self.nodes += part.get('nodes') or []
        self.by_id = {}
        self.dupes = []
        for n in self.nodes:
            nid = str(n.get('id'))
            if nid in self.by_id:
                self.dupes.append(nid)
            self.by_id[nid] = n

    def resolve(self, p):
        if p is None:
            return None
        p = str(p)
        return p if os.path.isabs(p) else os.path.normpath(os.path.join(self.dir, p))

    def paper_date(self):
        d = self.paper.get('date')
        if d is None:
            return None
        return d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d))

    def require_loaded(self):
        if self.load_errors:
            sys.exit('[FAILED] ' + '; '.join(self.load_errors))


def uses_of(n):
    return [str(u) for u in (n.get('uses') or [])]


def supports_of(n):
    return [s for s in (n.get('supports') or []) if isinstance(s, dict)]


def checks_of(n):
    return [c for c in (n.get('checks') or []) if isinstance(c, dict)]


def answered_by_of(n):
    return [str(a) for a in (n.get('answered_by') or [])]


def relates_of(n):
    return [r for r in (n.get('relates') or []) if isinstance(r, dict)]


def distinct_of(n):
    return [str(x) for x in (n.get('distinct_from') or [])]


def mentions_of(n):
    return [mt for mt in (n.get('mentions') or []) if isinstance(mt, dict)]


def sources_of(n):
    src = n.get('sources')
    if src is None and isinstance(n.get('source'), dict):
        src = [n['source']]
    return [s for s in (src or []) if isinstance(s, dict)]


def has_text(n):
    return any(mt.get('anchor') or mt.get('figure') for mt in mentions_of(n))


def build_graph(m):
    """down[x]: nodes that depend on x; up[x]: nodes x rests on. `checks` are not dependencies."""
    down, up = defaultdict(list), defaultdict(list)
    for nid, n in m.by_id.items():
        for u in uses_of(n):
            down[u].append((nid, 'is used by', None))
            up[nid].append((u, 'uses', None))
        for s in supports_of(n):
            to = str(s.get('to'))
            down[nid].append((to, 'supports', s))
            up[to].append((nid, 'rests on', s))
        for a in answered_by_of(n):
            down[a].append((nid, 'answers', None))
            up[nid].append((a, 'is answered by', None))
        for r in relates_of(n):
            down[nid].append((str(r.get('cite')), 'relates to', r))
            up[str(r.get('cite'))].append((nid, 'is related by', r))
        if n.get('restates') is not None:
            dna = str(n['restates'])
            down[dna].append((nid, 'is restated by', None))
            up[nid].append((dna, 'restates', None))
    return down, up


def serving_no_claim(m, down):
    """Results and statements from which no chain of the argument reaches a main claim."""
    dnas = {nid for nid, n in m.by_id.items() if n.get('kind') == 'dna'}
    orphans = []
    for nid, n in m.by_id.items():
        if n.get('kind') not in ('result', 'statement'):
            continue
        if not dnas & descendants({nid}, down):
            orphans.append(nid)
    return orphans


def supports_chain(start, down):
    """What a node argues for: the nodes its supports reach, directly or through others."""
    seen, q = set(), deque([start])
    while q:
        cur = q.popleft()
        for dep, label, _ in down.get(cur, []):
            if label == 'supports' and dep not in seen:
                seen.add(dep)
                q.append(dep)
    return seen


def claims_of_discussion(m, nid, down, up):
    """Main claims a Discussion position returns to: it argues for one, directly or through a component,
    or it rests on a main claim or on something that argues for one."""
    dnas = {x for x, n in m.by_id.items() if n.get('kind') == 'dna'}
    tied = dnas & supports_chain(nid, down)
    for x, label, _ in up.get(nid, []):
        if label in ('rests on', 'restates'):
            tied |= dnas & ({x} | supports_chain(x, down))
    return tied


def loose_discussion(m, down, up):
    """Discussion positions tied to neither a main claim nor the literature."""
    return [nid for nid, n in m.by_id.items() if n.get('kind') == 'discussion' and not n.get('restates')
            and not claims_of_discussion(m, nid, down, up) and not relates_of(n)]


class Tex:
    def __init__(self, path):
        self.path = path
        self.lines = read_text(path).splitlines()
        self.anchor_lines = defaultdict(list)
        for i, line in enumerate(self.lines, 1):
            for a in ANCHOR_TOKEN.findall(line):
                self.anchor_lines[a].append(i)

    def window(self, line_no, above=3):
        """Text of the anchored line and the lines above it: a sentence often ends where its anchor sits."""
        lo = max(1, line_no - above)
        return normalize_ws(strip_anchors(' '.join(self.lines[lo - 1:line_no])))

    def line_of(self, anchor):
        found = self.anchor_lines.get(str(anchor))
        return found[0] if found else None

    def span(self, anchor, quote):
        """First and last line of a mention: its anchor sits on the line where the quote ends."""
        end = self.line_of(anchor)
        if end is None:
            return None
        q = normalize_ws(quote or '')
        for above in range(4):
            if q and q in self.window(end, above):
                return end - above, end
        return end, end


def fmt_span(span):
    lo, hi = span
    return f'line {hi}' if lo == hi else f'lines {lo}-{hi}'


def fmt_lines(lines):
    """12, 30-31, 45: consecutive line numbers as ranges."""
    out, run = [], []
    for x in sorted(lines):
        if run and x == run[-1] + 1:
            run.append(x)
            continue
        if run:
            out.append(str(run[0]) if len(run) == 1 else f'{run[0]}-{run[-1]}')
        run = [x]
    if run:
        out.append(str(run[0]) if len(run) == 1 else f'{run[0]}-{run[-1]}')
    return ', '.join(out)


def prose_letters(lines):
    s = ' '.join(strip_comment(l) for l in lines)
    s = NON_CLAIM_ARG.sub(' ', s)
    s = re.sub(r'\\[A-Za-z]+\*?', ' ', s)
    return len(re.findall(r'[A-Za-z]', s))


def section_title(line):
    """Title of the section or subsection a line starts, or None; braces inside the title are kept."""
    m = SECTION_START.match(line)
    if not m:
        return None
    depth, i = 1, m.end()
    while i < len(line):
        if line[i] == '\\':
            i += 2
            continue
        if line[i] == '{':
            depth += 1
        elif line[i] == '}':
            depth -= 1
            if depth == 0:
                return line[m.end():i].strip()
        i += 1
    return line[m.end():].strip()


def paragraphs(tex, excluded_sections):
    """Prose blocks of the body between blank lines: (section, [(line_no, text), ...]).

    The body runs to the end of the document: an appendix often follows the list of references,
    which is not prose and is passed over.
    """
    lines = tex.lines
    start = next((i for i, l in enumerate(lines) if '\\begin{document}' in l), -1)
    end = next((i for i, l in enumerate(lines) if '\\end{document}' in l), len(lines))
    section, excluded, block, blocks, in_refs = 'front matter', False, [], [], False
    for i in range(start + 1, end):
        line = lines[i]
        if '\\begin{thebibliography}' in line:
            in_refs = True
            if block:
                blocks.append((section, block))
            block = []
        if in_refs:
            in_refs = '\\end{thebibliography}' not in line
            continue
        if line.strip().startswith('\\bibliography') or DEFINITION.match(line):
            continue
        title = section_title(line)
        if title is not None:
            if block:
                blocks.append((section, block))
            block = []
            section = title
            excluded = section in excluded_sections
            continue
        if excluded:
            continue
        if not line.strip() or (line.lstrip().startswith('%') and not ANCHOR_TOKEN.search(line)):
            if not line.strip() and block:
                blocks.append((section, block))
                block = []
            continue
        block.append((i + 1, line))
    if block:
        blocks.append((section, block))
    return [(sec, blk) for sec, blk in blocks if prose_letters([l for _, l in blk]) >= 40]


class Report:
    def __init__(self):
        self.errors, self.findings, self.warnings, self.info = [], [], [], []
        self.uncovered, self.unanchored = [], []

    def err(self, msg):
        self.errors.append(msg)

    def find(self, label, msg):
        self.findings.append(f'[{label}] {msg}')

    def warn(self, msg):
        self.warnings.append(msg)


def mention_where(mt, tex):
    if mt.get('figure'):
        return f'figure {mt.get("figure")} {mt.get("panel", "")}'.strip()
    ln = tex.line_of(mt.get('anchor'))
    return f'line {ln}' if ln else f'anchor {mt.get("anchor")}'


def value_findings(m, tex):
    """What the map finds without opening a source: the text against each node's value and scope, the
    values and words recorded for its sources against the node, results with no source to check.

    Each finding is (label, node id, message, page key, page fields): the check report prints the
    message; the argument page shows the findings under the main claims they support.
    """
    out = []
    for nid, n in m.by_id.items():
        value = n.get('value')
        value_toks = number_tokens(value) if value is not None else []
        for mt in mentions_of(n):
            where = mention_where(mt, tex)
            states = mt.get('states')
            if states is not None:
                stated = number_tokens(states)
            else:
                stated = number_tokens(mt.get('quote', '')) if value is not None else []
            bound = mt.get('bound')
            if value_toks and stated and str(bound) in BOUND_OPS:
                # "p < 0.001": the text states a bound on the value, not the value itself. The value and
                # the bounds written in states are the map's own, so their signs count.
                x = signed_first(value)
                limits = signed_numbers(states) if states is not None else [float(t) for t in stated]
                bad = [f'{b:g}' for b in limits if not BOUND_OPS[str(bound)](x, b)]
                if bad:
                    said = f'{bound} {", ".join(bad)}'
                    out.append(('MISMATCH', nid, f'{nid} ({where}): the text says value {said}; '
                                                 f'the node value is {value}',
                                'f_mismatch', {'said': said, 'value': value}))
            elif value_toks and stated and bound is None:
                bad = [t for t in stated if not agrees(t, value_toks)]
                if bad:
                    out.append(('MISMATCH', nid, f'{nid} ({where}): the text says {", ".join(bad)}; '
                                                 f'the node value is {value}',
                                'f_mismatch', {'said': ', '.join(bad), 'value': value}))
            if mt.get('scope') is not None and n.get('scope') is not None \
                    and str(mt['scope']) != str(n['scope']):
                said, on = m.scopes.get(str(mt['scope'])), m.scopes.get(str(n['scope']))
                out.append(('SCOPE', nid, f'{nid} ({where}): the text implies "{said}"; computed on "{on}"',
                            'f_scope', {'said': said, 'value': on}))
        srcs = sources_of(n)
        if n.get('kind') == 'result' and all(s.get('unavailable') for s in srcs):
            why = '; '.join(normalize_ws(s['unavailable']) for s in srcs)
            if why:
                out.append(('UNSOURCED', nid, f'{nid}: result without a source that can be checked '
                                              f'(unavailable: {why})', 'f_unavailable', {'said': why}))
            else:
                out.append(('UNSOURCED', nid, f'{nid}: result without a source', 'f_unsourced', {}))
        for s in srcs:
            where = source_where(s)
            name = where if s.get('unavailable') else where.replace('\\', '/').rsplit('/', 1)[-1]
            if s.get('value') is not None and value_toks:
                bad = [t for t in number_tokens(s['value']) if not agrees(t, value_toks)]
                if bad:
                    # Every number of a source's value is compared, so a real disagreement is never
                    # passed over. A number that differs only after a word or a bracket ('0.128 (SE 0.053)')
                    # is most likely an explanation written into the value.
                    head = number_tokens(re.split(r'\(|[A-Za-z]{2,}', str(s['value']), maxsplit=1)[0])
                    hint = ('; if the value carries an explanation, move it to the locator'
                            if not any(t in head for t in bad) else '')
                    out.append(('CONFLICT', nid, f'{nid}: source {where} gives {s["value"]}; '
                                                 f'the node value is {value}{hint}',
                                'f_conflict', {'where': name, 'said': s['value'], 'value': value}))
            if s.get('disagrees'):
                said = normalize_ws(s['disagrees'])
                out.append(('CONFLICT', nid, f'{nid}: source {where} disagrees: {said}',
                            'f_disagrees', {'where': name, 'said': said}))
    return out


def check(m, out_path=None):
    rep = Report()
    paper_file = m.resolve(m.paper.get('file'))
    if not paper_file or not os.path.exists(paper_file):
        sys.exit(f'[FAILED] paper.file not found: {paper_file}')
    tex = Tex(paper_file)
    paper_date = m.paper_date()
    rep.info.append(f'paper: {paper_file}')
    rep.info.append(f'paper sha256 now: {sha256_file(paper_file)}')
    for e in m.load_errors:
        rep.err(e)

    original = m.resolve(m.paper.get('original'))
    if original:
        if not os.path.exists(original):
            rep.err(f'paper.original not found: {original}')
        elif strip_anchors(read_text(paper_file)) != read_text(original):
            rep.err('the anchored copy differs from paper.original beyond anchors '
                    '(rerun place-anchors, or drop paper.original once the copy is the working text)')

    for d in m.dupes:
        rep.err(f'duplicate node id {d}')
    for sid in m.scopes:
        if not str(m.scopes[sid]).strip():
            rep.err(f'scope {sid} has no description')

    for nid, n in m.by_id.items():
        kind = n.get('kind')
        if kind not in KINDS:
            rep.err(f'{nid}: unknown kind {kind!r}')
        for u in uses_of(n):
            if u not in m.by_id:
                rep.err(f'{nid}: uses unknown node {u}')
        for s in supports_of(n):
            to = str(s.get('to'))
            if to not in m.by_id:
                rep.err(f'{nid}: supports unknown node {s.get("to")}')
            elif m.by_id[to].get('kind') in ('param', 'method'):
                # A parameter does not rest on a result; two values that must agree are a check.
                rep.warn(f'{nid} supports {to} ({m.by_id[to].get("kind")}): if this is a condition that two '
                         f'values agree, write it under checks - impact follows supports')
        for c in checks_of(n):
            hw = c.get('holds_while')
            if not isinstance(hw, dict):
                rep.err(f'{nid}: check without holds_while: {c}')
            elif 'node' in hw and str(hw['node']) not in m.by_id:
                rep.err(f'{nid}: check against unknown node {hw["node"]}')
        for a in answered_by_of(n):
            if a not in m.by_id:
                rep.err(f'{nid}: answered_by unknown node {a}')
        for r in relates_of(n):
            cite = m.by_id.get(str(r.get('cite')))
            if cite is None or cite.get('kind') != 'cite':
                rep.err(f'{nid}: relates to {r.get("cite")}, which is not a cite node')
            if str(r.get('how')) not in RELATION_TYPES:
                rep.err(f'{nid}: relation to {r.get("cite")} must be one of {sorted(RELATION_TYPES)}, not {r.get("how")!r}')
        if n.get('restates') is not None:
            target = m.by_id.get(str(n['restates']))
            if target is None or target.get('kind') != 'dna':
                rep.err(f'{nid}: restates {n["restates"]}, which is not a main claim')
        for x in n.get('same_measure_as') or []:
            if str(x) not in m.by_id:
                rep.err(f'{nid}: same_measure_as unknown node {x}')
        for x in distinct_of(n):
            if x not in m.by_id:
                rep.err(f'{nid}: distinct_from unknown node {x}')
        if n.get('scope') is not None and str(n['scope']) not in m.scopes:
            rep.err(f'{nid}: unknown scope {n["scope"]}')
        if kind == 'param' and not sources_of(n):
            rep.warn(f'{nid}: parameter without a source - record every place in the code that sets it')

    # Mentions: bound to the text, the numbers they state, the scope they claim.
    map_anchors = {}
    for nid, n in m.by_id.items():
        value = n.get('value')
        for mt in mentions_of(n):
            where = None
            quote = normalize_ws(mt.get('quote', ''))
            if mt.get('figure'):
                where = f'figure {mt.get("figure")} {mt.get("panel", "")}'.strip()
            else:
                a = mt.get('anchor')
                if not a:
                    rep.err(f'{nid}: mention without anchor')
                    continue
                a = str(a)
                if a == 'skip':
                    rep.err(f'{nid}: anchor name "skip" is reserved')
                    continue
                if a in map_anchors:
                    rep.err(f'anchor {a} is used by two mentions ({map_anchors[a]} and {nid})')
                map_anchors[a] = nid
                found = tex.anchor_lines.get(a, [])
                if not found:
                    rep.err(f'{nid}: anchor {a} not found in the text (run place-anchors?)')
                    continue
                if len(found) > 1:
                    rep.err(f'anchor {a} occurs {len(found)} times in the text (lines {found})')
                ln = found[0]
                where = f'line {ln}'
                if not quote:
                    rep.err(f'{nid} {a} ({where}): mention without quote')
                elif quote not in tex.window(ln):
                    rep.err(f'{nid} {a} ({where}): quote not found at the anchor - '
                            f'the text changed or the quote is wrong: "{quote[:70]}"')
            if mt.get('scope') is not None and str(mt['scope']) not in m.scopes:
                rep.err(f'{nid} ({where}): unknown scope {mt["scope"]}')

            states = mt.get('states')
            # A number written in words ("twenty-eight") cannot be found among the quote's digits. A number
            # the reading sets aside (the level of an interval) may still be stated on purpose.
            if states is not None and quote and not mt.get('verbal'):
                quote_nums = [float(t) for t in number_tokens(quote) + re.findall(r'\d+(?:\.\d+)?', quote)]
                missing = [t for t in number_tokens(states)
                           if not any(abs(float(t) - q) < 1e-9 for q in quote_nums)]
                if missing:
                    rep.err(f'{nid} ({where}): states {missing} not found in the quote')
            bound = mt.get('bound')
            if bound is not None and str(bound) not in BOUND_OPS:
                rep.err(f'{nid} ({where}): bound must be one of {sorted(BOUND_OPS)}, not {bound!r}')
            if n.get('kind') == 'result' and value is not None and mt.get('scope') is None \
                    and not mt.get('figure'):
                rep.warn(f'{nid} ({where}): mention does not record which scope the text states')

    for a, found in tex.anchor_lines.items():
        if a != 'skip' and a not in map_anchors:
            rep.err(f'anchor {a} in the text (line {found[0]}) has no mention in the map')

    # Sources: present, pinned, unchanged; dated against the paper version. Their values and words are
    # compared with the node below, with the text.
    stale = set()
    for nid, n in m.by_id.items():
        for s in sources_of(n):
            if s.get('unavailable'):
                continue  # the place is known but cannot be opened: nothing to pin or date
            if s.get('commit'):
                repo = m.resolve(s.get('git') or m.paper.get('code_repo'))
                ok = git_object_exists(repo, str(s['commit']), str(s.get('path', ''))) if repo else None
                if ok is False:
                    rep.err(f'{nid}: {s.get("commit")}:{s.get("path")} not found in {repo}')
                elif ok is None:
                    rep.warn(f'{nid}: could not ask git about {s.get("commit")}:{s.get("path")}')
            else:
                f = m.resolve(s.get('file'))
                if not f:
                    rep.err(f'{nid}: source without file or commit (or `unavailable` with the reason)')
                    continue
                if not os.path.exists(f):
                    rep.err(f'{nid}: source file missing: {f}')
                    continue
                rec = s.get('sha256')
                if not rec:
                    rep.err(f'{nid}: source not pinned (no sha256): {f}')
                elif sha256_file(f) != str(rec).strip().lower():
                    rep.find('STALE', f'{nid}: source changed since it was mapped: {f}')
                    stale.add(nid)
                if paper_date:
                    mdate = dt.date.fromtimestamp(os.path.getmtime(f))
                    if mdate > paper_date:
                        rep.find('AFTER-VERSION', f'{nid}: source modified {mdate}, after the paper '
                                                  f'version of {paper_date}: {f}')
    for label, _, msg, _, _ in value_findings(m, tex):
        rep.find(label, msg)

    # Conditions: under which a support holds, and which values must agree.
    for nid, n in m.by_id.items():
        for s in supports_of(n):
            conditions = s.get('holds_while')
            if not conditions:
                continue
            # One condition, or a list of them that must all hold ("a third" is a band, not a bound).
            for hw in (conditions if isinstance(conditions, list) else [conditions]):
                res = condition_holds(m, n, hw)
                if res is None:
                    rep.err(f'{nid} -> {s.get("to")}: holds_while cannot be evaluated '
                            f'({unevaluable_reason(m, n, hw)}): {hw}')
                elif not res[0]:
                    rep.find('BROKEN', f'{nid} -> {s.get("to")}: "{normalize_ws(s.get("says", ""))}" holds while '
                                       f'{res[1]:g} {hw.get("op")} {res[2]:g}; it does not')
        for c in checks_of(n):
            hw = c.get('holds_while')
            res = condition_holds(m, n, hw) if isinstance(hw, dict) else None
            if res is None:
                if isinstance(hw, dict):
                    rep.err(f'{nid}: check cannot be evaluated ({unevaluable_reason(m, n, hw)}): {hw}')
            elif not res[0]:
                rep.find('INCONSISTENT', f'{nid}: "{normalize_ws(c.get("says", ""))}" requires '
                                         f'{res[1]:g} {hw.get("op")} {res[2]:g}; it does not')

    if stale:
        down, _ = build_graph(m)
        affected = descendants(stale, down)
        if affected:
            rep.find('RE-CHECK', 'downstream of changed sources: ' + ', '.join(sorted(affected)))

    # One parameter, one node: two parameter nodes with the same value set on the same line of a
    # source are usually one parameter written down twice, by two helpers, and a change reaches
    # only one of them. Different values on one line are different parameters (a, b = 100, 5000);
    # equal values on one line (folds=5, shuffles=5) are told apart by distinct_from.
    set_on = defaultdict(list)
    for nid, n in m.by_id.items():
        if n.get('kind') != 'param':
            continue
        for s in sources_of(n):
            line = source_line(s)
            value = first_token(s.get('value') if s.get('value') is not None else n.get('value'))
            if line and value is not None and nid not in set_on[line + (float(value),)]:
                set_on[line + (float(value),)].append(nid)
    for (where, line, value), ids in set_on.items():
        same = sorted({a for a in ids for b in ids if a != b and b not in distinct_of(m.by_id[a])
                       and a not in distinct_of(m.by_id[b])})
        if len(same) > 1:
            rep.warn(f'parameters {" and ".join(same)} are set on the same line of a source ({where}, line {line}) '
                     f'to the same value {value:g}: if they are one parameter, keep one node; if each takes this '
                     f'default, make the default a node they use; if they are different parameters, say so in '
                     f'distinct_from (never drop a true source)')

    # A restatement of a main claim that adds something (a wider scope, a stronger word) needs
    # evidence of its own for the addition; resting on the main claim alone, it oversells.
    down, up = build_graph(m)
    for nid, n in m.by_id.items():
        if n.get('restates') is not None and n.get('adds'):
            own = [p for p, label, _ in up.get(nid, []) if label in ('rests on', 'uses')]
            if not own:
                rep.find('OVERSTATED', f'{nid}: restates {n["restates"]} and adds "{normalize_ws(n["adds"])}" '
                                       f'with no support of its own')

    # The argument: which main claims the author has confirmed, and what serves none of them.
    dnas = [nid for nid, n in m.by_id.items() if n.get('kind') == 'dna']
    unconfirmed = [d for d in dnas if not m.by_id[d].get('confirmed')]
    orphans = serving_no_claim(m, down)
    loose_disc = loose_discussion(m, down, up)
    unanswered =[nid for nid, n in m.by_id.items()
                  if n.get('kind') == 'intro' and n.get('question') and not answered_by_of(n)]
    argument = [f'main claims: {len(dnas)}; main claims not confirmed by the author: {len(unconfirmed)}'
                + (f' ({", ".join(unconfirmed)})' if unconfirmed else ''),
                f'results and statements serving no main claim: {len(orphans)}'
                + (f' ({", ".join(orphans[:40])}{" ..." if len(orphans) > 40 else ""})' if orphans else ''),
                f'Discussion positions tied to neither a main claim nor the literature: {len(loose_disc)}'
                + (f' ({", ".join(loose_disc)})' if loose_disc else ''),
                f'questions of the Introduction without an answer: {len(unanswered)}'
                + (f' ({", ".join(unanswered)})' if unanswered else '')]

    # Things that rest on nothing, and results nobody uses.
    for nid, n in m.by_id.items():
        kind = n.get('kind')
        if kind in ('dna', 'discussion') and not up.get(nid):
            rep.warn(f'{nid} ({kind}): rests on nothing in the map')
        if kind == 'intro' and n.get('question') and not answered_by_of(n):
            rep.warn(f'{nid}: question of the Introduction without answered_by')
        if kind == 'result' and not down.get(nid) and not mentions_of(n):
            rep.warn(f'{nid}: result with no mention and nothing depending on it')

    for nid, n in m.by_id.items():
        dec = n.get('decision')
        if dec:
            rep.info.append(f'decision on {nid} ({dec.get("date", "?")}): {normalize_ws(dec.get("what", ""))}')

    # Coverage: every prose paragraph carries an anchor or an explicit skip, and every number in it
    # lies inside the quote of a mention anchored there. A paragraph is often a single line, so an
    # anchor near a number says nothing about the number.
    quote_of = {str(mt['anchor']): normalize_ws(mt.get('quote', '')) for n in m.by_id.values()
                for mt in mentions_of(n) if mt.get('anchor') and not mt.get('figure')}
    excluded = m.paper.get('coverage_exclude') or DEFAULT_EXCLUDED_SECTIONS
    paras = paragraphs(tex, excluded)
    by_section_total, by_section_numbers = defaultdict(int), defaultdict(int)
    for sec, blk in paras:
        by_section_total[sec] += 1
        anchors = [a for _, l in blk for a in ANCHOR_TOKEN.findall(l)]
        if not anchors:
            rep.uncovered.append(f'{sec}, lines {blk[0][0]}-{blk[-1][0]}: '
                                 f'{normalize_ws(strip_comment(blk[0][1]))[:80]}')
        if 'skip' in anchors:
            continue
        text = normalize_ws(' '.join(strip_comment(l) for _, l in blk))
        # Quotes may overlap, so each is looked for in the text as it is, and only then masked.
        covered = [False] * len(text)
        for a in anchors:
            for mo in re.finditer(re.escape(quote_of.get(a) or '\x00'), text):
                covered[mo.start():mo.end()] = [True] * (mo.end() - mo.start())
        outside = number_tokens(''.join('\x01' if c else ch for ch, c in zip(text, covered)))
        if outside:
            by_section_numbers[sec] += len(outside)
            rep.unanchored.append(f'{sec}, {fmt_span((blk[0][0], blk[-1][0]))}: {", ".join(outside)} | '
                                  f'{normalize_ws(strip_comment(blk[0][1]))[:80]}')

    kinds = defaultdict(int)
    for n in m.by_id.values():
        kinds[n.get('kind')] += 1
    n_mentions = sum(len(mentions_of(n)) for n in m.by_id.values())
    n_checks = sum(len(checks_of(n)) for n in m.by_id.values())
    rep.info.append('nodes: ' + ', '.join(f'{k} {v}' for k, v in sorted(kinds.items(), key=lambda kv: str(kv[0]))))
    rep.info.append(f'mentions: {n_mentions}; anchors in the text: '
                    f'{sum(len(v) for a, v in tex.anchor_lines.items() if a != "skip")}; '
                    f'prose paragraphs: {len(paras)}; checks: {n_checks}')

    lines = ['PAPER MAP CHECK  ' + m.path]
    lines += ['  ' + x for x in rep.info]
    lines.append(f'\n== INTEGRITY ERRORS: {len(rep.errors)} (the map must be fixed) ==')
    lines += ['  ' + x for x in rep.errors]
    lines.append(f'\n== PARAGRAPHS WITHOUT ANCHOR: {len(rep.uncovered)} ==')
    lines += ['  ' + x for x in rep.uncovered]
    lines.append('\n== ARGUMENT (put to the author; the map stays clean without it) ==')
    lines += ['  ' + x for x in argument]
    lines.append(f'\n== FINDINGS FOR THE AUTHOR: {len(rep.findings)} ==')
    lines += ['  ' + x for x in sorted(rep.findings)]
    lines.append(f'\n== NUMBERS OUTSIDE EVERY QUOTE: {sum(by_section_numbers.values())}, '
                 f'in {len(rep.unanchored)} paragraphs ==')
    for sec in by_section_total:
        if by_section_numbers.get(sec):
            lines.append(f'  {sec}: {by_section_numbers[sec]}')
    lines += ['  ' + x for x in rep.unanchored[:200]]
    if len(rep.unanchored) > 200:
        lines.append(f'  ... {len(rep.unanchored) - 200} more')
    lines.append(f'\n== WARNINGS: {len(rep.warnings)} ==')
    lines += ['  ' + x for x in rep.warnings]
    clean = not rep.errors and not rep.uncovered
    lines.append('\nRESULT: ' + ('[OK] CLEAN' if clean else
                                 f'[FAILED] NOT CLEAN ({len(rep.errors)} integrity errors, '
                                 f'{len(rep.uncovered)} paragraphs without anchor)'))
    text = '\n'.join(lines) + '\n'
    print(text)
    if out_path:
        write_text(out_path, text)
    return 0 if clean else 1


def descendants(start, down):
    seen, q = set(), deque(start)
    while q:
        cur = q.popleft()
        for dep, _, _ in down.get(cur, []):
            if dep not in seen and dep not in start:
                seen.add(dep)
                q.append(dep)
    return seen


def reach(m, ids):
    """Every node downstream of the changed ones, with the fewest argument steps on the way.

    A `uses` step carries the change itself: the value is recomputed from it. A `supports` or
    `answers` step only puts a statement in question. Counting the latter separates what must be
    redone from what must be re-read.
    """
    down, _ = build_graph(m)
    steps = {i: 0 for i in ids}
    parent = {i: None for i in ids}
    dq = deque((i, 0) for i in ids)
    while dq:
        cur, s = dq.popleft()
        if s > steps[cur]:
            continue
        for dep, label, edge in down.get(cur, []):
            w = 1 if label in ARGUMENT_STEPS else 0
            if s + w < steps.get(dep, math.inf):
                steps[dep] = s + w
                parent[dep] = (cur, label, edge)
                if w:
                    dq.append((dep, s + w))
                else:
                    dq.appendleft((dep, s + w))
    direct = {dep for i in ids for dep, label, _ in down.get(i, []) if label == 'is used by'}
    return steps, parent, direct


def tier_of(nid, n, steps, direct):
    kind = n.get('kind')
    if kind == 'dna':
        return 'claims'
    if not has_text(n):
        return 'off-text'
    if kind == 'result' and steps == 0:
        return 'recompute'
    if kind in DESCRIPTION_KINDS and nid in direct:
        return 'rewrite'
    if kind in DESCRIPTION_KINDS and steps == 0:
        return 'downstream'
    if kind in FRAMING_KINDS:
        return 're-read' if steps == 0 else 'further'
    return 're-read' if steps <= 1 else 'further'


def impact_tiers(m, ids):
    """Node ids downstream of the changed ones, by what has to be done with them, in reach order."""
    steps, _, direct = reach(m, ids)
    tiers = {name: [] for name, _ in TIERS}
    for nid in steps:
        if nid not in ids:
            tiers[tier_of(nid, m.by_id[nid], steps[nid], direct)].append(nid)
    return tiers


def describe_mentions(n, tex, indent='      '):
    out = []
    for mt in mentions_of(n):
        if mt.get('figure'):
            what = mt.get('shows') or mt.get('states') or mt.get('quote') or ''
            out.append(f'{indent}figure {mt.get("figure")} {mt.get("panel", "")}: {normalize_ws(what)}'.rstrip())
            continue
        span = tex.span(mt.get('anchor'), mt.get('quote'))
        loc = fmt_span(span) if span else f'anchor {mt.get("anchor")} MISSING'
        out.append(f'{indent}{loc}: {normalize_ws(mt.get("quote", ""))[:110]}')
    return out


def text_lines(n, tex):
    lines = set()
    for mt in mentions_of(n):
        if mt.get('anchor') and not mt.get('figure'):
            span = tex.span(mt.get('anchor'), mt.get('quote'))
            if span:
                lines.update(range(span[0], span[1] + 1))
    return lines


def describe_sources(n, indent='      '):
    out = []
    for s in sources_of(n):
        where = source_where(s)
        extra = '; '.join(x for x in (normalize_ws(s.get('locator', '')),
                                      f'value {s["value"]}' if s.get('value') is not None else '') if x)
        out.append(f'{indent}{where}' + (f' ({extra})' if extra else ''))
    return out


def action_for(n):
    kind = n.get('kind')
    if kind in STATEMENT_KINDS:
        return 're-read the statement'
    if kind == 'result':
        if n.get('value') is None:
            return 're-check the statement'
        return 'recompute' if sources_of(n) else 're-check'
    if kind in DESCRIPTION_KINDS:
        return 'update the description'
    return 're-check'


def support_state(m, nid, edge):
    """'holds', 'BROKEN' or 'no condition' for a supports edge from node nid, as the values stand now."""
    hw = (edge or {}).get('holds_while')
    conds = hw if isinstance(hw, list) else [hw] if hw else []
    if not conds:
        return 'no condition'
    results = [condition_holds(m, m.by_id[nid], c) for c in conds]
    if any(r is not None and not r[0] for r in results):
        return 'BROKEN'
    return 'cannot evaluate' if any(r is None for r in results) else 'holds'


def chain_to(nid, parent):
    chain, cur = [], nid
    while parent[cur] is not None:
        prev, label, edge = parent[cur]
        step = f'{prev} {label} {cur}'
        if edge and edge.get('holds_while'):
            step += f' (holds while {edge["holds_while"]})'
        chain.append(step)
        cur = prev
    return ' <- '.join(chain)


def impact(m, ids, out_path=None):
    m.require_loaded()
    for i in ids:
        if i not in m.by_id:
            sys.exit(f'[FAILED] unknown node {i}')
    tex = Tex(m.resolve(m.paper.get('file')))
    steps, parent, direct = reach(m, ids)
    tiers = impact_tiers(m, ids)
    out = ['IMPACT of ' + ', '.join(ids)]
    main_lines, other_lines = set(), set()

    out.append('\n== CHANGED ==')
    for i in ids:
        n = m.by_id[i]
        out.append(f'* {i} ({n.get("kind")}): {normalize_ws(n.get("claim", ""))}')
        out += describe_mentions(n, tex) or ['      (no place in the text)']
        main_lines |= text_lines(n, tex)
        srcs = describe_sources(n, indent='        ')
        if srcs:
            out.append('    set in (every place must change with it):')
            out += srcs
        for c in checks_of(n):
            other = (c.get('holds_while') or {}).get('node')
            out.append(f'    check to re-evaluate: {normalize_ws(c.get("says", ""))}' + (f' (with {other})' if other else ''))
        for oid, o in m.by_id.items():
            for c in checks_of(o):
                if str((c.get('holds_while') or {}).get('node')) == i and oid not in ids:
                    out.append(f'    check to re-evaluate: {normalize_ws(c.get("says", ""))} (on {oid})')

    for name, title in TIERS:
        members = tiers[name]
        out.append(f'\n== {title}: {len(members)} ==')
        for nid in members:
            n = m.by_id[nid]
            lines = text_lines(n, tex)
            if name == 'claims':
                # The author decides what happens to a main claim; the map shows what holds it now.
                confirmed = n.get('confirmed')
                out.append(f'- {nid}: {normalize_ws(n.get("claim", ""))}'
                           + (f'  [confirmed by the author: {confirmed}]' if confirmed else '  [not confirmed by the author]'))
                out.append(f'    via: {chain_to(nid, parent)}')
                _, up = build_graph(m)
                for prev, label, edge in up.get(nid, []):
                    if label == 'rests on' and prev in steps:
                        out.append(f'    rests on {prev}: {normalize_ws((edge or {}).get("says", ""))[:120]} '
                                   f'[{support_state(m, prev, edge)}]')
                if lines:
                    out.append(f'      in the text: {fmt_lines(lines)}')
            elif name in MAIN_TIERS:
                main_lines |= lines
                out.append(f'- {nid} ({n.get("kind")}): {normalize_ws(n.get("claim", ""))}')
                out.append(f'    do: {action_for(n)}; via: {chain_to(nid, parent)}')
                says = (parent[nid][2] or {}).get('says')
                if says:
                    out.append(f'    the link says: {normalize_ws(says)}')
                out += describe_mentions(n, tex)
                if name == 'rewrite':
                    out += describe_sources(n)
            elif name == 'off-text':
                out.append(f'- {nid} ({n.get("kind")}): {normalize_ws(n.get("claim", ""))[:100]}')
                out += describe_sources(n)
            else:
                other_lines |= lines
                figs = [f'{mt.get("figure")} {mt.get("panel", "")}'.strip() for mt in mentions_of(n) if mt.get('figure')]
                where = ', '.join(x for x in (fmt_lines(lines), ', '.join(figs)) if x)
                out.append(f'- {nid} ({n.get("kind")}): {normalize_ws(n.get("claim", ""))[:100]} | {where}')

    skips = sorted(tex.anchor_lines.get('skip', []))
    out.append(f'\nLINES TO LOOK AT (recompute, rewrite, re-read): {len(main_lines)}: {fmt_lines(main_lines)}')
    other_lines -= main_lines
    out.append(f'ALSO REACHED (further up, downstream steps): {len(other_lines)}: {fmt_lines(other_lines)}')
    out.append(f'NOT ANALYSED: {len(skips)} paragraph{"" if len(skips) == 1 else "s"} marked skip'
               + (f', anchors at lines {fmt_lines(skips)}' if skips else ''))
    out.append('NODES: changed ' + str(len(ids)) + '; '
               + '; '.join(f'{name} {len(tiers[name])}' for name, _ in TIERS))
    text = '\n'.join(out) + '\n'
    print(text)
    if out_path:
        write_text(out_path, text)
    return 0


def trace(m, nid):
    m.require_loaded()
    if nid not in m.by_id:
        sys.exit(f'[FAILED] unknown node {nid}')
    _, up = build_graph(m)
    seen, q = {nid: 0}, deque([nid])
    print('TRACE of ' + nid)
    while q:
        cur = q.popleft()
        n = m.by_id.get(cur, {})
        pad = '  ' * seen[cur]
        print(f'{pad}- {cur} ({n.get("kind")}): {normalize_ws(n.get("claim", ""))}'
              + (f'  value: {n.get("value")}' if n.get('value') is not None else '')
              + (f'  scope: {n.get("scope")}' if n.get('scope') is not None else ''))
        for s in sources_of(n):
            print(f'{pad}    source: {source_where(s)} {s.get("locator", "")}'.rstrip())
        for prev, label, _ in up.get(cur, []):
            if prev not in seen:
                seen[prev] = seen[cur] + 1
                q.append(prev)
    return 0


PAGE_TEXT = {
    'en': {
        'title': 'The argument of the paper: main claims and what breaks them',
        'source': 'Built from the map {map} on {date}. The main claims are the author\'s: they are put to the author '
                  'and never reworded without agreement.',
        'confirmed': 'confirmed by the author: {}', 'unconfirmed': 'not confirmed by the author: put it to the author',
        'verdict': 'Verdict',
        'v_broken': 'does not hold as written: conditions of its support not met: {}',
        'v_deep': 'holds, but conditions not met inside its support: {}',
        'v_holds': 'holds: every condition of its support is met',
        'v_nocond': 'rests on {} supports with {} results below them; none carries a checkable condition',
        'v_none': 'rests on nothing in the map', 'v_single': 'rests on a single support',
        'v_data': 'against the data: {n} finding{s} in its support (below)',
        'data': 'Against the data, in its support', 'data_none': 'no finding',
        'kind': {'CONFLICT': 'the source disagrees', 'SCOPE': 'computed on another set than the text names',
                 'UNSOURCED': 'no source to check against', 'MISMATCH': 'the text differs from the value'},
        'f_mismatch': 'the text says {said}, the value is {value}',
        'f_scope': 'the text implies "{said}", computed on "{value}"',
        'f_unsourced': 'no source to check it against', 'f_unavailable': 'its source cannot be opened: {said}',
        'f_conflict': 'the source {where} gives {said}, the value is {value}',
        'f_disagrees': 'the source {where}: {said}',
        'breaks': 'What breaks it', 'rests': 'What it rests on', 'below': 'results below it: {}',
        'restated': 'Restatements', 'adds': 'adds', 'add_support': 'support of the addition',
        'add_none': 'no support of its own: the restatement oversells',
        'discussion': 'Discussion and literature around it', 'no_lit': 'not tied to the literature',
        'in_text': 'In the text: lines', 'questions': 'Questions for the author',
        'q_unconf': 'Main claims not yet confirmed by the author ({})',
        'q_orphans': 'Results in the text serving no main claim ({}). For each: is the link unclear, should it go, '
                     'or be strengthened?',
        'q_offtext': 'Working nodes of the map without a place in the text serving no main claim: {} (not for the author)',
        'conds': 'conditions',
        'q_disc': 'Discussion positions tied to neither a main claim nor the literature ({})',
        'q_intro': 'Questions of the Introduction without an answer ({})',
        'more': '... and {} more',
        'state': {'holds': 'holds', 'BROKEN': 'BROKEN', 'no condition': 'no condition', 'cannot evaluate': 'cannot evaluate'},
        'rel': {'confirms': 'confirms', 'extends': 'extends', 'contradicts': 'contradicts', 'contrasts': 'contrasts with',
                'uses': 'uses', 'motivates': 'is motivated by'},
    },
    'ru': {
        'title': 'Аргумент статьи: главные утверждения и что их ломает',
        'source': 'Собрано из карты {map}, {date}. Главные утверждения принадлежат автору: они выносятся на его '
                  'согласование и без согласования не меняются.',
        'confirmed': 'подтверждено автором: {}', 'unconfirmed': 'не подтверждено автором: вынести на согласование',
        'verdict': 'Вердикт',
        'v_broken': 'в нынешнем виде не держится: не выполнено условий опоры — {}',
        'v_deep': 'держится, но внутри опоры не выполнено условий — {}',
        'v_holds': 'держится: все условия опор выполнены',
        'v_nocond': 'держится на опорах: {}, под ними результатов: {}; проверяемых условий нет',
        'v_none': 'в карте ни на чём не держится', 'v_single': 'держится на одной опоре',
        'v_data': 'сверка с данными: находок в опоре — {n} (ниже)',
        'data': 'Сверка с данными в его опоре', 'data_none': 'находок нет',
        'kind': {'CONFLICT': 'источник расходится', 'SCOPE': 'посчитано не на том наборе, что назван в тексте',
                 'UNSOURCED': 'нет источника для проверки', 'MISMATCH': 'число в тексте не совпадает со значением'},
        'f_mismatch': 'в тексте {said}, значение {value}',
        'f_scope': 'текст подразумевает «{said}», посчитано на «{value}»',
        'f_unsourced': 'нет источника, по которому проверить', 'f_unavailable': 'источник не открыть: {said}',
        'f_conflict': 'источник {where} даёт {said}, значение {value}',
        'f_disagrees': 'источник {where}: {said}',
        'breaks': 'Что ломает', 'rests': 'На чём держится', 'below': 'под ней результатов: {}',
        'restated': 'Пересказы', 'adds': 'добавляет', 'add_support': 'опора добавки',
        'add_none': 'своей опоры нет: пересказ завышает',
        'discussion': 'Обсуждение и литература вокруг него', 'no_lit': 'с литературой не связано',
        'in_text': 'В тексте: строки', 'questions': 'Вопросы автору',
        'q_unconf': 'Главные утверждения, ещё не подтверждённые автором ({})',
        'q_orphans': 'Результаты в тексте, которые не служат ни одному главному утверждению ({}). По каждому: связь '
                     'неясна, убрать или усилить?',
        'q_offtext': 'Рабочих узлов карты без места в тексте, не служащих главному утверждению: {} (не для автора)',
        'conds': 'условия',
        'q_disc': 'Положения Обсуждения без главного утверждения и без литературы ({})',
        'q_intro': 'Вопросы Введения без ответа ({})',
        'more': '... и ещё {}',
        'state': {'holds': 'держится', 'BROKEN': 'НАРУШЕНО', 'no condition': 'без условия', 'cannot evaluate': 'не проверить'},
        'rel': {'confirms': 'подтверждает', 'extends': 'расширяет', 'contradicts': 'противоречит',
                'contrasts': 'отличается от', 'uses': 'использует', 'motivates': 'мотивировано работой'},
    },
}


def section_titles(tex):
    """Line number -> title of the section or subsection it belongs to."""
    titles, current = {}, 'front matter'
    for i, line in enumerate(tex.lines, 1):
        current = section_title(line) or current
        titles[i] = current
    return titles


def argument_page(m, lang='en'):
    """The page an author reads first: each main claim, its verdict, what breaks it, what it rests on,
    its restatements, the Discussion and literature around it; then the questions only the author can answer."""
    t = PAGE_TEXT[lang]
    tex = Tex(m.resolve(m.paper.get('file')))
    down, up = build_graph(m)
    # A verdict read from the paper's own numbers says nothing of the data under them.
    found_on = defaultdict(list)
    for f in value_findings(m, tex):
        found_on[f[1]].append(f)

    def claim(nid, k=160):
        s = normalize_ws(m.by_id[nid].get('claim', ''))
        return s if len(s) <= k else s[:k].rstrip() + '...'

    out = [f'# {t["title"]}', '',
           t['source'].format(map=os.path.basename(m.path), date=dt.date.today().isoformat())]
    dnas = [nid for nid, n in m.by_id.items() if n.get('kind') == 'dna']
    for i, d in enumerate(dnas, 1):
        n = m.by_id[d]
        out += ['', f'## {i}. {claim(d, 400)}', '']
        out.append(f'*{t["confirmed"].format(n["confirmed"]) if n.get("confirmed") else t["unconfirmed"]}*')
        direct = [(p, e) for p, label, e in up.get(d, []) if label == 'rests on']
        below_d = descendants({d}, up)
        broken = []
        for nid in below_d:
            for s in supports_of(m.by_id[nid]):
                if (str(s.get('to')) == d or str(s.get('to')) in below_d) and support_state(m, nid, s) == 'BROKEN':
                    broken.append((nid, s))
        states = [support_state(m, p, e) for p, e in direct]
        # A broken edge into the claim breaks it; one deeper inside its support weakens a part of it.
        broken_direct = [b for b in broken if str(b[1].get('to')) == d]
        if broken_direct:
            verdict = t['v_broken'].format(len(broken_direct))
        elif broken:
            verdict = t['v_deep'].format(len(broken))
        elif not direct:
            verdict = t['v_none']
        elif len(direct) == 1:
            verdict = t['v_single']
        elif all(s == 'no condition' for s in states):
            n_below = sum(1 for x in below_d if m.by_id[x].get('kind') in ('result', 'statement'))
            verdict = t['v_nocond'].format(len({p for p, _ in direct}), n_below)
        else:
            verdict = t['v_holds']
        with_data = [x for x in m.by_id if (x == d or x in below_d) and found_on.get(x)]
        n_data = sum(len(found_on[x]) for x in with_data)
        if n_data:
            verdict += '; ' + t['v_data'].format(n=n_data, s='' if n_data == 1 else 's')
        out += ['', f'**{t["verdict"]}:** {verdict}']
        if broken:
            out += ['', f'**{t["breaks"]}:**']
            for nid, s in broken:
                hw = s.get('holds_while')
                for c in (hw if isinstance(hw, list) else [hw]):
                    r = condition_holds(m, m.by_id[nid], c)
                    if r is not None and not r[0]:
                        out.append(f'- {normalize_ws(s.get("says", ""))} — {claim(nid, 110)}: '
                                   f'{r[1]:g} {c.get("op")} {r[2]:g}')
        counts = defaultdict(int)
        for x in with_data:
            for f in found_on[x]:
                counts[f[0]] += 1
        out += ['', f'**{t["data"]}:** ' + ('; '.join(f'{t["kind"][k]}: {c}' for k, c in counts.items())
                                           if n_data else t['data_none'])]
        for x in with_data[:8]:
            out.append(f'- {claim(x, 110)}: ' + '; '.join(t[key].format(**fields) for _, _, _, key, fields in found_on[x]))
        if len(with_data) > 8:
            out.append(f'- {t["more"].format(len(with_data) - 8)}')
        out += ['', f'**{t["rests"]}:**']
        edges_of = defaultdict(list)
        for p, e in direct:
            edges_of[p].append(e)
        for p, edges in edges_of.items():
            pn = m.by_id[p]
            below = sum(1 for x in descendants({p}, up) if m.by_id[x].get('kind') in ('result', 'statement'))
            value = f' = {pn.get("value")}' if pn.get('value') is not None else ''
            if len(edges) == 1:
                says = f' — {normalize_ws((edges[0] or {}).get("says", ""))[:140]} [{t["state"][support_state(m, p, edges[0])]}]'
            else:
                says = f' — {t["conds"]}: ' + ', '.join(t['state'][support_state(m, p, e)] for e in edges)
            out.append(f'- {claim(p)}{value}{says}' + (f'; {t["below"].format(below)}' if below else ''))
        restatements = [x for x, nx in m.by_id.items() if str(nx.get('restates')) == d]
        if restatements:
            out += ['', f'**{t["restated"]}:**']
            for x in restatements:
                own = [p for p, label, _ in up.get(x, []) if label in ('rests on', 'uses')]
                line = f'- {claim(x)}'
                if m.by_id[x].get('adds'):
                    line += (f' — {t["adds"]}: {normalize_ws(m.by_id[x]["adds"])}; '
                             + (f'{t["add_support"]}: ' + '; '.join(claim(p, 90) for p in own) if own else t['add_none']))
                out.append(line)
        around = [x for x, nx in m.by_id.items() if nx.get('kind') == 'discussion' and x not in restatements
                  and d in claims_of_discussion(m, x, down, up)]
        if around:
            out += ['', f'**{t["discussion"]}:**']
            for x in around:
                rels = '; '.join(f'{t["rel"].get(str(r.get("how")), r.get("how"))}: {claim(str(r.get("cite")), 90)}'
                                 for r in relates_of(m.by_id[x]) if str(r.get('cite')) in m.by_id)
                out.append(f'- {claim(x)} — {rels or t["no_lit"]}')
        lines = text_lines(n, tex)
        if lines:
            out += ['', f'{t["in_text"]} {fmt_lines(lines)}']

    out += ['', f'## {t["questions"]}']
    unconfirmed = [d for d in dnas if not m.by_id[d].get('confirmed')]
    if unconfirmed:
        out += ['', f'**{t["q_unconf"].format(len(unconfirmed))}**']
        out += [f'- {claim(d)}' for d in unconfirmed]
    orphans = serving_no_claim(m, down)
    # Only what the reader of the paper sees goes to the author; working nodes stay with the agent.
    in_text = [nid for nid in orphans if text_lines(m.by_id[nid], tex)]
    if in_text:
        out += ['', f'**{t["q_orphans"].format(len(in_text))}**']
        sections = section_titles(tex)
        groups = defaultdict(list)
        for nid in in_text:
            groups[sections.get(min(text_lines(m.by_id[nid], tex)), '?')].append(nid)
        for sec, ids in groups.items():
            out.append(f'- *{sec}* ({len(ids)}):')
            for nid in ids[:4]:
                out.append(f'  - {claim(nid, 120)} ({fmt_lines(text_lines(m.by_id[nid], tex))})')
            if len(ids) > 4:
                out.append(f'  - {t["more"].format(len(ids) - 4)}')
    if len(orphans) > len(in_text):
        out += ['', t['q_offtext'].format(len(orphans) - len(in_text))]
    loose = loose_discussion(m, down, up)
    if loose:
        out += ['', f'**{t["q_disc"].format(len(loose))}**']
        out += [f'- {claim(x, 140)}' for x in loose]
    unanswered = [x for x, nx in m.by_id.items() if nx.get('kind') == 'intro' and nx.get('question')
                  and not answered_by_of(nx)]
    if unanswered:
        out += ['', f'**{t["q_intro"].format(len(unanswered))}**']
        out += [f'- {claim(x)}' for x in unanswered]
    return '\n'.join(out) + '\n'


def place_anchors(m):
    m.require_loaded()
    orig_path = m.resolve(m.paper.get('original'))
    out_path = m.resolve(m.paper.get('file'))
    if not orig_path or not os.path.exists(orig_path):
        sys.exit(f'[FAILED] paper.original not found: {orig_path}')
    original = read_text(orig_path)
    text = strip_anchors(original)
    lines = text.splitlines(keepends=True)
    # Quotes are matched with all whitespace runs collapsed, so a quote may cross line breaks.
    norm_chars, norm_line, prev_space = [], [], True
    for ln, line in enumerate(lines, 1):
        for ch in line:
            if ch.isspace():
                if not prev_space:
                    norm_chars.append(' ')
                    norm_line.append(ln)
                    prev_space = True
            else:
                norm_chars.append(ch)
                norm_line.append(ln)
                prev_space = False
    norm = ''.join(norm_chars)

    requests = []
    for n in m.nodes:
        for mt in mentions_of(n):
            if mt.get('anchor') and not mt.get('figure'):
                requests.append((str(mt['anchor']), mt.get('quote'), mt.get('near_line'), str(n.get('id'))))
    for s in m.skips:
        requests.append(('skip', s.get('quote'), s.get('near_line'), 'skip'))

    placements, errors, seen = defaultdict(list), [], set()
    for anchor, quote, near, nid in requests:
        if anchor != 'skip':
            if anchor in seen:
                errors.append(f'[DUPLICATE] anchor {anchor} ({nid})')
                continue
            seen.add(anchor)
        q = normalize_ws(quote or '')
        if not q:
            errors.append(f'[NO QUOTE] {nid} {anchor}')
            continue
        hits = [mo.start() for mo in re.finditer(re.escape(q), norm)]
        if not hits:
            errors.append(f'[NOT FOUND] {nid} {anchor}: "{q[:80]}"')
            continue
        if len(hits) > 1 and near is None:
            errors.append(f'[AMBIGUOUS] {nid} {anchor}: the quote occurs {len(hits)} times '
                          f'(lines {[norm_line[h] for h in hits]}); lengthen it or set near_line')
            continue
        hit = min(hits, key=lambda h: abs(norm_line[h] - int(near))) if len(hits) > 1 else hits[0]
        end_line = norm_line[hit + len(q) - 1]
        if anchor not in placements[end_line]:
            placements[end_line].append(anchor)

    out = []
    for ln, line in enumerate(lines, 1):
        if ln in placements:
            body = line.rstrip('\r\n')
            line = body + ''.join(' %@' + a for a in placements[ln]) + line[len(body):]
        out.append(line)
    anchored = ''.join(out)
    if strip_anchors(anchored) != text:
        sys.exit('[FAILED] internal: stripping the anchors does not restore the original')
    write_text(out_path, anchored)
    print(f'anchored copy: {out_path}')
    print(f'anchors placed: {sum(len(v) for v in placements.values())}; problems: {len(errors)}')
    for e in errors:
        print('  ' + e)
    return 0 if not errors else 1


def strip_file(src, dst):
    write_text(dst, strip_anchors(read_text(src)))
    print(f'[OK] anchors removed: {dst}')
    return 0


def main():
    # Node texts are often not in English; a cp1251 console must not crash the report.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('check')
    p.add_argument('map')
    p.add_argument('--out')
    p = sub.add_parser('impact')
    p.add_argument('map')
    p.add_argument('ids', nargs='+')
    p.add_argument('--out')
    p = sub.add_parser('trace')
    p.add_argument('map')
    p.add_argument('id')
    p = sub.add_parser('argument')
    p.add_argument('map')
    p.add_argument('--lang', choices=sorted(PAGE_TEXT), default='en')
    p.add_argument('--out')
    p = sub.add_parser('place-anchors')
    p.add_argument('map')
    p = sub.add_parser('strip')
    p.add_argument('src')
    p.add_argument('dst')
    a = ap.parse_args()
    if a.cmd == 'strip':
        return strip_file(a.src, a.dst)
    m = Map(a.map)
    if a.cmd == 'check':
        return check(m, a.out)
    if a.cmd == 'impact':
        return impact(m, a.ids, a.out)
    if a.cmd == 'trace':
        return trace(m, a.id)
    if a.cmd == 'argument':
        m.require_loaded()
        page = argument_page(m, a.lang)
        print(page)
        if a.out:
            write_text(a.out, page)
        return 0
    return place_anchors(m)


if __name__ == '__main__':
    sys.exit(main())
