# Answer key: `fixtures/audit_rules.tsx`

This is the LLM-level regression check. Run `/grc-design-review tests/fixtures/audit_rules.tsx` (Local mode) and compare the report against this list.

**Pass bar:** every "must catch" item is reported (in 🔴 or 🟡), and nothing in the "must NOT flag" list is reported.

## Must catch (9, all doc-backed)

| # | Line | Planted issue | Source |
|---|---|---|---|
| 1 | 27 | Submit button disabled while the input is empty | DESIGN.md → Prefer warn-after-the-fact |
| 2 | 20–29 | Dialog has no `onClose`, so Esc does nothing | DESIGN.md → Dialog dismissal |
| 3 | 35 | Destructive "Delete" confirm has no `color="error"` | DESIGN.md → Deletion dialogs |
| 4 | 33 | Deletion title puts the name in the title instead of following the template | DESIGN.md → Deletion dialogs |
| 5 | 39 | Icon-only delete `IconButton` has no accessible name | DESIGN.md → Accessible by default / Integration-level a11y questions |
| 6 | 43–50 | Hand-rolled `Drawer` duplicates `GrcPageDrawer` | GrcPageDrawer MANIFEST |
| 7 | 52 | Spinner for loading, with no skeleton | DESIGN.md → Loading state presentation |
| 8 | 64 | Raw hex `#9E64D5` | DESIGN.md → Design values (Token-driven); AGENTS.md → Design Tokens |
| 9 | 67 | MUI theme string `'error.main'` used as a CSS colour | AGENTS.md → Design Tokens |

> Retired on 2026-09-25, when the skill became docs-only: label mismatch, `text` variant on the trigger, the drawer title/background, "Learn more" order, the empty-state icon, hiding Export when there's no data, and the trailing sparkle. These came from the UX audit, not from the docs. The skill should now **not** report them unless the docs add those rules.

## Must NOT flag
- Anything without a doc citation (e.g. the retired audit-only items above).
- Line 26 and line 34: Cancel is `variant="text"`, which is correct.
- Line 45: the close `IconButton` has `aria-label="Close"`.
- Imports: everything comes from `@workiva/unify` or the component library.

## Scoring log

| Date | Skill change | Caught | False flags | Notes |
|---|---|---|---|---|
| 2026-09-24 | baseline (run 1) | 13/14 | 0 | missed #4 (dialog Esc); extra valid catches: unlabeled `<input>`, drawer can't be dismissed |
| 2026-09-24 | baseline (run 2) | 14/14 | 0 | same 🔴 set as run 1 |
