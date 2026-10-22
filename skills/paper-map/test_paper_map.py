"""Behaviour the skill relies on, checked on a small paper written here.

Run: python test_paper_map.py
"""
import contextlib
import hashlib
import io
import os
import sys
import tempfile
import types
from pathlib import Path

# The skill folder is installed for agents; a test run must not leave a byte-code cache in it.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import paper_map as pm

ok = True


def check(name, got, want):
    global ok
    good = got == want
    ok &= good
    print(f'[{"PASS" if good else "FAIL"}] {name}')
    if not good:
        print(f'        got : {got!r}\n        want: {want!r}')


PAPER = r"""\documentclass{article}
\begin{document}
\begin{abstract}
About 34\% of V1 neurons respond to drifting gratings in our recordings.
\end{abstract}
\section{Results}
Of 412 segmented neurons, 34\% (95\% CI 29--39\%) responded to
drifting gratings, and the response was tested against shuffled traces.

\section{Discussion}
A substantial fraction of V1 neurons responds, which supports a dense code.
This is consistent with earlier reports of dense coding in visual cortex.
Dense coding is likely universal across the cortex, as earlier work suggested.

\section{Methods}
Cells closer than 5~$\mu$m were merged, at a pixel size of
0.5~$\mu$m. Stimuli were shown at 80\% contrast on a grey background.
Responses were tested against shuffled traces of the same neuron.

\section{Data availability}
Processed tables will be deposited in a public repository on publication.
\end{document}
"""

MAIN = """paper:
  original: 'paper.tex'
  file: 'paper_anchored.tex'
  date: 2026-01-15
scopes:
  S_all: 'all neurons, 5 mice'
parts: ['parts/results.yaml']
skip:
  - {quote: 'Processed tables will be deposited', why: 'a promise, nothing to check'}
nodes:
  - id: P-pix
    kind: param
    claim: 'pixel size'
    value: '0.5'
    sources: [{file: 'calib.txt', sha256: '%(calib)s', locator: 'line 1', value: '0.5'}]
    mentions: [{anchor: pix-m, quote: 'at a pixel size of 0.5~$\\mu$m', states: '0.5'}]
    checks:
      - {says: 'the pixel size equals the calibration of the microscope', holds_while: {op: '==', node: P-calib}}
  - id: P-calib
    kind: param
    claim: 'calibration of the microscope'
    value: '0.6'
    sources: [{file: 'calib.txt', sha256: '%(calib)s', locator: 'line 2'}]
  - id: P-merge
    kind: param
    claim: 'merge distance in micrometres, converted to pixels with the pixel size'
    value: '5'
    uses: [P-pix]
    sources: [{file: 'calib.txt', sha256: '%(calib)s', locator: 'line 3'}]
    mentions: [{anchor: merge-m, quote: 'Cells closer than 5~$\\mu$m were merged', states: '5'}]
  - id: P-contrast
    kind: param
    claim: 'stimulus contrast'
    value: '80'
    mentions: [{anchor: contrast-m, quote: 'Stimuli were shown at 80\\%% contrast', states: '80'}]
  - id: M-seg
    kind: method
    claim: 'segmentation run'
    uses: [P-merge]
    sources: [{file: 'calib.txt', sha256: '%(calib)s', locator: 'run log'}]
  - id: M-test
    kind: method
    claim: 'responses tested against shuffled traces'
    uses: [M-seg]
    mentions: [{anchor: test-m, quote: 'Responses were tested against shuffled traces of the same neuron'}]
  - id: R-n
    kind: result
    claim: 'number of segmented neurons'
    value: '412'
    scope: S_all
    uses: [P-pix]
    sources: [{file: 'calib.txt', sha256: '%(calib)s', locator: 'line 4', value: '412'}]
    mentions: [{anchor: n-r, quote: 'Of 412 segmented neurons', states: '412', scope: S_all}]
"""

