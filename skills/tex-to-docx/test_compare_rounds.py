"""Tests of the comparison mode: numbers from the .aux, and the round each change came from.

Three snapshots of a tiny paper; Word's comparison of the first and the last is written
by hand, as Word writes it (w:del / w:ins). No Word is needed for these. The end-to-end
run through Word is at the bottom and is skipped, with the reason, where Word is absent.

Run: python test_compare_rounds.py
"""
import sys
import tempfile
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')  # round labels are Russian; a cp1251 console would crash
sys.path.insert(0, str(Path(__file__).parent))
import aux_numbers  # noqa: E402
import round_labels  # noqa: E402

ok = True


def check(name, got, want):
    global ok
    good = got == want
    ok &= good
    print(f'[{"PASS" if good else "FAIL"}] {name}')
    if not good:
        print(f'        got : {got!r}\n        want: {want!r}')


NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def doc(*paras):
    """document.xml with one paragraph per argument; an argument is a list of runs,
    a run is text, ('del', text) or ('ins', text)."""
    out, rid = [], [0]

    def run(r):
        if isinstance(r, str):
            return '<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % r
        rid[0] += 1
        kind, text = r
        tag = 'delText' if kind == 'del' else 't'
        return ('<w:%s w:id="%d" w:author="compare" w:date="2026-01-01T00:00:00Z"><w:r><w:%s xml:space="preserve">%s'
                '</w:%s></w:r></w:%s>' % (kind, rid[0], tag, text, tag, kind))
    for p in paras:
        runs = [p] if isinstance(p, (str, tuple)) else p
        out.append('<w:p>%s</w:p>' % ''.join(run(r) for r in runs))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document %s><w:body>%s</w:body></w:document>'
            % (NS, ''.join(out))).encode('utf-8')


# Round 1 (co-author): drops "very" and adds a sentence. Round 2 (agent): cuts the second
# paragraph's last clause and replaces "big" by "large".
S0 = doc('The method is very fast.', 'It finds big effects in all mice, as shown before.')
S1 = doc('The method is fast. It needs no tuning.', 'It finds big effects in all mice, as shown before.')
S2 = doc('The method is fast. It needs no tuning.', 'It finds large effects in all mice.')
TRACKED = doc(['The method is ', ('del', 'very '), 'fast.', ('ins', ' It needs no tuning.')],
              ['It finds ', ('del', 'big'), ('ins', 'large'), ' effects in all mice', ('del', ', as shown before'), '.'])
ROUNDS = [None, ('соавтор (PDF 03.11): снята фраза', '2026-11-04T12:00:00Z'),
          ('агент, 06.11: сокращение под 10 страниц', '2026-11-06T12:00:00Z')]

print('--- round of each change ---')
xml, recs, extra = round_labels.label_part(TRACKED, [S0, S1, S2], ROUNDS)
got = [(r['kind'], r['text'].strip(), r['caption']) for r in recs]
check('deletion of "very" -> round 1', got[0], ('del', 'very', ROUNDS[1][0]))
check('inserted sentence -> round 1', got[1], ('ins', 'It needs no tuning.', ROUNDS[1][0]))
check('"big" -> "large" -> round 2 (both halves)', got[2:4],
      [('del', 'big', ROUNDS[2][0]), ('ins', 'large', ROUNDS[2][0])])
check('cut clause -> round 2', got[4], ('del', ', as shown before', ROUNDS[2][0]))
check('date of the change = date of its round', recs[0]['date'], ROUNDS[1][1])
check('the author is written into the XML', ROUNDS[2][0].encode('utf-8') in xml and b'"compare"' not in xml, True)

print('\n--- a change made of two rounds names both ---')
T0 = doc('alpha beta gamma delta')
T1 = doc('alpha gamma delta')          # round 1 removes beta
T2 = doc('alpha delta')                # round 2 removes gamma
T = doc(['alpha ', ('del', 'beta gamma '), 'delta'])
_, recs2, _ = round_labels.label_part(T, [T0, T1, T2], ROUNDS)
check('two rounds joined with " + "', recs2[0]['caption'], ROUNDS[1][0] + ' + ' + ROUNDS[2][0])

print('\n--- a change no snapshot explains is said to be unexplained ---')
U0 = doc('one two three')
U1 = doc('one two three')
U = doc(['one ', ('del', 'two'), ('ins', 'two'), ' three'])   # Word saw a change the chain did not
_, recs3, _ = round_labels.label_part(U, [U0, U1], ROUNDS[:2])
check('unexplained -> "источник не определён"', {r['caption'] for r in recs3}, {round_labels.UNKNOWN})

print('\n--- accept all / reject all views ---')
p = round_labels.Part(TRACKED)
check('reject all = first snapshot',
      p.views['old']['text'].split(), round_labels.Part(S0).views['new']['text'].split())
check('accept all = last snapshot',
      p.views['new']['text'].split(), round_labels.Part(S2).views['new']['text'].split())

