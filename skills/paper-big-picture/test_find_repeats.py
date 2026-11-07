"""Tests for find_repeats.py. Run: python test_find_repeats.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_repeats import find_repeats  # noqa: E402

CLAIM = "compression emerged only in the layers where the task structure demands it"


def main():
    failed = 0

    def check(why, got, want):
        nonlocal failed
        if got != want:
            failed += 1
            print(f"[FAILED] {why}: expected {want!r}, got {got!r}")

    tex = ("\\begin{document}\n"
           "\\begin{abstract}We show that " + CLAIM + ".\\end{abstract}\n"
           "\\section{Results}Relevance rose in every mouse \\citep{a2020}.\n"
           "% " + CLAIM + "\n"
           "\\section{Discussion}As in the network, " + CLAIM + " \\citep{b2021}.\n"
           "Relevance rose in every mouse.\n"
           "\\begin{thebibliography}\\bibitem{x} " + CLAIM + "\\end{thebibliography}\n"
           "\\end{document}\n")
    found = find_repeats(tex)
    check("one repeated claim, comment and bibliography ignored", len(found), 1)
    if found:
        check("the whole repeated phrase", found[0][0], CLAIM)
        check("lines of both occurrences", found[0][1], [2, 5])

    short = ("\\begin{document}Relevance rose in every mouse. Later, relevance rose in every "
             "mouse again.\\end{document}")
    check("phrases under eight words are not reported", find_repeats(short), [])

    cites = ("\\begin{document}The estimator \\citep{a} is unbiased for Gaussian variables "
             "at any sample size.\n\nThe estimator \\citep{b, c} is unbiased for Gaussian "
             "variables at any sample size.\\end{document}")
    check("different citations do not hide a repeat", len(find_repeats(cites)), 1)

    maths = ("\\begin{document}In the deepest layer $I(Z;Y)$ kept rising after compression "
             "began.\n\nIn the deepest layer $I( Z ; Y )$ kept rising after compression "
             "began.\\end{document}")
    check("a formula is one word, spacing ignored", len(find_repeats(maths)), 1)

    reworded = ("\\begin{document}\nAcross all three systems, we observed coherent motion along "
                "the relevance axis with learning, while compression was not universal.\n"
                "Across all three systems, we observed coherent motion along the relevance "
                "axis with learning, while compression was not universal.\n"
                "Thus we observed coherent motion along the relevance axis with learning in "
                "all three systems, while compression was not universal.\\end{document}")
    found = find_repeats(reworded)
    check("an occurrence reworded at its edges joins the same phrase",
          [f[1] for f in found], [[2, 3, 4]])

    if failed:
        print(f"{failed} FAILED")
        return 1
    print("ALL PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
