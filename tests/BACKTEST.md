# Backtest: skill vs. human design reviews

The strongest test of whether the skill is useful. Run it blind on merged ts-grc PRs *as they looked before human review*, then compare its findings with what reviewers actually said.

## How to rerun
1. For each PR below, fetch the changed UI files at the listed commit, plus the diff from the PR's merge base to that commit (`gh api repos/Workiva/ts-grc/compare/<base>...<commit>`).
2. Run the skill in PR mode on those files with `--diff`, **without** looking at the PR's comments.
3. Pull the PR's top-level inline comments from non-author humans (`gh api repos/Workiva/ts-grc/pulls/<N>/comments`).
4. Classify each comment:
   - **DESIGN**: catchable from code plus docs
   - **DESIGN-FIGMA**: needs Figma, screenshots, or unwritten conventions
   - **OUT**: logic, tests, naming, etc.
5. Score recall (caught + ½ partial) on catchable DESIGN comments, plus the precision of the skill's 🔴 and 🟡.

**Caveat:** the docs are fetched from *today's* master, so some findings cite rules written after the PR merged.

## PR set (chosen 2026-09-24 for design-relevant review comments)

| PR | Reviewed commit | Why it's in the set |
|---|---|---|
| 10500 | `e10b4b363c` | Access rules: disabled Save, dialog discarding input, blank loading page, listbox ARIA |
| 10766 | `11301732fa` | Dialogs with no `onClose` (Esc), a swallowed query error |
| 8768 | `3262342a24` | Log-time dialog: header alignment, `autoFocus`, literal "+" |
| 10494 | `84136687d6` | Disabled + tooltip vs. click and validate |
| 10671 | `b94442d61c` | Native `disabled` on the Add buttons |
| 8389 | `6a2e373fbe` | Hard-coded colour → `getToken` |
| 11773 | `fae673e302` | Cancel-project dialog copy conventions (mostly Figma or convention) |
| 9160 | `17038e5c9b` | Attachment viewer: should use UnifyList, `getToken` source, padding |
| 11794 | `18b325f9f9` | CPM import full page: Kate's content-style-guide copy comments, icon colour, redirect flow |
| 8521 | `8704765ebd` | FRESH (added 2026-09-25): overflow-menu disabled state and tooltip copy |
| 10171 | `abfa90ab36` | FRESH: governance program dialogs, error toasts and copy (mostly product calls) |
| 9174 | `7fd35e4e8b` | FRESH: project/template dialogs, navigation guard, team toast conventions |
| 8854 | `21db6e5c12` | FRESH: grid export menu, confirm dialog copy, hide export when empty |
| 11294 | `35b7b23ee0` | Publish dialog: focus loss, error copy, long action labels |
| 10052 | `acf6df3a4c` | Accordion: `square` prop, `overflow: hidden` clipping the focus ring, tokens |

## Results log

| Date | Skill version | Recall (catchable) | 🔴 precision | 🟡 precision (sampled) | Notes |
|---|---|---|---|---|---|
| 2026-09-24 | baseline | 12/27 (44%) | 11/13 valid, 1 wrong | 46/63 valid, 0 wrong | Misses were mostly behaviour (Esc, focus, data states) and copy by analogy. Fixes applied the same day: behaviour checklist, severity rubric, dialog/colour/`getToken` scanner checks. Rerun still needed. |
| 2026-09-24 | + content style guide + copy pass | #11794 only: 8/10 of Kate's inline comments (was 0/10) | 2/2 valid | — | Missed: the icon colour (visual) and the "Couldn't update X" word order (it wrongly praised it). Also missed the post-import redirect (a product flow call). |
| 2026-09-25 | + behaviour checks, severity rubric, doc-verified scanner, token catalog, content guide + copy pass | Repeat: 23.5/27 (87%); 84% without 5 leaked heuristics. Fresh: 4/5 (80%, small n) | 42/44 valid, 2 debatable, 0 wrong | Repeat 65/93 valid, 2 wrong · Fresh 24/31 valid, 0 wrong | Both wrong 🟡 recommended `radius/card` (a doc bug: DESIGN.md names a token that isn't in semantic.ts). Reports are about 2.3× longer (~3 🔴 + 12–14 🟡 per PR). Noise: embedded audit rule vs DESIGN.md button variants, copy nits on pre-existing strings, team practice diverging from docs. |