print('\n--- numbers from the .aux ---')
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    (tmp / 'p.tex').write_text(
        '\\documentclass{article}\n\\usepackage{cleveref}\n\\newcommand{\\fig}[1]{Fig.~\\ref{#1}}\n'
        '\\newcommand{\\be}{\\begin{equation}}\n\\newcommand{\\ee}{\\end{equation}}\n'
        '\\begin{document}\n\\section{Intro}\\label{sec:i}\nSee \\fig{fig:a}, \\Cref{tab:t}, '
        '\\S\\ref{sec:m} and \\eqref{eq:x}. % a comment\n'
        '\\section*{Unnumbered}\n\\section{Methods}\\label{sec:m}\n\\be x=1 \\label{eq:x}\\ee\n'
        '\\begin{figure}\\caption{A figure.}\\label{fig:a}\\end{figure}\n'
        '\\begin{table}\\caption{A table.}\\label{tab:t}\\end{table}\n\\end{document}\n', encoding='utf-8')
    (tmp / 'p.aux').write_text(
        '\\newlabel{sec:i}{{1}{1}}\n\\newlabel{sec:m}{{2}{1}}\n\\newlabel{eq:x}{{1}{1}}\n'
        '\\newlabel{fig:a}{{1}{1}}\n\\newlabel{tab:t}{{1}{1}}\n\\newlabel{tab:t@cref}{{[table][1][]1}{[1][1][]1}}\n'
        '\\@writefile{toc}{\\contentsline {section}{\\numberline {1}Intro}{1}{section.1}}\n'
        '\\@writefile{toc}{\\contentsline {section}{\\numberline {2}Methods}{1}{section.2}}\n'
        '\\@writefile{lof}{\\contentsline {figure}{\\numberline {1}{\\ignorespaces A figure.}}{1}}\n'
        '\\@writefile{lot}{\\contentsline {table}{\\numberline {1}{\\ignorespaces A table.}}{1}}\n', encoding='utf-8')
    probs = aux_numbers.prepare(tmp / 'p.tex', tmp / 'p.aux', tmp / 'out.tex')
    out = (tmp / 'out.tex').read_text(encoding='utf-8')
    check('no problems', probs, [])
    check('macro-wrapped \\ref resolved', 'See Fig.~1,' in out, True)
    check('\\Cref with its word', 'Table\u00a01' in out, True)
    check('section sign kept with its number', '\u00a72 and' in out, True)
    check('\\eqref in parentheses', '(1).' in out, True)
    check('numbered headings, starred left alone',
          ('\\section{1 Intro}' in out, '\\section*{Unnumbered}' in out, '\\section{2 Methods}' in out),
          (True, True, True))
    check('captions numbered', ('\\textbf{Figure 1.} A figure.' in out, '\\textbf{Table 1.} A table.' in out),
          (True, True))
    check('no comment, no \\be shorthand left', ('a comment' in out, '\\be ' in out), (False, False))
    aux_numbers.prepare(tmp / 'p.tex', tmp / 'p.aux', tmp / 'out3.tex', final={'fig:a': '2', 'sec:m': '3'})
    out3 = (tmp / 'out3.tex').read_text(encoding='utf-8')
    check('numbers of the last version: no renumbering shown',
          ('See Fig.~2,' in out3, '\\textbf{Figure 2.}' in out3, '\\section{3 Methods}' in out3, '\u00a73 and' in out3),
          (True, True, True, True))
    (tmp / 'q.aux').write_text('\\newlabel{sec:i}{{1}{1}}\n', encoding='utf-8')
    probs = aux_numbers.prepare(tmp / 'p.tex', tmp / 'q.aux', tmp / 'out2.tex')
    check('an unresolved reference is reported, not hidden',
          any('unresolved reference sec:m' in p for p in probs), True)

print('\n--- a file name with a dot in it, as LaTeX reads it ---')
import tex2docx  # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    (tmp / 'references_v11.1.bib').write_text('@article{a, title={A}}\n', encoding='utf-8')
    (tmp / 'appendix_v11.1.tex').write_text('Appendix text.\n', encoding='utf-8')
    check('\\bibliography{references_v11.1} -> references_v11.1.bib',
          [b.name for b in tex2docx.find_bibliography('\\bibliography{references_v11.1}', tmp)],
          ['references_v11.1.bib'])
    check('\\input{appendix_v11.1} -> appendix_v11.1.tex',
          'Appendix text.' in tex2docx.expand_inputs('\\input{appendix_v11.1}', tmp), True)

print('\n--- end to end through Word ---')
try:
    import win32com.client  # noqa: F401
    import pythoncom
    pythoncom.CoInitialize()
    w = win32com.client.DispatchEx('Word.Application')
    w.Quit()
    have_word = True
except Exception as exc:  # noqa: BLE001
    have_word = False
    print('[SKIP] Word is not available here (%s); the comparison itself needs Microsoft Word.'
          % type(exc).__name__)
if have_word:
    import compare_rounds
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        files = []
        for i, x in enumerate((S0, S1, S2)):
            f = tmp / ('s%d.docx' % i)
            with zipfile.ZipFile(f, 'w') as z:
                z.writestr('[Content_Types].xml',
                           '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/'
                           'package/2006/content-types"><Default Extension="rels" ContentType="application/'
                           'vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType='
                           '"application/xml"/><Override PartName="/word/document.xml" ContentType="application/'
                           'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
                z.writestr('_rels/.rels',
                           '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.'
                           'org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.'
                           'openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                           'Target="word/document.xml"/></Relationships>')
                z.writestr('word/document.xml', x)
            files.append(f)
        w = compare_rounds.word()
        try:
            compare_rounds.word_compare(w, files[0], files[2], tmp / 'raw.docx', 'compare')
        finally:
            w.Quit()
        recs, _ = round_labels.label_docx(tmp / 'raw.docx', files,
                                          [None, ('round one', '04.11.2026'), ('round two', '06.11.2026')],
                                          tmp / 'signed.docx')
        caps = {r['text'].strip(): r['caption'] for r in recs if r['text'].strip()}
        check('Word: "very" signed round one', caps.get('very'), 'round one')
        check('Word: no change left unsigned', round_labels.UNKNOWN in caps.values(), False)
        v = round_labels.views_text(tmp / 'signed.docx')
        check('Word: accept all = last, reject all = first',
              (v['new'] == round_labels.views_text(files[2])['new'], v['old'] == round_labels.views_text(files[0])['new']),
              (True, True))

print('\nALL PASS' if ok else '\nSOME FAILED')
sys.exit(0 if ok else 1)
