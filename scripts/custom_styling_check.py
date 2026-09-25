#!/usr/bin/env python3
"""
custom_styling_check.py — detect hand-rolled visual structure that should use GRC components.

Usage:
    python3 custom_styling_check.py <path> [<path> ...]                 # files and/or directories
    python3 custom_styling_check.py <path> [<path> ...] --json          # machine-readable output
    python3 custom_styling_check.py <path> ... --diff <patch>           # tag findings introduced vs pre-existing
    python3 custom_styling_check.py <path> ... --diff <patch> --changed-only   # report only lines the patch adds

    python3 custom_styling_check.py <path> ... --docs <work_dir>        # verify rule sources + load MANIFEST deprecations
    python3 custom_styling_check.py --docs <work_dir> --rules           # print rule sources / disabled checks / deprecations

With --diff, each finding is marked in_diff (on a line the patch adds) or pre-existing, and the
exit code only counts in-diff violations.

Exit code 1 if any violations found (useful for CI).
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

# ── Configuration ─────────────────────────────────────────────────────────────

# sx properties that signal visual structure (not layout)
STRUCTURAL_PROPS = {
    'backgroundColor', 'bgcolor', 'background',
    'border', 'borderColor', 'borderTop', 'borderBottom', 'borderLeft', 'borderRight',
    'borderTopColor', 'borderBottomColor', 'borderLeftColor', 'borderRightColor',
    'borderRadius', 'borderTopLeftRadius', 'borderTopRightRadius',
    'borderBottomLeftRadius', 'borderBottomRightRadius',
    'outline', 'outlineColor',
    'boxShadow', 'filter',
}

# Non-GRC elements to check for sx accumulation
TARGET_ELEMENTS = {'Box', 'Paper', 'Stack', 'div', 'span', 'section', 'article', 'main', 'aside'}

# GRC components that should NOT be double-wrapped with styled()
GRC_COMPONENTS = {
    'GrcPage', 'GrcPageSection', 'GrcPageSectionContent', 'GrcPageSectionPrimaryAction',
    'GrcTabs', 'GrcCardCallout', 'GrcDetailsPageLayout', 'GrcFixedPageLayout',
    'GrcCondensedPageHeader', 'GrcBreadcrumbs', 'GrcLabeledValue',
    'GrcExperienceIcon', 'GrcPageTitle', 'GrcPageActions', 'GrcAiBadge', 'GrcChip',
}

# Threshold: number of structural sx props on a single element to flag
CONCERN_THRESHOLD = 3   # 🟡
VIOLATION_THRESHOLD = 4  # 🔴

# Named anti-patterns: (primary_props, required_also, label, suggestion)
ANTI_PATTERNS = [
    (
        {'backgroundColor', 'bgcolor', 'background'},
        {'borderRadius'},
        'background + borderRadius',
        'GrcPageSection + GrcPageSectionContent for a section container, '
        'or a new Bucket D card primitive in packages/component-library/',
    ),
    (
        {'border', 'borderColor', 'borderTop', 'borderBottom', 'borderLeft', 'borderRight'},
        {'borderRadius', 'backgroundColor', 'bgcolor'},
        'border + borderRadius/background',
        'A card primitive from packages/component-library/ (Bucket D candidate). '
        'File a component library ticket rather than shipping this inline.',
    ),
    (
        {'boxShadow', 'filter'},
        {'backgroundColor', 'bgcolor', 'background'},
        'shadow + background on a surface',
        'Elevation should reinforce container structure, not replace it. '
        'Use the layered-container model (background tone + radius) first; '
        'elevation only on cards/tooltips/menus/dialogs.',
    ),
]

# GRC alternative lookup by element + pattern
GRC_SUGGESTIONS = {
    'background + borderRadius': 'GrcPageSection + GrcPageSectionContent',
    'border + borderRadius/background': 'card primitive from component-library (Bucket D)',
    'shadow + background on a surface': 'layered-container model without elevation',
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    file: str
    line: int
    severity: str        # 'violation' | 'concern'
    element: str
    message: str
    suggestion: Optional[str] = None
    check: str = ''      # which check produced this
    in_diff: Optional[bool] = None  # None = no --diff given
    source: str = ''     # the doc rule backing this check


# ── Parsing helpers ───────────────────────────────────────────────────────────

def extract_brace_content(text: str, open_pos: int) -> tuple[str, int]:
    """
    Given text and a position pointing at '{', return (content, end_pos).
    Handles nested braces and quoted strings.
    """
    assert text[open_pos] == '{'
    depth = 0
    i = open_pos
    in_single = False
    in_double = False
    in_template = False
    while i < len(text):
        c = text[i]
        if in_single:
            if c == '\\':
                i += 2
                continue
            if c == "'":
                in_single = False
        elif in_double:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                in_double = False
        elif in_template:
            if c == '\\':
                i += 2
                continue
            if c == '`':
                in_template = False
        else:
            if c == "'":
                in_single = True
            elif c == '"':
                in_double = True
            elif c == '`':
                in_template = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return text[open_pos:i + 1], i
        i += 1
    return text[open_pos:], len(text) - 1


def line_number_at(text: str, pos: int) -> int:
    """Return 1-indexed line number for a position in text."""
    return text[:pos].count('\n') + 1


def preceding_tag_name(text: str, sx_pos: int) -> Optional[str]:
    """
    Search backwards from sx_pos to find the JSX element name this sx belongs to.
    Looks for the most recent '<TagName' that hasn't been closed.
    """
    snippet = text[max(0, sx_pos - 400):sx_pos]
    # Find all tag openings in the snippet
    matches = list(re.finditer(r'<([A-Za-z][A-Za-z0-9.]*)', snippet))
    if not matches:
        return None
    # Return the last one found
    return matches[-1].group(1)


def get_top_level_prop_names(obj_content: str) -> set[str]:
    """
    Extract top-level property names from an sx object literal.
    Skips pseudo-selector keys like '&:hover', '&.Mui-disabled', etc.
    Only counts depth-1 properties (not nested inside pseudo-selectors).
    """
    props = set()
    # Strip outer braces
    inner = obj_content.strip()
    if inner.startswith('{') and inner.endswith('}'):
        inner = inner[1:-1]

    depth = 0
    i = 0
    in_single = False
    in_double = False
    in_template = False
    token_start = None

    while i < len(inner):
        c = inner[i]

        if in_single:
            if c == '\\':
                i += 2
                continue
            if c == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                in_double = False
            i += 1
            continue
        if in_template:
            if c == '\\':
                i += 2
                continue
            if c == '`':
                in_template = False
            i += 1
            continue

        if c == "'":
            in_single = True
        elif c == '"':
            in_double = True
        elif c == '`':
            in_template = True
        elif c in ('{', '[', '('):
            depth += 1
            token_start = None
        elif c in ('}', ']', ')'):
            depth -= 1
            token_start = None
        elif depth == 0:
            if c.isalpha() or c == '_':
                if token_start is None:
                    token_start = i
            elif c == ':' and token_start is not None:
                prop = inner[token_start:i].strip()
                # Skip pseudo-selectors and computed keys
                if prop and not prop.startswith('&') and not prop.startswith('['):
                    props.add(prop)
                token_start = None
            elif not (c.isalnum() or c in ('_', ' ', '\n', '\r', '\t')):
                token_start = None
        else:
            token_start = None

        i += 1

    return props


# ── Check implementations ─────────────────────────────────────────────────────

LAYOUT_ONLY_PROPS = {
    'left', 'right', 'top', 'bottom', 'width', 'height', 'minWidth', 'minHeight', 'maxWidth', 'maxHeight',
    'position', 'transform', 'display', 'flex', 'flexBasis', 'gridColumn', 'gridRow', 'zIndex', 'inset',
}


MAGIC_PROPS = {'borderRadius', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing'}


def check_magic_numbers(source: str, filepath: str) -> list[Finding]:
    """Literal radius/typography values in sx or style objects. DESIGN.md → Design values: Token-driven."""
    findings = []
    for m in re.finditer(r'(?<![a-zA-Z-])(?:sx|style)=\{', source):
        obj_start = m.end()
        if obj_start >= len(source) or source[obj_start] != '{':
            continue
        obj_text, _ = extract_brace_content(source, obj_start)
        base = line_number_at(source, obj_start)
        for pm in re.finditer(r"""\b(""" + '|'.join(MAGIC_PROPS) + r""")\s*:\s*(\d+(?:\.\d+)?|['"`]\d+(?:\.\d+)?(?:px|rem|em)?['"`])""", obj_text):
            findings.append(Finding(
                file=filepath, line=base + obj_text[:pm.start()].count('\n'), severity='violation',
                element='(magic number)', message=f'`{pm.group(1)}: {pm.group(2)}` is a hard-coded value.',
                suggestion="Use getToken('radius/…') or a typography variant/token instead.",
                check='magic-number',
            ))
    return findings


def check_styled_wrappers(source: str, filepath: str) -> list[Finding]:
    """Flag styled() wrapping a GRC component."""
    findings = []
    for m in re.finditer(r'\bstyled\(([A-Za-z][A-Za-z0-9]*)\)', source):
        component = m.group(1)
        if component in GRC_COMPONENTS:
            line = line_number_at(source, m.start())
            findings.append(Finding(
                file=filepath,
                line=line,
                severity='concern',
                element=f'styled({component})',
                message=(
                    f'`styled({component})` double-wraps a GRC component. '
                    f'GRC components expose `sx` and `slotProps` for customisation — '
                    f'a wrapper creates a second API surface and hides Unify improvements.'
                ),
                suggestion=f'Use the `sx` prop on `{component}` directly, or propose a new prop on the component.',
                check='styled-wrapper',
            ))
    return findings


def check_multiple_primary_buttons(source: str, filepath: str) -> list[Finding]:
    """Flag files with many variant='contained' buttons — suggests competing primary actions (DESIGN.md → One primary per surface)."""
    matches = []
    for m in re.finditer(r"""variant\s*=\s*(?:"contained"|'contained'|\{['"]contained['"]\})""", source):
        line_start = source.rfind('\n', 0, m.start()) + 1
        if source[line_start:m.start()].lstrip().startswith(('//', '*', '/*')):
            continue  # in a comment
        tag = preceding_tag_name(source, m.start()) or ''
        if not tag.endswith('Button'):
            continue  # e.g. GrcDataGrid / Chip variants
        matches.append(m)
    if len(matches) < 3:
        return []
    lines = sorted(set(line_number_at(source, m.start()) for m in matches))
    severity = 'violation' if len(matches) >= 5 else 'concern'
    return [Finding(
        file=filepath,
        line=lines[0],
        severity=severity,
        element='Button',
        message=(
            f'Found {len(matches)} `variant="contained"` (primary) buttons in this file '
            f'(lines {", ".join(map(str, lines))}). '
            f'Each rendered surface should have at most one primary action simultaneously visible.'
        ),
        suggestion=(
            'Demote secondary actions to `variant="outlined"` (secondary) or `variant="text"` (ghost/cancel). '
            'If they sit on different surfaces (separate dialogs, stepper steps, exclusive branches), this is a false positive — drop it.'
        ),
        check='multiple-primary-buttons',
    )]


COLOR_KEYS = r'(?:color|bgcolor|backgroundColor|background|borderColor|border|borderTop|borderBottom|borderLeft|borderRight|outline|outlineColor|fill|stroke|boxShadow)'
THEME_STRING = r"(?:(?:primary|secondary|error|warning|info|success|text|background|grey|action|common)\.[A-Za-z0-9]+|divider)"


def check_colors(source: str, filepath: str) -> list[Finding]:
    """Raw hex/rgb/hsl colors and MUI theme strings used as CSS values inside sx/style objects."""
    findings = []
    for m in re.finditer(r'(?<![a-zA-Z-])(?:sx|style)=\{', source):
        obj_start = m.end()
        if obj_start >= len(source) or source[obj_start] != '{':
            continue
        obj_text, _ = extract_brace_content(source, obj_start)
        base = line_number_at(source, obj_start)
        for cm in re.finditer(r"""(['"`][^'"`]*?)(#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\()""", obj_text):
            findings.append(Finding(
                file=filepath, line=base + obj_text[:cm.start()].count('\n'), severity='violation',
                element='(color)', message=f'Raw color `{cm.group(2)}` as a CSS value.',
                suggestion="Use getToken('<semantic token>'); add one to theme/tokens/semantic.ts if none fits.",
                check='raw-color',
            ))
        for cm in re.finditer(COLOR_KEYS + r"""\s*:\s*['"](""" + THEME_STRING + r""")['"]""", obj_text):
            findings.append(Finding(
                file=filepath, line=base + obj_text[:cm.start()].count('\n'), severity='violation',
                element='(color)', message=f"MUI theme string `'{cm.group(1)}'` used as a CSS color value.",
                suggestion="Use getToken('<semantic token>'). Theme strings are only OK as component color props (e.g. <Button color=\"error\">).",
                check='theme-string-color',
            ))
    return findings


def check_dialog_dismissal(source: str, filepath: str) -> list[Finding]:
    """Dialogs with no onClose (Esc does nothing) or disableEscapeKeyDown. DESIGN.md → Dialog dismissal."""
    findings = []
    for m in re.finditer(r'<Dialog\b', source):
        end = source.find('>', m.end())
        # skip over => inside the tag (arrow functions in props)
        while end != -1 and source[end - 1] == '=':
            end = source.find('>', end + 1)
        tag = source[m.start():end if end != -1 else m.start() + 400]
        line = line_number_at(source, m.start())
        if 'disableEscapeKeyDown' in tag:
            msg = '`disableEscapeKeyDown` — Esc must be supported on dialogs.'
        elif not re.search(r'\bonClose\s*=', tag) and not re.search(r'\{\s*\.\.\.', tag):
            msg = 'No `onClose`, so Esc does nothing.'
        else:
            continue
        findings.append(Finding(
            file=filepath, line=line, severity='concern', element='Dialog', message=msg,
            suggestion="Pass onClose that ignores 'backdropClick' but handles Esc (with an 'are you sure' guard once the user has typed).",
            check='dialog-dismissal',
        ))
    return findings


def check_gettoken_source(source: str, filepath: str) -> list[Finding]:
    """getToken imported from @workiva/unify — the component library's getToken is preferred (AGENTS.md → Design Tokens)."""
    findings = []
    for m in re.finditer(r"import\s*\{[^}]*\bgetToken\b[^}]*\}\s*from\s*['\"]@workiva/unify['\"]", source):
        findings.append(Finding(
            file=filepath, line=line_number_at(source, m.start()), severity='concern', element='getToken',
            message='`getToken` imported from `@workiva/unify`.',
            suggestion="Import it from '@workiva/ts-grc-component-library' (preferred; resolves GRC semantic tokens).",
            check='gettoken-source',
        ))
    return findings


def check_token_names(source: str, filepath: str) -> list[Finding]:
    """getToken('x') where x isn't in the live semantic catalog, or is marked @deprecated there.
    Legacy namespaces (Core/*, GRC/*) come from Unify and aren't in semantic.ts, so they're skipped."""
    if not TOKENS:
        return []
    findings = []
    for m in re.finditer(r"""getToken\(\s*['"]([^'"]+)['"]""", source):
        name = m.group(1)
        if not name[:1].islower():
            continue
        line = line_number_at(source, m.start())
        if name not in TOKENS:
            close = [t for t in TOKENS if t.split('/')[0] == name.split('/')[0]][:6]
            findings.append(Finding(
                file=filepath, line=line, severity='violation', element='getToken',
                message=f"Unknown token '{name}' — not in the semantic token catalog.",
                suggestion='Existing tokens in this group: ' + (', '.join(close) if close else '(none)') +
                           '. If none fits, add one to semantic.ts.',
                check='unknown-token', source=TOKEN_SOURCE,
            ))
        elif TOKENS[name]:
            findings.append(Finding(
                file=filepath, line=line, severity='concern', element='getToken',
                message=f"Token '{name}' is @deprecated: {TOKENS[name]}",
                suggestion='Use the replacement named in semantic.ts, or ask UX.',
                check='deprecated-token', source=TOKEN_SOURCE,
            ))
    return findings


def check_mui_imports(source: str, filepath: str) -> list[Finding]:
    """Flag direct @mui imports — everything must come from @workiva/unify."""
    findings = []
    for m in re.finditer(r"""from\s+['"](@mui/(?:material|icons-material)[^'"]*)['"]""", source):
        findings.append(Finding(
            file=filepath,
            line=line_number_at(source, m.start()),
            severity='violation',
            element=m.group(1),
            message=f'Direct `{m.group(1)}` import — MUI components and icons must come from `@workiva/unify`.',
            suggestion='Import from `@workiva/unify` (components) or `@workiva/unify/UnifyIcons` (icons).',
            check='mui-import',
        ))
    return findings


# ── Doc-derived rules ─────────────────────────────────────────────────────────
# Every check that enforces a written GRC rule cites the exact phrase it relies on. With --docs, the
# scanner verifies each phrase still exists in the freshly fetched docs and DISABLES any check whose
# source rule has changed or disappeared, so the scanner can never enforce a rule the docs dropped.
# Every check is doc-backed: either listed here, or derived at runtime (MANIFEST deprecations, token catalog).
RULE_SOURCES = {
    'mui-import': ('packages/component-library/DESIGN.md',
                   'Always import MUI components and icons from `@workiva/unify`'),
    'raw-color': ('documentation/DESIGN.md', 'No raw hex, no MUI theme strings'),
    'theme-string-color': ('AGENTS.design-tokens.md', 'never use raw MUI theme strings'),
    'gettoken-source': ('AGENTS.design-tokens.md', '`@workiva/ts-grc-component-library` (preferred)'),
    'dialog-dismissal': ('documentation/DESIGN.md', '**Esc key** — supported'),
    'multiple-primary-buttons': ('documentation/DESIGN.md', '**One primary per surface.**'),
    'nested-container': ('packages/component-library/DESIGN.md', '**Sections and surfaces do NOT get borders.**'),
    'styled-wrapper': ('packages/component-library/DESIGN.md', 'Wrapper proliferation is expensive'),
    'magic-number': ('documentation/DESIGN.md', 'CSS colors, spacing, radii, and typography come from `getToken()`'),
}

DEPRECATED: list[dict] = []   # filled from MANIFESTs by load_docs()
TOKENS: dict[str, str] = {}   # semantic token name -> '' or deprecation note, from semantic.ts
TOKEN_SOURCE = 'packages/component-library/src/theme/tokens/semantic.ts'
DISABLED: dict[str, str] = {}  # check -> reason, filled by load_docs()


def load_docs(work: str) -> list[str]:
    """Verify RULE_SOURCES against fetched docs and derive deprecations from MANIFESTs. Returns notes."""
    notes = []
    for check, (rel, phrase) in RULE_SOURCES.items():
        path = os.path.join(work, rel)
        text = open(path, encoding='utf-8').read() if os.path.isfile(path) else ''
        if phrase not in text:
            DISABLED[check] = f'source rule not found in {rel}: "{phrase}"'
            notes.append(f'check `{check}` DISABLED — {DISABLED[check]}')
    mdir = os.path.join(work, 'packages/component-library/src')
    for dirpath, _, files in os.walk(mdir):
        for fn in files:
            if not fn.endswith('.MANIFEST.md'):
                continue
            component = fn[:-len('.MANIFEST.md')]
            rel = os.path.relpath(os.path.join(dirpath, fn), work)
            lines = open(os.path.join(dirpath, fn), encoding='utf-8').read().splitlines()
            if any(re.match(r'status:\s*deprecated\b', l.strip()) for l in lines[:15]):
                DEPRECATED.append({'component': component, 'prop': None, 'severity': 'concern',
                                   'source': f'{rel} (status: deprecated)', 'text': 'Component is deprecated.'})
            for n, line in enumerate(lines, 1):
                for m in re.finditer(r'`([a-z][A-Za-z0-9]*)`', line):
                    after, before = line[m.end():m.end() + 30].lower(), line[max(0, m.start() - 20):m.start()].lower()
                    if re.search(r'deprecated|removed|ignored', after) or re.search(r"don't use|do not use", before):
                        rule = re.sub(r'^[-*\s]+', '', line).strip()
                        DEPRECATED.append({
                            'component': component, 'prop': m.group(1),
                            'severity': 'violation' if re.match(r"(\*\*)?(don't|do not)", rule.lower()) else 'concern',
                            'source': f'{rel}:{n}', 'text': rule[:160],
                        })
    tok_path = os.path.join(work, 'tokens', 'semantic.ts')
    if os.path.isfile(tok_path):
        pending = None  # deprecation note waiting for the next key
        in_doc = False
        for line in open(tok_path, encoding='utf-8').read().splitlines():
            st = line.strip()
            if st.startswith('/**'):
                in_doc = True
            if in_doc and '@deprecated' in st:
                pending = re.sub(r'.*@deprecated\s*', '', st).rstrip('*/ ').strip() or 'deprecated'
            if in_doc and st.endswith('*/'):
                in_doc = False
                continue
            m = re.match(r"\s*'([a-z][^']*)'\s*:", line)
            if m:
                TOKENS[m.group(1)] = pending or ''
                pending = None
        deprecated_count = sum(1 for v in TOKENS.values() if v)
        notes.append(f'{len(TOKENS)} semantic tokens loaded ({deprecated_count} deprecated)')
    else:
        notes.append('token catalog not loaded: unknown/deprecated token names not checked')
    notes.append(f'{len(DEPRECATED)} deprecation(s) derived from MANIFESTs: ' +
                 ', '.join(f"{d['component']}{'.' + d['prop'] if d['prop'] else ''}" for d in DEPRECATED))
    return notes


def check_deprecated_props(source: str, filepath: str) -> list[Finding]:
    """Deprecated components/props, derived at runtime from component MANIFESTs (requires --docs)."""
    findings = []
    for d in DEPRECATED:
        pattern = (rf'<{d["component"]}\b[^>]*?\b{d["prop"]}\b' if d['prop'] else rf'<{d["component"]}\b(?![A-Za-z])')
        for m in re.finditer(pattern, source, re.DOTALL):
            what = f'`{d["prop"]}` on `{d["component"]}`' if d['prop'] else f'`{d["component"]}`'
            findings.append(Finding(
                file=filepath, line=line_number_at(source, m.end()), severity=d['severity'],
                element=d['component'], message=f'{what} is deprecated per its MANIFEST: "{d["text"]}"',
                suggestion=f'See {d["source"]}.', check='deprecated-prop',
            ))
    return findings



def check_nested_container_pattern(source: str, filepath: str) -> list[Finding]:
    """
    Outer Box/Paper/Stack whose own sx sets a background, wrapping (within 10 lines) an inner one whose
    own sx sets border + borderRadius — the layered-container-by-hand smell.
    """
    boxes = []
    for m in re.finditer(r'\bsx=\{', source):
        obj_start = m.end()
        if obj_start >= len(source) or source[obj_start] != '{':
            continue
        element = preceding_tag_name(source, m.start())
        if element not in ('Box', 'Paper', 'Stack'):
            continue
        obj_text, _ = extract_brace_content(source, obj_start)
        props = get_top_level_prop_names(obj_text)
        boxes.append((line_number_at(source, m.start()), element, props))
    findings = []
    for i, (line, element, props) in enumerate(boxes):
        if not props & {'bgcolor', 'backgroundColor', 'background'}:
            continue
        for inner_line, inner_el, inner_props in boxes[i + 1:]:
            if inner_line - line > 10:
                break
            if inner_props & {'border', 'borderColor'} and 'borderRadius' in inner_props:
                findings.append(Finding(
                    file=filepath, line=line, severity='concern', element=element,
                    message=(f'Outer `{element}` (background) wraps inner `{inner_el}` (border + borderRadius, line {inner_line}) '
                             f'— the layered-container-by-hand pattern.'),
                    suggestion='GrcPageSection (outer) + GrcPageSectionContent (inner), or a card primitive.',
                    check='nested-container',
                ))
                break
    return findings


# ── Scanner ───────────────────────────────────────────────────────────────────

SKIP_PATTERNS = {'.test.', '.spec.', '.stories.', '__generated__', '.d.ts'}

def should_skip(filename: str) -> bool:
    return any(p in filename for p in SKIP_PATTERNS)


def scan_file(filepath: str) -> list[Finding]:
    try:
        with open(filepath, encoding='utf-8') as f:
            source = f.read()
    except Exception:
        return []

    findings: list[Finding] = []
    findings.extend(check_magic_numbers(source, filepath))
    findings.extend(check_styled_wrappers(source, filepath))
    findings.extend(check_multiple_primary_buttons(source, filepath))
    findings.extend(check_mui_imports(source, filepath))
    findings.extend(check_colors(source, filepath))
    findings.extend(check_dialog_dismissal(source, filepath))
    findings.extend(check_gettoken_source(source, filepath))
    findings.extend(check_token_names(source, filepath))
    findings.extend(check_deprecated_props(source, filepath))
    findings.extend(check_nested_container_pattern(source, filepath))
    findings = [f for f in findings if f.check not in DISABLED]
    for f in findings:
        if f.check in RULE_SOURCES:
            rel, phrase = RULE_SOURCES[f.check]
            f.source = f'{rel}: "{phrase}"'

    return findings


def scan_path(target: str) -> list[Finding]:
    if os.path.isfile(target):
        return scan_file(target)

    all_findings: list[Finding] = []
    for dirpath, _, filenames in os.walk(target):
        for fname in filenames:
            if not (fname.endswith('.tsx') or fname.endswith('.ts')):
                continue
            if should_skip(os.path.join(dirpath, fname)):
                continue
            all_findings.extend(scan_file(os.path.join(dirpath, fname)))
    return all_findings


def parse_added_lines(patch_path: str) -> dict[str, set[int]]:
    """Map each file in a unified diff to the set of line numbers it adds (new-file numbering)."""
    added: dict[str, set[int]] = {}
    current = None
    new_line = 0
    with open(patch_path, encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if line.startswith('+++ '):
                path = line[4:].strip()
                current = path[2:] if path.startswith('b/') else (None if path == '/dev/null' else path)
                if current:
                    added.setdefault(current, set())
            elif line.startswith('@@') and current:
                m = re.search(r'\+(\d+)', line)
                new_line = int(m.group(1)) if m else 0
            elif current and not line.startswith('---'):
                if line.startswith('+'):
                    added[current].add(new_line)
                    new_line += 1
                elif line.startswith('-'):
                    pass
                else:
                    new_line += 1
    return added


def tag_in_diff(findings: list[Finding], added: dict[str, set[int]]) -> None:
    for f in findings:
        norm = f.file.replace(os.sep, '/')
        match = next((p for p in added if norm.endswith('/' + p) or norm == p or p.endswith(norm)), None)
        if match is None:
            f.in_diff = False
        elif f.check == 'multiple-primary-buttons':
            f.in_diff = True  # file-level check: count it if the file was touched
        else:
            f.in_diff = f.line in added[match]


# ── Output ────────────────────────────────────────────────────────────────────

SEVERITY_ICON = {'violation': '🔴', 'concern': '🟡'}

def print_report(findings: list[Finding], root: str) -> None:
    violations = [f for f in findings if f.severity == 'violation']
    concerns = [f for f in findings if f.severity == 'concern']

    bar = '─' * 42
    print(f'\n── Custom Styling Check {bar}')
    print(f'   Scanned : {root}')
    print(f'   🔴 Violations : {len(violations)}')
    print(f'   🟡 Concerns   : {len(concerns)}')

    for severity_label, group in [('🔴 Violations', violations), ('🟡 Concerns', concerns)]:
        if not group:
            continue
        print(f'\n── {severity_label} {"─" * (60 - len(severity_label))}')
        for f in group:
            rel = os.path.relpath(f.file, root) if (os.path.isdir(root) and root != os.sep) else f.file
            tag = '  (pre-existing)' if f.in_diff is False else ''
            print(f'\n  {rel}:{f.line}  [{f.element}]{tag}')
            print(f'  {f.message}')
            if f.suggestion:
                print(f'  → {f.suggestion}')
            if f.source:
                print(f'  Source: {f.source}')

    if not findings:
        print('\n  ✅ No custom styling issues detected.\n')
    else:
        print()


def print_json(findings: list[Finding], root: str) -> None:
    out = []
    for f in findings:
        rel = os.path.relpath(f.file, root) if (os.path.isdir(root) and root != os.sep) else f.file
        out.append({
            'file': rel,
            'line': f.line,
            'severity': f.severity,
            'element': f.element,
            'message': f.message,
            'suggestion': f.suggestion,
            'check': f.check,
            'in_diff': f.in_diff,
            'source': f.source,
        })
    print(json.dumps(out, indent=2))


# ── Entry point ───────────────────────────────────────────────────────────────

def count_files(paths: list[str]) -> int:
    n = 0
    for p in paths:
        if os.path.isfile(p):
            n += 1
            continue
        for dirpath, _, filenames in os.walk(p):
            n += sum(1 for fn in filenames if fn.endswith(('.ts', '.tsx')) and not should_skip(os.path.join(dirpath, fn)))
    return n


def main() -> None:
    args = sys.argv[1:]
    as_json = '--json' in args
    diff_path = None
    if '--diff' in args:
        i = args.index('--diff')
        diff_path = args[i + 1] if i + 1 < len(args) else None
        args = args[:i] + args[i + 2:]
        if not diff_path or not os.path.isfile(diff_path):
            print(f'error: --diff patch not found: {diff_path}', file=sys.stderr)
            sys.exit(2)
    docs_dir = None
    if '--docs' in args:
        i = args.index('--docs')
        docs_dir = args[i + 1] if i + 1 < len(args) else None
        args = args[:i] + args[i + 2:]
        if not docs_dir or not os.path.isdir(docs_dir):
            print(f'error: --docs dir not found: {docs_dir}', file=sys.stderr)
            sys.exit(2)
    paths = [a for a in args if not a.startswith('--')]
    notes = load_docs(docs_dir) if docs_dir else [
        'no --docs given: doc-backed checks unverified, deprecations not loaded']
    if '--rules' in sys.argv:
        print(json.dumps({'sources': RULE_SOURCES, 'disabled': DISABLED, 'deprecated': DEPRECATED,
                          'tokens': len(TOKENS), 'deprecated_tokens': sorted(k for k, v in TOKENS.items() if v)}, indent=2))
        sys.exit(1 if DISABLED else 0)

    if not paths:
        print('Usage: python3 custom_styling_check.py <path> [<path> ...] [--json] [--diff <patch>]')
        sys.exit(2)
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        print(f'error: path not found: {", ".join(missing)}', file=sys.stderr)
        sys.exit(2)
    scanned = count_files(paths)
    if scanned == 0:
        print('error: no .ts/.tsx files to scan (tests/stories/generated are skipped)', file=sys.stderr)
        sys.exit(2)

    findings: list[Finding] = []
    for p in paths:
        findings.extend(scan_path(p))
    if diff_path:
        tag_in_diff(findings, parse_added_lines(diff_path))
        if '--changed-only' in sys.argv:
            hidden = sum(1 for f in findings if f.in_diff is False)
            findings = [f for f in findings if f.in_diff is not False]
            notes.append(f'--changed-only: {hidden} finding(s) on lines this change did not touch were not reported')
    target = paths[0] if len(paths) == 1 else os.path.commonpath([os.path.abspath(p) for p in paths])

    if as_json:
        print_json(findings, target)
    else:
        print(f'   Files scanned : {scanned}')
        for n in notes:
            print(f'   Note : {n}')
        print_report(findings, target)

    counted = [f for f in findings if f.in_diff is not False]
    if any(f.severity == 'violation' for f in counted):
        sys.exit(1)


if __name__ == '__main__':
    main()