PART = """nodes:
  - id: R-resp
    kind: result
    claim: 'fraction of neurons responding to gratings'
    value: '34.2 [29.1, 39.0]'
    scope: S_all
    uses: [M-seg, P-contrast]
    sources: [{file: 'calib.txt', sha256: '%(calib)s', locator: 'line 5', value: '34.2'}]
    mentions:
      - {anchor: resp-abs, quote: 'About 34\\%% of V1 neurons respond', states: '34', scope: S_all}
      - {anchor: resp-r, quote: '34\\%% (95\\%% CI 29--39\\%%) responded to drifting gratings', scope: S_all}
      - {anchor: resp-test, quote: 'and the response was tested against shuffled traces.'}
    supports:
      - {to: D-dense, says: 'a sizeable fraction responds', holds_while: {op: '>=', value: 25}}
      - {to: DNA-dense, says: 'a dense code needs most neurons responding', holds_while: {op: '>', value: 50}}
  - id: D-dense
    kind: discussion
    claim: 'V1 code is dense'
    mentions: [{anchor: dense-d, quote: 'A substantial fraction of V1 neurons responds, which supports a dense code.'}]
    supports: [{to: DNA-dense, says: 'the main claim rests on the dense code'}]
    relates: [{cite: C-prior, how: confirms, says: 'agrees with earlier reports'}]
  - id: DNA-dense
    kind: dna
    claim: 'dense coding in V1'
    mentions: [{anchor: dna-d, quote: 'This is consistent with earlier reports of dense coding in visual cortex.'}]
  - id: D-everywhere
    kind: discussion
    claim: 'dense coding throughout the cortex'
    restates: DNA-dense
    adds: 'all cortical areas'
    mentions: [{anchor: every-d, quote: 'Dense coding is likely universal across the cortex'}]
  - id: C-prior
    kind: cite
    bibkey: smith2020
    claim: 'earlier work found dense coding'
    mentions: [{anchor: prior-c, quote: 'as earlier work suggested.'}]
"""


