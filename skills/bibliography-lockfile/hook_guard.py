# -*- coding: utf-8 -*-
"""Claude Code PreToolUse hook: blocks direct edits to .bib files.

The bibliography is a generated artifact (see the bibliography-lockfile skill).
The harness runs this on every Write/Edit BEFORE it is applied; exit 2 = block,
stderr is returned to the model as the explanation. Non-bib files pass instantly.
"""
import json
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # not our payload — do not interfere
    tool_input = data.get('tool_input') or {}
    path = str(tool_input.get('file_path') or tool_input.get('notebook_path') or '')
    if not path.lower().endswith('.bib'):
        return 0
    sys.stderr.write(
        'BLOCKED by bibliography-lockfile policy: .bib files are GENERATED, never '
        'edited by hand.\n'
        'To add or change a reference:\n'
        '  1. edit tools/bibgen/sources.yaml (add a doi:/arxiv:/pmlr:/openalex_title: entry);\n'
        '  2. run: python tools/bibgen/bibgen.py\n'
        '  3. copy tools/bibgen/refs.generated.bib over the target .bib.\n'
        'Author names must NEVER be typed or expanded from initials by hand or from '
        'memory; a manual author field requires authors_override with a verified: '
        'stamp in sources.yaml. Hand-written entries are how fabricated co-author '
        'names end up in submitted papers and get flagged by venue citation checkers.\n')
    return 2


if __name__ == '__main__':
    sys.exit(main())
