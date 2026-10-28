"""Tests for count_numbers.py. Run: python test_count_numbers.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from count_numbers import count_numbers, report  # noqa: E402

CASES = [
    # (text, expected number count, why)
    ("INTENSE labelled 5{,}365 cells and the classic method 6{,}531.", 2, "thousands separators"),
    ("Jaccard index 0.28 ($p < 0.001$).", 2, "decimals and a p-value"),
    ("better in 27 of 29~sessions", 2, "a count out of a total"),
    ("at $p < 10^{-5}$", 1, "a power of ten is one number"),
    ("Stage 1 screens pairs; Stage 2 validates them.", 0, "stage labels"),
    ("the F1 score and CA1 neurons", 0, "identifiers with digits"),
    ("$F_1 = 0.85$ and $R^2 = 0.62$", 2, "sub- and superscripts are names"),
    ("(Fig. 2c; Figure 3, Table 1, Section 4.2)", 0, "figure, table and section labels"),
    ("Supplementary Fig. S4 and Extended Data Fig. 1", 0, "supplementary labels"),
    ("as shown before \\cite{smith2020} in 2019", 1, "citations removed, a bare year counts"),
    ("see Fig.~\\ref{fig:a}", 0, "references removed"),
    ("DRIADA v1.2.2 was used", 0, "version strings"),
    ("held-out $R^2$ was $-0.08$", 1, "negative value, R^2 is a name"),
    ("traces sampled at 30 Hz for 20 min", 2, "values with units"),
    ("% 12 34 a comment\nno numbers here", 0, "LaTeX comments"),
    ("A quarter of neuron-sessions were selective, one in six of them to two variables.", 2,
     "verbal fractions are numbers too"),
    ("Nine in ten pairs passed; one pair in ten reached Stage 2.", 2, "N in M in words"),
    ("nearly half of the cells and two thirds of the sessions", 2, "half, thirds"),
    ("about a third of the mice", 1, "a qualified fraction counts once"),
    ("in the first half of the session, a third variable", 0, "half and third as names"),
    ("the majority of pairs", 0, "majority is not a quantity"),
]


def main():
    failed = 0
    for text, want, why in CASES:
        got = count_numbers(text)
        if got != want:
            failed += 1
            print(f"[FAILED] {why}: expected {want}, got {got}: {text!r}")
    tex = ("\\begin{document}\\section{Results}Of 30{,}105 cells, 7{,}414 were selective "
           "(Fig. 2a).\\begin{figure}\\caption{Accepted pairs (9{,}009) in green.}\\end{figure}"
           "\\section{Discussion}The method works.\\end{document}")
    rows = {r[0]: r for r in report(tex)}
    if rows["Results"][2] != 2 or rows["Captions"][2] != 1 or rows["Discussion"][2] != 0:
        failed += 1
        print(f"[FAILED] sections and captions split: {rows}")
    if failed:
        print(f"{failed} FAILED")
        return 1
    print("ALL PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
