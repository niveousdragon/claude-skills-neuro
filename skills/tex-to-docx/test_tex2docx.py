"""Invariants that keep the preprocessing rules general rather than fitted to one
document. Each case here is a real way an earlier version corrupted a file.

Run: python test_tex2docx.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tex2docx import (convert_guillemets, uses_guillemet_ligature,
                      number_equations, needs_flattening,
                      materialise_nomenclature)

ok = True


def check(name, got, want):
    global ok
    good = got == want
    ok &= good
    print(f'[{"PASS" if good else "FAIL"}] {name}')
    if not good:
        print(f'        got : {got!r}\n        want: {want!r}')


print('--- guillemets must not touch math or code ---')
check('RU prose converted',
      convert_guillemets(r'Метод <<белого ящика>>.'),
      'Метод «белого ящика».')
check('inline math untouched',
      convert_guillemets(r'where $a << b$ holds'),
      r'where $a << b$ holds')
check('display math untouched',
      convert_guillemets(r'\begin{equation} a << b \end{equation}'),
      r'\begin{equation} a << b \end{equation}')
check('verb code untouched',
      convert_guillemets(r'\verb|cout << x| and <<цитата>>'),
      r'\verb|cout << x| and «цитата»')
check('lstlisting untouched',
      convert_guillemets('\\begin{lstlisting}\ncout << x;\n\\end{lstlisting}'),
      '\\begin{lstlisting}\ncout << x;\n\\end{lstlisting}')

print('\n--- language gate: only ligature languages ---')
check('russian babel detected',
      uses_guillemet_ligature(r'\usepackage[russian,english]{babel}'), True)
check('french detected',
      uses_guillemet_ligature(r'\usepackage[french]{babel}'), True)
check('english-only NOT detected',
      uses_guillemet_ligature(r'\usepackage[english]{babel}'), False)
check('no babel NOT detected',
      uses_guillemet_ligature(r'\documentclass{article}'), False)

print('\n--- equation numbering beyond plain `equation` ---')
out = number_equations(r'see \eqref{eq:a}' + '\n'
                       r'\begin{equation}E=mc^2\label{eq:a}\end{equation}')
check('equation numbered + ref resolved', '(1)' in out and '[eq:a]' not in out, True)

out = number_equations(r'see \eqref{eq:b}' + '\n'
                       r'\begin{align}x&=1\\ y&=2\label{eq:b}\end{align}')
check('align: 2nd row is (2), ref resolves to it',
      '(2)' in out and 'see (2)' in out, True)

out = number_equations(r'\begin{equation*}E=mc^2\end{equation*}')
check('starred equation NOT numbered', '\\qquad(' not in out, True)

out = number_equations(r'\begin{align}x&=1\nonumber\\ y&=2\label{eq:c}\end{align}'
                       + r'ref \eqref{eq:c}')
check('\\nonumber row skipped, next row is (1)', 'ref (1)' in out, True)

print('\n--- package-generated content must be materialised ---')
src = r'\renewcommand{\nomname}{Список сокращений}'
out = materialise_nomenclature(
    r'\nomenclature[A GCMI]{GCMI}{Gaussian Copula MI}'
    r'\nomenclature[A z_01]{ВИ}{взаимная информация}'
    r'\printnomenclature[3.5cm]', src)
check('entries survive \\printnomenclature',
      'GCMI' in out and 'взаимная информация' in out, True)
check('heading taken from \\nomname', 'Список сокращений' in out, True)
check('sorted by the LaTeX sort key (GCMI before ВИ)',
      out.index('GCMI') < out.index('ВИ'), True)
check('raw \\nomenclature commands removed', '\\nomenclature' not in out, True)

print('\n--- flatten auto-detection ---')
check('thesis (preamble \\input + body \\include) -> flatten',
      needs_flattening(r'\documentclass{memoir}'
                       '\n\\input{common/setup}\n'
                       r'\begin{document}\include{ch1}\end{document}'), True)
check('single-file paper -> no flatten',
      needs_flattening(r'\documentclass{article}\usepackage{graphicx}'
                       r'\begin{document}Hello \cite{x}\end{document}'), False)

print('\nALL PASS' if ok else '\nSOME FAILED')
sys.exit(0 if ok else 1)
