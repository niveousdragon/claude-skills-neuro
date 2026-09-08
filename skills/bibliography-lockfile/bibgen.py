# -*- coding: utf-8 -*-
"""bibgen — генератор refs.bib из издательских метаданных.

Принцип: авторские поля НИКОГДА не набираются руками и не «расшифровываются» —
они приходят из Crossref/arXiv/PMLR/OpenAlex или через явный authors_override
с verified-штампом в sources.yaml.

Запуск:   python bibgen.py                     -> refs.generated.bib + report.md
Сверка:   python bibgen.py --compare path.bib  -> сравнение авторских полей
"""
import json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')
os.makedirs(CACHE, exist_ok=True)

UA = {'User-Agent': 'bibgen/1.0 (bibliography generator, academic use)'}


def _cached_get(url, cache_key):
    path = os.path.join(CACHE, re.sub(r'[^A-Za-z0-9._-]', '_', cache_key) + '.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))['body']
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        body = r.read().decode('utf-8', 'replace')
    json.dump({'url': url, 'fetched': time.strftime('%Y-%m-%d %H:%M'), 'body': body},
              open(path, 'w', encoding='utf-8'))
    time.sleep(0.2)
    return body


# ---------------- LaTeX escaping (NFD combining marks -> macros) --------------
COMBINING = {u'\u0301': "'", u'\u0300': '`', u'\u0308': '"', u'\u0302': '^',
             u'\u0303': '~', u'\u030c': 'v', u'\u0306': 'u', u'\u0307': '.',
             u'\u030a': 'r', u'\u0327': 'c', u'\u030b': 'H', u'\u0304': '='}
SPECIAL = {u'ø': r'{\o}', u'Ø': r'{\O}', u'ß': r'{\ss}', u'ł': r'{\l}',
           u'Ł': r'{\L}', u'æ': r'{\ae}', u'Æ': r'{\AE}', u'đ': r'{\dj}',
           u'’': "'", u'‘': '`', u'–': '--', u'—': '---', u'&': r'\&'}


def latex_escape(s):
    out = []
    for ch in s:
        if ord(ch) < 128:
            out.append(SPECIAL.get(ch, ch))
            continue
        if ch in SPECIAL:
            out.append(SPECIAL[ch]); continue
        d = unicodedata.normalize('NFD', ch)
        if len(d) == 2 and d[1] in COMBINING:
            base = d[0]
            if base in 'ij':
                base = '\\' + base + ' '
            out.append('{\\%s{%s}}' % (COMBINING[d[1]], base))
        else:
            out.append(ch)  # оставить как есть; попадёт в отчёт как warning
    return ''.join(out)


def protect_title(t):
    words = []
    for w in t.split(' '):
        core = re.sub(r'[^A-Za-z0-9+-]', '', w)
        if core and core != core.lower() and not (core[0].isupper() and core[1:].islower()):
            words.append('{' + w + '}')
        else:
            words.append(w)
    return ' '.join(words)


# ------------------------------- fetchers ------------------------------------
def fetch_crossref(doi):
    body = _cached_get('https://api.crossref.org/works/' + urllib.parse.quote(doi),
                       'crossref_' + doi)
    m = json.loads(body)['message']
    authors = []
    for a in m.get('author', []):
        fam, giv, suf = a.get('family', ''), a.get('given', ''), a.get('suffix', '')
        if suf:
            authors.append('%s, %s, %s' % (fam, suf, giv))
        else:
            authors.append('%s, %s' % (fam, giv) if giv else fam)
    return {'authors': authors, 'title': ' '.join(m.get('title', [])),
            'journal': ' '.join(m.get('container-title', [])),
            'volume': m.get('volume'), 'number': m.get('issue'),
            'pages': (m.get('page') or '').replace('-', '--') or None,
            'year': str(m.get('issued', {}).get('date-parts', [[None]])[0][0] or ''),
            'doi': doi}


def fetch_arxiv(aid):
    body = _cached_get('http://export.arxiv.org/api/query?id_list=' + aid, 'arxiv_' + aid)
    entry = re.search(r'<entry>(.*?)</entry>', body, re.S)
    if not entry:
        raise RuntimeError('arXiv: no entry for ' + aid)
    e = entry.group(1)
    names = re.findall(r'<name>(.*?)</name>', e)         # natural order
    title = re.search(r'<title>(.*?)</title>', e, re.S).group(1)
    year = re.search(r'<published>(\d{4})', e).group(1)
    return {'authors': names, 'title': re.sub(r'\s+', ' ', title).strip(),
            'journal': None, 'volume': None, 'number': None, 'pages': None,
            'year': year, 'doi': None}


def fetch_pmlr(pid):
    body = _cached_get('https://proceedings.mlr.press/%s.html' % pid, 'pmlr_' + pid.replace('/', '_'))
    names = re.findall(r'name="citation_author" content="(.*?)"', body)   # natural order
    title = re.search(r'name="citation_title" content="(.*?)"', body).group(1)
    year = re.search(r'name="citation_publication_date" content="(\d{4})', body).group(1)
    if not names:
        raise RuntimeError('PMLR: no citation_author meta for ' + pid)
    return {'authors': names, 'title': title, 'journal': None, 'volume': None,
            'number': None, 'pages': None, 'year': year, 'doi': None}


def _norm_title(t):
    return re.sub(r'[^a-z0-9]', '', t.lower())


def fetch_openalex_title(title):
    body = _cached_get('https://api.openalex.org/works?search=' + urllib.parse.quote(title) +
                       '&per-page=5', 'openalex_' + _norm_title(title)[:60])
    items = json.loads(body)['results']
    want = _norm_title(title)
    for it in items:
        if _norm_title(it.get('title') or '') == want:
            names = [a['author']['display_name'] for a in it.get('authorships', [])]
            return {'authors': names, 'title': it['title'], 'journal': None,
                    'volume': None, 'number': None, 'pages': None,
                    'year': str(it.get('publication_year') or ''), 'doi': None}
    raise RuntimeError('OpenAlex: no exact-title match for "%s"' % title)


# ------------------------------- rendering -----------------------------------
FIELD_ORDER = ['title', 'author', 'journal', 'booktitle', 'series', 'institution',
               'publisher', 'edition', 'volume', 'number', 'pages', 'address',
               'year', 'doi', 'note']


def render_entry(key, etype, fields):
    lines = ['@%s{%s,' % (etype, key)]
    for f in FIELD_ORDER:
        if fields.get(f):
            lines.append('  %-9s = {%s},' % (f, fields[f]))
    lines[-1] = lines[-1].rstrip(',')
    lines.append('}')
    return '\n'.join(lines)


def build(entries):
    out, report, failures = [], [], []
    for key, spec in entries.items():
        etype = spec.get('type', 'article')
        try:
            if spec.get('manual'):
                if not spec.get('verified'):
                    raise RuntimeError('manual entry without verified stamp')
                fields = dict(spec['fields'])
                src = 'manual (verified: %s)' % spec['verified']
            else:
                if 'doi' in spec:
                    meta, src = fetch_crossref(spec['doi']), 'crossref:' + spec['doi']
                elif 'arxiv' in spec:
                    meta, src = fetch_arxiv(spec['arxiv']), 'arxiv:' + spec['arxiv']
                elif 'pmlr' in spec:
                    meta, src = fetch_pmlr(spec['pmlr']), 'pmlr:' + spec['pmlr']
                elif 'openalex_title' in spec:
                    meta, src = fetch_openalex_title(spec['openalex_title']), 'openalex'
                else:
                    raise RuntimeError('no source specified')
                fields = {'title': protect_title(latex_escape(meta['title'])),
                          'journal': latex_escape(meta['journal']) if meta.get('journal') else None,
                          'volume': meta.get('volume'), 'number': meta.get('number'),
                          'pages': meta.get('pages'), 'year': meta.get('year'),
                          'doi': meta.get('doi')}
                if spec.get('authors_override'):
                    if not spec.get('verified'):
                        raise RuntimeError('authors_override without verified stamp')
                    fields['author'] = spec['authors_override']
                    src += ' + authors_override (verified: %s)' % spec['verified']
                else:
                    if not meta['authors']:
                        raise RuntimeError('source returned empty author list')
                    fields['author'] = ' and '.join(latex_escape(a) for a in meta['authors'])
            for f, v in (spec.get('override') or {}).items():
                fields[f] = v
            if not fields.get('author'):
                raise RuntimeError('no author field after merge')
            out.append(render_entry(key, etype, fields))
            report.append('| %s | %s | OK | %s |' % (key, src, fields['author'][:90]))
        except Exception as exc:
            failures.append(key)
            report.append('| %s | - | **FAILED: %s** | |' % (key, exc))
    return out, report, failures


# ------------------------------- comparison ----------------------------------
def parse_bib_authors(path):
    txt = open(path, encoding='utf-8').read()
    res = {}
    for m in re.finditer(r'@\w+\s*\{\s*([^,\s]+)\s*,(.*?)\n\}', txt, re.S):
        key, body = m.group(1), m.group(2)
        am = re.search(r'author\s*=\s*\{(.*?)\},?\s*\n', body, re.S)
        if am:
            res[key] = re.sub(r'\s+', ' ', am.group(1)).strip()
    return res


def strip_tex(s):
    s = re.sub(r'\\[a-zA-Z]+\s*', '', s)
    s = re.sub(r'[{}\\\'"`^~=.]', '', s)
    return unicodedata.normalize('NFKD', s)


PARTICLES = {'van', 'den', 'der', 'de', 'von', 'del', 'la'}
SUFFIXES = {'jr', 'jr.', 'ii', 'iii'}


def families(author_field):
    """Нормализованная фамилия: без частиц (van den ...) и суффиксов (Jr, II)."""
    fams = []
    for part in re.split(r'\s+and\s+', author_field):
        part = strip_tex(part).strip()
        fam = part.split(',')[0].strip() if ',' in part else part
        toks = [t for t in fam.lower().split() if t not in PARTICLES]
        while toks and toks[-1] in SUFFIXES:
            toks.pop()
        fams.append(toks[-1] if toks else '')
    return fams


def main():
    import yaml
    entries = yaml.safe_load(open(os.path.join(HERE, 'sources.yaml'), encoding='utf-8'))['entries']
    out, report, failures = build(entries)
    header = ('% GENERATED by tools/bibgen/bibgen.py from sources.yaml — DO NOT EDIT BY HAND.\n'
              '% To add or change a reference, edit sources.yaml and regenerate.\n'
              '% Generated: {}, {} entries.\n\n'.format(time.strftime('%Y-%m-%d %H:%M'), len(out)))
    open(os.path.join(HERE, 'refs.generated.bib'), 'w', encoding='utf-8').write(
        header + '\n\n'.join(out) + '\n')
    rep = ['# bibgen report — %s' % time.strftime('%Y-%m-%d %H:%M'),
           '', '| key | source | status | author field |', '|---|---|---|---|'] + report
    if failures:
        rep.append('\n**FAILURES: %s**' % failures)
    open(os.path.join(HERE, 'report.md'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    print('generated %d entries, %d failures %s' % (len(out), len(failures), failures or ''))

    if '--compare' in sys.argv:
        ref_path = sys.argv[sys.argv.index('--compare') + 1]
        ref = parse_bib_authors(ref_path)
        gen = parse_bib_authors(os.path.join(HERE, 'refs.generated.bib'))
        print('\n--- comparison vs %s (surname level) ---' % os.path.basename(ref_path))
        mismatch = 0
        for key in gen:
            if key not in ref:
                print('ONLY-IN-GENERATED:', key); continue
            fg, fr = families(gen[key]), families(ref[key])
            if fg != fr:
                mismatch += 1
                print('DIFF %s\n  gen: %s\n  ref: %s' % (key, fg, fr))
        for key in ref:
            if key not in gen:
                print('ONLY-IN-REFERENCE:', key)
        print('surname-level mismatches: %d' % mismatch)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
