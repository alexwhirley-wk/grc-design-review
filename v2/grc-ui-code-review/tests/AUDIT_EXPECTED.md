# Answer key: `fixtures/audit_rules.tsx`

This is the LLM-level regression check. Run `/grc-ui-code-review tests/fixtures/audit_rules.tsx` (Local mode) and compare the report against this list.

**Pass bar:** every "must catch" item is reported (in 🔴 or 🟡), and nothing in the "must NOT flag" list is reported.

## Must catch (6, all doc-backed)

| # | Line | Planted issue | Source |
|---|---|---|---|
| 1 | 20–29 | Dialog has no `onClose`, so Esc does nothing | DESIGN.md → Dialog dismissal |
| 2 | 35 | Destructive "Delete" confirm has no `color="error"` | DESIGN.md → Deletion dialogs |
| 3 | 33 | Deletion title puts the name in the title instead of following the template | DESIGN.md → Deletion dialogs |
| 4 | 43–50 | Hand-rolled `Drawer` duplicates `GrcPageDrawer` | GrcPageDrawer MANIFEST |
| 5 | 64 | Raw hex `#9E64D5` | DESIGN.md → Design values (Token-driven); AGENTS.md → Design Tokens |
| 6 | 67 | MUI theme string `'error.main'` used as a CSS colour | AGENTS.md → Design Tokens |

> Out of scope in v2 (2026-11-19), so the skill should **not** report them: line 27, the Submit button disabled while the input is empty (accessibility); line 39, the icon-only `IconButton` with no accessible name (accessibility); line 52, the spinner with no skeleton (loading states). v1 retired the UX-audit-only items on 2026-09-25, and they stay retired.

## Must NOT flag
- Anything without a doc citation.
- The three out-of-scope items above.
- Line 26 and line 34: Cancel is `variant="text"`, which is correct.
- Line 45: the close `IconButton` has `aria-label="Close"`.
- Imports: everything comes from `@workiva/unify` or the component library.

## Scoring log

| Date | Skill change | Caught | False flags | Notes |
|---|---|---|---|---|
| 2026-11-19 | v2.0.0, docs from master f1c038c | 6/6 | 0 | 1 out-of-scope finding (empty state shown while loading) dropped at verify. Extra valid catches: hard-coded strings across 16 lines (react-intl), the drawer can't be dismissed, `GrcAiBadge` reuse, Unify `TextField` and `EmptyView`, dialog state composition, drawer width. 4 🔴 + 11 🟡. v1 history is in the v1 folder's `tests/AUDIT_EXPECTED.md` |
