#!/usr/bin/env python3
"""
extract_copy.py — list every user-facing message (react-intl defaultMessage) in the given files,
so UI copy can be reviewed against the content style guide. Covers .ts as well as .tsx: validators,
hooks, and config objects often hold user-facing strings.

Usage:
    python3 extract_copy.py <path> [<path> ...] [--diff <patch>] [--json]

With --diff, each message is marked in_diff (on a line the patch adds) or pre-existing.
"""
import json
import os
import re
import sys

sys.dont_write_bytecode = True  # keep the skill folder clean
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from custom_styling_check import parse_added_lines, should_skip  # noqa: E402

MSG = re.compile(r"""defaultMessage\s*[:=]\s*\{?\s*(?P<q>['"`])(?P<text>(?:\\.|(?!(?P=q)).)*?)(?P=q)""", re.DOTALL)
DESC = re.compile(r"""description\s*[:=]\s*\{?\s*(?P<q>['"`])(?P<text>(?:\\.|(?!(?P=q)).)*?)(?P=q)""", re.DOTALL)


def unescape(text: str) -> str:
    return re.sub(r"\\(['\"`])", r'\1', text)


def files_under(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for d, _, fs in os.walk(p):
            for f in sorted(fs):
                full = os.path.join(d, f)
                if f.endswith(('.ts', '.tsx')) and not should_skip(full):
                    yield full


def main():
    args = sys.argv[1:]
    as_json = '--json' in args
    diff = None
    if '--diff' in args:
        i = args.index('--diff')
        diff = parse_added_lines(args[i + 1])
        args = args[:i] + args[i + 2:]
    paths = [a for a in args if not a.startswith('--')]
    missing = [p for p in paths if not os.path.exists(p)]
    if not paths or missing:
        print(f'error: path not found: {", ".join(missing) or "(none given)"}', file=sys.stderr)
        sys.exit(2)

    out = []
    for f in files_under(paths):
        src = open(f, encoding='utf-8', errors='replace').read()
        for m in MSG.finditer(src):
            line = src.count('\n', 0, m.start()) + 1
            d = DESC.search(src, m.end(), m.end() + 400)
            in_diff = None
            if diff is not None:
                norm = f.replace(os.sep, '/')
                key = next((k for k in diff if norm.endswith('/' + k) or norm == k), None)
                in_diff = bool(key and line in diff[key])
            out.append({'file': f, 'line': line, 'text': unescape(' '.join(m.group('text').split())),
                        'description': ' '.join(d.group('text').split()) if d else '', 'in_diff': in_diff})

    if as_json:
        print(json.dumps(out, indent=2))
        return
    print(f'{len(out)} message(s)' + (f', {sum(1 for o in out if o["in_diff"])} added by this change' if diff else ''))
    for o in out:
        tag = '' if o['in_diff'] is not False else '  (pre-existing)'
        print(f'{o["file"]}:{o["line"]}{tag}\n  "{o["text"]}"' + (f'\n  ↳ {o["description"]}' if o['description'] else ''))


if __name__ == '__main__':
    main()