def run(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(*args)
    return code, buf.getvalue()


def make_paper(tmp, main=MAIN, part=PART):
    calib = b'0.5\n0.6\n5\n412\n34.2\n'
    (tmp / 'calib.txt').write_bytes(calib)
    sha = hashlib.sha256(calib).hexdigest()
    (tmp / 'paper.tex').write_text(PAPER, encoding='utf-8', newline='')
    (tmp / 'parts').mkdir(exist_ok=True)
    (tmp / 'parts' / 'results.yaml').write_text(part % {'calib': sha}, encoding='utf-8')
    (tmp / 'paper.map.yaml').write_text(main % {'calib': sha}, encoding='utf-8')
    return tmp / 'paper.map.yaml'


with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    map_path = make_paper(tmp)
    code, out = run(pm.place_anchors, pm.Map(str(map_path)))
    check('place-anchors places every anchor', code, 0)
    anchored = (tmp / 'paper_anchored.tex').read_text(encoding='utf-8')
    check('stripping anchors restores the paper byte for byte', pm.strip_anchors(anchored), PAPER)

    print('--- check ---')
    code, out = run(pm.check, pm.Map(str(map_path)))
    check('nodes from a part are loaded: the map is clean', code, 0)
    check('a failed consistency check is a finding', '[INCONSISTENT] P-pix' in out, True)
    check('a parameter without a source is warned about', 'P-contrast: parameter without a source' in out, True)

    print('--- impact ---')
    tiers = pm.impact_tiers(pm.Map(str(map_path)), ['P-pix'])
    check('a result computed from the change is recomputed', sorted(tiers['recompute']), ['R-n', 'R-resp'])
    check('a parameter using the change directly is rewritten', tiers['rewrite'], ['P-merge'])
    check('a statement one argument step away is re-read', tiers['re-read'], ['D-dense'])
    check('a main claim reached is listed as a claim at stake', tiers['claims'], ['DNA-dense'])
    check('a restatement and a cited work two steps away are further up', sorted(tiers['further']),
          ['C-prior', 'D-everywhere'])
    check('a method fed indirectly is a downstream step', tiers['downstream'], ['M-test'])
    check('a node without a place in the text is listed apart', tiers['off-text'], ['M-seg'])
    reached = {x for k, v in tiers.items() for x in v}
    check('a consistency check is not followed', 'P-calib' in reached, False)

    code, out = run(pm.impact, pm.Map(str(map_path)), ['P-pix'])
    check('a quote over two lines is reported as a range', 'lines 7-8' in out, True)
    check('where the changed value is set is shown', 'calib.txt' in out.split('RECOMPUTE')[0], True)
    check('the consistency check of the changed node is named', 'the calibration of the microscope' in out, True)
    main_line = next(l for l in out.splitlines() if l.startswith('LINES TO LOOK AT'))
    listed = set()
    for part in main_line.split(': ', 2)[2].split(','):
        lo, _, hi = part.strip().partition('-')
        if lo:
            listed.update(range(int(lo), int(hi or lo) + 1))
    check('the lines to look at hold the result and the statement', {4, 7, 8, 11} <= listed, True)
    check('the framing claim is not among the lines to look at', 12 in listed, False)
    check('paragraphs marked skip are reported as not analysed', 'NOT ANALYSED: 1 paragraph' in out, True)
    check('main claims at stake come first, for the author', out.index('MAIN CLAIMS AT STAKE') < out.index('RECOMPUTE'), True)
    check('the broken support of a main claim is shown at stake', 'BROKEN' in out.split('RECOMPUTE')[0], True)

    print('--- argument ---')
    code, out = run(pm.check, pm.Map(str(map_path)))
    check('a main claim not confirmed by the author is listed', 'main claims not confirmed by the author: 1' in out, True)
    check('a result serving no main claim is listed', 'serving no main claim: 1' in out and 'R-n' in out.split('== ARGUMENT')[1], True)
    check('a restatement that adds without support is overstated', '[OVERSTATED] D-everywhere' in out, True)
    page = pm.argument_page(pm.Map(str(map_path)), 'en')
    check('the page names the main claim', 'dense coding in V1' in page, True)
    check('the page marks it unconfirmed', 'not confirmed by the author' in page, True)
    check('the page says what breaks it', 'a dense code needs most neurons responding' in page.split('What breaks it')[1], True)
    check('the page shows the restatement and what it adds', 'all cortical areas' in page, True)
    check('the page shows the Discussion with its literature', 'confirms: earlier work found dense coding' in page, True)
    check('the page asks the author about results serving nothing', 'number of segmented neurons' in page.split('Questions for the author')[1], True)
    page_ru = pm.argument_page(pm.Map(str(map_path)), 'ru')
    check('the page can be written in Russian', 'Что ломает' in page_ru and 'подтверждает' in page_ru, True)

    code, out = run(pm.impact, pm.Map(str(map_path)), ['P-calib'])
    check('changing the other side of a check reaches nothing', 'NODES: changed 1; claims 0; recompute 0' in out, True)

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    dup = PART + """  - id: P-pix
    kind: param
    claim: 'pixel size, again'
"""
    map_path = make_paper(tmp, part=dup)
    run(pm.place_anchors, pm.Map(str(map_path)))
    code, out = run(pm.check, pm.Map(str(map_path)))
    check('the same id in the map and in a part is an error', 'duplicate node id P-pix' in out, True)

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    odd = MAIN.replace("    mentions: [{anchor: merge-m",
                       "    supports: [{to: P-calib, says: 'must agree'}]\n    mentions: [{anchor: merge-m")
    map_path = make_paper(tmp, main=odd)
    run(pm.place_anchors, pm.Map(str(map_path)))
    code, out = run(pm.check, pm.Map(str(map_path)))
    check('supports into a parameter is warned about', 'P-merge supports P-calib (param)' in out, True)

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    twin = MAIN.replace("  - id: P-contrast\n",
                        "  - id: P-pix-again\n    kind: param\n    claim: 'pixel size, written down a second time'\n"
                        "    value: '0.5'\n"
                        "    sources: [{file: 'calib.txt', sha256: '%(calib)s', locator: 'line 1: 0.5'}]\n"
                        "  - id: P-contrast\n")
    twin = twin.replace("{says: 'the pixel size equals the calibration of the microscope', holds_while: {op: '==', node: P-calib}}",
                        "{says: 'the pixel size equals the calibration of the microscope', holds_while: {op: '==', node: M-seg}}")
    map_path = make_paper(tmp, main=twin)
    run(pm.place_anchors, pm.Map(str(map_path)))
    code, out = run(pm.check, pm.Map(str(map_path)))
    check('two parameters set on the same line of a source are warned about',
          'P-pix and P-pix-again are set on the same line' in out, True)
    check('a condition against a node without a value says so', 'node M-seg has no numeric value' in out, True)

print('--- conditions ---')
fake = types.SimpleNamespace(by_id={'A': {'value': '0.5'}, 'B': {'value': '0.6'}, 'C': {'value': '0.50'},
                                    'N': {'value': '-0.3 [-0.5, -0.1]'}, 'M': {'value': '-0.5'}})
check('a negative value keeps its sign', pm.condition_holds(fake, fake.by_id['N'], {'op': '<', 'value': 0})[0], True)
check('two negative values compare by sign', pm.condition_holds(fake, fake.by_id['N'], {'op': '>', 'node': 'M'})[0], True)
check('a negative bound from YAML keeps its sign', pm.condition_holds(fake, fake.by_id['A'], {'op': '>', 'value': -1.0})[0], True)
check('== at the stated precision: 0.5 and 0.6 differ', pm.condition_holds(fake, fake.by_id['A'], {'op': '==', 'node': 'B'})[0], False)
check('== at the stated precision: 0.5 and 0.50 agree', pm.condition_holds(fake, fake.by_id['A'], {'op': '==', 'node': 'C'})[0], True)
check('== with a tolerance', pm.condition_holds(fake, fake.by_id['A'], {'op': '==', 'node': 'B', 'tolerance': 0.2})[0], True)
check('>= against a number', pm.condition_holds(fake, fake.by_id['A'], {'op': '>=', 'value': 0.4})[0], True)
check('an unknown operator cannot be evaluated', pm.condition_holds(fake, fake.by_id['A'], {'op': '~', 'value': 1}), None)

print('--- numbers ---')
check('thin space thousands', pm.number_tokens(r'10\,000 shuffles'), ['10000'])
check('power of ten', pm.number_tokens(r'$p = 6.6\times10^{-11}$'), ['6.6e-11'])
check('digits in names are not numbers', pm.number_tokens('CA1 neurons of F28_1D in 2D'), [])
check('ordinals are numbers', pm.number_tokens('the 85th percentile'), ['85'])
check('confidence level is not a number', pm.number_tokens(r'95\% CI 29--39\%'), ['29', '39'])
check('names of layers and sections are not numbers', pm.number_tokens('layers L3.1 and L4.0.sn1, section S6.5'), [])
check('names with underscores and ranges are not numbers', pm.number_tokens('the d_obj1..4 columns'), [])
check('confidence level before a math boundary', pm.number_tokens(r'$\pm 95\%$ CI $[0.02, 0.24]$'), ['0.02', '0.24'])
check('confidence level after a tie', pm.number_tokens(r'95\%~CI 29--39'), ['29', '39'])
check('a number right after a command', pm.number_tokens(r'$\approx0.5$'), ['0.5'])

# A second paper: one paragraph per line, an appendix after the bibliography, a section title with
# braces, a negative bound, sources that explain, disagree in words or cannot be opened.
PAPER2 = r"""\documentclass{article}
\begin{document}
\section{Results}
Layers L3.1 and L4.0.sn1 were probed, and section S6.5 lists the d_obj1..4 columns; the median $R^2$ was $-1.97$, far below zero, the drift stayed below $-0.1$, while 61 sessions entered the analysis and 7 permutations were run over 3 days in 2 rooms.

\subsection{Input-axis $R^2(Z \to X_\text{phys})$ per mouse}
The input-axis contrast fell in every mouse, with a mean slope of $0.128$ bits per day, $95\%$ CI $[0.02, 0.24]$; the estimator was a classifier.

\section{Discussion}
The fall of the input axis is a component of the compression claim, which we discuss here at length.
Compression is not universal across the systems we studied, and we hold to this claim throughout.
Where the input axis falls, the systems resemble each other more closely than anywhere else.

\bibliographystyle{plain}
\bibliography{refs}

\appendix
\setcounter{figure}{0}
\setcounter{table}{0}
\renewcommand{\thesection}{S\arabic{section}}
\renewcommand{\thesubsection}{S\arabic{section}.\arabic{subsection}}
\renewcommand{\thesubsubsection}{S\arabic{section}.\arabic{subsection}.\arabic{subsubsection}}

\section{Extra analyses}
In the appendix we report a further control with 12 shuffles and a held-out set of 300 trials, which is a claim about the work.

\begin{thebibliography}{9}
\bibitem{a} A. Author and B. Author. A title of a cited paper with many words in it. Journal 12, 2020.
\end{thebibliography}
\end{document}
"""

MAP2 = r"""paper:
  original: 'paper2.tex'
  file: 'paper2_anchored.tex'
  coverage_exclude: ['Extra analyses']
scopes:
  S_all: 'all sessions'
nodes:
  - id: DNA-comp
    kind: dna
    claim: 'compression is not universal'
    mentions: [{anchor: comp-d, quote: 'Compression is not universal across the systems we studied'}]
  - id: S-comp-input
    kind: statement
    claim: 'the input axis falls in every mouse'
    mentions: [{anchor: input-s, quote: 'The input-axis contrast fell in every mouse'}]
    supports:
      - {to: DNA-comp, says: 'first component: the input axis falls'}
      - {to: D-input, says: 'the Discussion reads the fall as part of the claim'}
  - id: D-input
    kind: discussion
    claim: 'the fall of the input axis is part of the compression claim'
    mentions: [{anchor: input-d, quote: 'The fall of the input axis is a component of the compression claim'}]
  - id: D-input2
    kind: discussion
    claim: 'where the input axis falls, the systems resemble each other'
    mentions: [{anchor: input-d2, quote: 'the systems resemble each other more closely than anywhere else'}]
    supports: [{to: S-comp-input, says: 'the resemblance is read as the same fall'}]
  - id: M-est
    kind: method
    claim: 'the estimator of the input axis'
    sources: [{file: 'data.txt', sha256: '%(data)s', locator: 'line 2', disagrees: 'the code uses KSG, not a classifier'}]
    mentions: [{anchor: est-m, quote: 'the estimator was a classifier'}]
  - id: R-slope
    kind: result
    claim: 'mean slope of the input axis per day'
    value: '0.128 [0.02, 0.24]'
    scope: S_all
    uses: [M-est]
    sources: [{file: 'data.txt', sha256: '%(data)s', locator: 'line 1', value: '0.128'}]
    mentions: [{anchor: slope-r, quote: 'a mean slope of $0.128$ bits per day, $95\%%$ CI $[0.02, 0.24]$', scope: S_all}]
    supports: [{to: S-comp-input, says: 'the slope is the fall'}]
  - id: P-ci
    kind: param
    claim: 'level of the confidence interval, percent'
    value: '95'
    sources: [{file: 'data.txt', sha256: '%(data)s', locator: 'line 6', value: '95'}]
    mentions: [{anchor: ci-p, quote: '$95\%%$ CI', states: '95'}]
  - id: R-expl
    kind: result
    claim: 'a value whose source entry carries an explanation'
    value: '0.128'
    sources: [{file: 'data.txt', sha256: '%(data)s', locator: 'line 1', value: '0.128 (SE 0.053)'}]
  - id: R-r2
    kind: result
    claim: 'median input-axis R2'
    value: '-1.97'
    scope: S_all
    sources: [{file: 'data.txt', sha256: '%(data)s', locator: 'line 5'}]
    mentions: [{anchor: r2-r, quote: 'the median $R^2$ was $-1.97$, far below zero', states: '0', verbal: true, bound: '<', scope: S_all}]
    supports: [{to: S-comp-input, says: 'the axis is far from fitting'}]
  - id: R-r2b
    kind: result
    claim: 'drift of the input axis'
    value: '-0.05'
    scope: S_all
    sources: [{file: 'data.txt', sha256: '%(data)s', locator: 'line 5'}]
    mentions: [{anchor: drift-r, quote: 'the drift stayed below $-0.1$', states: '-0.1', bound: '<', scope: S_all}]
    supports: [{to: S-comp-input, says: 'the drift is small'}]
  - id: R-sess
    kind: result
    claim: 'number of sessions analysed'
    value: '61'
    scope: S_all
    sources: [{unavailable: 'raw data outside the allowed folders', locator: 'session list'}]
    mentions: [{anchor: sess-r, quote: 'while 61 sessions entered the analysis', states: '61', scope: S_all}]
    supports: [{to: S-comp-input, says: 'every session counts'}]
  - id: P-run
    kind: param
    claim: 'duration of the permutation runs, days; its quote overlaps the next one'
    value: '3'
    mentions: [{anchor: run-p, quote: 'permutations were run over 3 days', states: '3'}]
  - id: P-perm
    kind: param
    claim: 'number of permutations'
    value: '7'
    sources: [{unavailable: 'library default, outside the allowed folders', locator: 'pkg/stats.py, line 40', value: '7'}]
    mentions: [{anchor: perm-p, quote: '7 permutations were run', states: '7'}]
  - id: P-folds
    kind: param
    claim: 'number of folds'
    value: '5'
    sources: [{file: 'data.txt', sha256: '%(data)s', locator: 'line 3: folds=5', value: '5'}]
  - id: P-shuffles
    kind: param
    claim: 'number of shuffles, set in the same call as the folds'
    value: '5'
    distinct_from: [P-folds]
    sources: [{file: 'data.txt', sha256: '%(data)s', locator: 'line 3: shuffles=5', value: '5'}]
  - id: R-count
    kind: result
    claim: 'a count whose source gives another count in the same words'
    value: '16 of 21'
    sources: [{file: 'data.txt', sha256: '%(data)s', locator: 'line 4', value: '15 of 21'}]
  - id: R-int
    kind: result
    claim: 'responding fraction with its interval'
    value: '34 [29, 39]'
    sources: [{file: 'data.txt', sha256: '%(data)s', locator: 'line 4', value: '34 [27, 41]'}]
"""

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    data = b'0.128\nKSG\nfolds=5, shuffles=5\n34\n-1.97\n95\n'
    (tmp / 'data.txt').write_bytes(data)
    (tmp / 'paper2.tex').write_text(PAPER2, encoding='utf-8', newline='')
    map2 = tmp / 'paper2.map.yaml'
    map2.write_text(MAP2 % {'data': hashlib.sha256(data).hexdigest()}, encoding='utf-8')
    code, out = run(pm.place_anchors, pm.Map(str(map2)))
    check('paper 2: every anchor is placed', code, 0)

    print('--- paper 2: text ---')
    tex2 = pm.Tex(str(tmp / 'paper2_anchored.tex'))
    sections = [sec for sec, _ in pm.paragraphs(tex2, [])]
    check('the appendix after the bibliography is scanned', 'Extra analyses' in sections, True)
    check('a section left out by coverage_exclude is not scanned',
          'Extra analyses' in [sec for sec, _ in pm.paragraphs(tex2, ['Extra analyses'])], False)
    check('the bibliography is not prose',
          any('bibitem' in line for _, blk in pm.paragraphs(tex2, []) for _, line in blk), False)
    check('definitions of counters and commands are not prose',
          any('renewcommand' in line for _, blk in pm.paragraphs(tex2, []) for _, line in blk), False)
    check('a section title keeps its braces', r'Input-axis $R^2(Z \to X_\text{phys})$ per mouse' in sections, True)

    print('--- paper 2: check ---')
    code, out = run(pm.check, pm.Map(str(map2)))
    check('paper 2: the map is clean', code, 0)
    check('a stated number the reading sets aside (an interval level) is still found in its quote',
          'P-ci (line 7): states' in out, False)
    check('a number outside every quote is listed even when its line has an anchor, '
          'and overlapping quotes both cover their numbers', 'Results, line 4: 2 |' in out, True)
    check('a negative value below a bound of zero is no mismatch', '[MISMATCH] R-r2 ' in out, False)
    check('a negative bound from states keeps its sign', '[MISMATCH] R-r2b' in out, True)
    check('the level of a confidence interval is not a stated number', '[MISMATCH] R-slope' in out, False)
    expl = [line for line in out.splitlines() if '[CONFLICT] R-expl' in line]
    check('an explanation in the value of a source is compared and named as such',
          bool(expl) and 'move it to the locator' in expl[0], True)
    count = [line for line in out.splitlines() if '[CONFLICT] R-count' in line]
    check('a conflict in the value itself is not blamed on an explanation',
          bool(count) and 'move it to the locator' not in count[0], True)
    check('an interval that differs from the source is a conflict', '[CONFLICT] R-int' in out, True)
    check('a source that disagrees in words is a conflict',
          '[CONFLICT] M-est' in out and 'the code uses KSG, not a classifier' in out, True)
    check('an unavailable source is no integrity error', 'source without file or commit' in out, False)
    check('a parameter whose source is unavailable has a source', 'P-perm: parameter without a source' in out, False)
    unsourced = [line for line in out.splitlines() if '[UNSOURCED] R-sess' in line]
    check('a result whose source is unavailable stays unsourced, with the reason',
          bool(unsourced) and 'raw data outside the allowed folders' in unsourced[0], True)
    check('parameters marked distinct are not warned about as one', 'P-folds and P-shuffles' in out, False)
    check('a Discussion position tied through a component is not loose',
          'Discussion positions tied to neither a main claim nor the literature: 0' in out, True)

    print('--- paper 2: argument page ---')
    page = pm.argument_page(pm.Map(str(map2)), 'en')
    claim_part = next(p for p in page.split('\n## ') if p.startswith('1. compression is not universal'))
    verdict = next(line for line in claim_part.splitlines() if line.startswith('**Verdict:**'))
    check('the verdict counts the findings against the data in its support',
          'against the data: 3 findings in its support' in verdict, True)
    check('the page shows the findings against the data under the claim', 'Against the data, in its support' in claim_part, True)
    check('a disagreement in words reaches the page', 'the code uses KSG, not a classifier' in claim_part, True)
    check('an unavailable source reaches the page', 'raw data outside the allowed folders' in claim_part, True)
    check('the page shows a Discussion position resting on a component',
          'the fall of the input axis is part of the compression claim' in claim_part, True)
    check('the page shows a Discussion position supporting a component',
          'where the input axis falls, the systems resemble each other' in claim_part, True)

    code, out = run(pm.impact, pm.Map(str(map2)), ['P-perm'])
    check('impact shows where an unavailable source sets the value', 'library default, outside the allowed folders' in out, True)

print('\nALL PASSED' if ok else '\nSOME FAILED')
sys.exit(0 if ok else 1)
