# Answer key: `fixtures/audit_rules.tsx`

This is the LLM-level regression check. Run `/grc-design-review tests/fixtures/audit_rules.tsx` (Local mode) and compare the report against this list.

**Pass bar:** every item below is reported (in 🔴 or 🟡) and nothing in the "must NOT flag" list is reported.

## Must catch (14)

| # | Line | Planted issue | Source |
|---|---|---|---|
| 1 | 19 | "Log Response" trigger uses `variant="text"` for a non-cancel action | audit #92/#93 |
| 2 | 19/21/27 | Label mismatch: trigger "Log Response" → title "Log Management Response" → submit "Add" | audit #199/#205 |
| 3 | 27 | Submit button disabled while the input is empty | DESIGN.md → warn-after-the-fact; audit #68 |
| 4 | 20–29 | Dialog has no `onClose`, so Esc does nothing | DESIGN.md → Dialog dismissal |
| 5 | 35 | Destructive "Delete" confirm has no `color="error"` | audit #64/#98 |
| 6 | 33 | Deletion title puts the name in the title instead of the template (`Delete [item]?` + quoted name in the body) | DESIGN.md → Deletion dialogs |
| 7 | 39 | Icon-only delete `IconButton` has no `aria-label` | DESIGN.md → Accessibility |
| 8 | 44–48 | Drawer title sits below a divider instead of next to the close button | audit #28/#41 |
| 9 | 49 | Drawer body uses the gray section background | audit #41 |
| 10 | 52 | Spinner for loading, with no skeleton and no `aria-live` | DESIGN.md → Loading state presentation |
| 11 | 57–58 | "Learn more" comes before the primary action | audit #119/#128 |
| 12 | 55–59, 61 | Empty state has no icon, **and** Export shows even when there's no data | audit #54; #120/#149 |
| 13 | 64–65 | Trailing sparkle icon **and** raw hex `#9E64D5` (the old AI purple) | audit #32/#40; AGENTS.md → Design Tokens |
| 14 | 67 | MUI theme string `'error.main'` used as a CSS colour | AGENTS.md → Design Tokens |

## Must NOT flag
- Line 26 and line 34: Cancel is `variant="text"`, which is correct.
- Line 45: the close `IconButton` has `aria-label="Close"`.
- Imports: everything comes from `@workiva/unify` or the component library.

## Scoring log

| Date | Skill change | Caught | False flags | Notes |
|---|---|---|---|---|
| 2026-09-24 | baseline (run 1) | 13/14 | 0 | missed #4 (dialog Esc); extra valid catches: unlabeled `<input>`, drawer can't be dismissed |
| 2026-09-24 | baseline (run 2) | 14/14 | 0 | same 🔴 set as run 1 |
