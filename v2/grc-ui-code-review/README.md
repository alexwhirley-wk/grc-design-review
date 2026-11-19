# grc-ui-code-review

> *Catch what your FE reviewer would flag before you click "Ready for review".*

A Claude Code skill for developers working in `Workiva/ts-grc`. Run it on your branch before you open a PR. It checks your front-end changes against the repository's own written rules, then offers to fix what it finds.

Version 2.2.0. Owner: Alex Whirley. This is a separate skill from `grc-design-review` (v1), with a narrower, developer-focused scope. Both can be installed side by side.

---

## What it checks

| Area | Typical findings |
|---|---|
| **Dialogs, empty states, and toasts** | Dialog can't be closed with Esc, or closes on a backdrop click; dialog state that survives close and reopen; error from a dialog fired as a toast that renders behind it; outlined Cancel in a dialog footer; red Delete in an overflow menu; drawer used where the docs call for a dialog or route; missing success toast or empty state |
| **react-intl** | Hard-coded user-facing strings; translated strings joined together or passed into another message; `formatMessage` without `defaultMessage` or `description`; dates formatted with `toLocaleDateString()` |
| **Components and reuse** | Hand-rolled drawer, list, accordion, or button where a GRC or Unify component exists; deprecated components and props; a MANIFEST's "Don't" list. Existing shared components no doc names are listed as reuse candidates, without a severity |
| **Design tokens** | Raw hex, `'error.main'` used as a colour, `borderRadius: 4`, `padding: '12px'` or `style={{ margin: 16 }}` (theme steps like `p: 2` are fine), `getToken` names that don't exist or are deprecated, `getToken` imported from the wrong package |
| **Component-library architecture** | Wrap vs. theme vs. build, `styled(GrcX)` wrappers and thin wrapper components, boolean-prop sprawl vs. variants and slots, direct `@mui` imports, barrel and export rules |

**Not checked:** UI copy and tone, accessibility (including whether to disable a button), usability, how loading and error states look, layered containers, density and truncation, and general code quality. The report points you to the skill that covers each of these when it notices one.

---

## Where the rules come from

Nothing is copied into the skill. **Every finding quotes the rule it's based on and names the document and section**, so you can check it yourself. If no document states a rule, there's no finding.

The docs are read from **the ts-grc checkout you're reviewing**. If you aren't in a checkout (for example, reviewing a PR from another folder), the skill fetches the same files from `master`.

| File in ts-grc | Used for |
|---|---|
| `documentation/DESIGN.md` | Dialog, drawer, empty-state, and toast patterns; design values and tokens |
| `packages/component-library/DESIGN.md` | Wrap vs. theme vs. build, prop design, imports and barrels |
| `AGENTS.md` | Internationalization, date formatting, dialog error handling and composition, design tokens, thin wrappers |
| `packages/component-library/src/**/*.MANIFEST.md` | When to use each GRC component, its "Don't" list, deprecated props |
| `packages/component-library/src/theme/tokens/semantic.ts` | The real token names, and which are deprecated |

The report's **Rules** line shows which commit the docs came from. If your branch is behind `origin/master`, it says by how much, because you were checked against your branch's version of the docs.

> **It won't enforce a rule the docs dropped.** Each scanner check quotes the sentence it enforces. If that sentence is removed or reworded, the check switches itself off for the run, and the report says so.

---

## How a run works

1. **Scanner.** A fast, deterministic pass for the mechanical rules: tokens, imports, wrappers, dialog dismissal, and deprecations. It can also run on its own (see below).
2. **Three reviewer agents, in parallel.** Each reads one rule source in full: dialogs, empty states, and toasts; component library, tokens, and react-intl; components and MANIFESTs.
3. **Verify.** Every finding must quote rule text that really is in the docs and sit on a line your change added or modified. Anything else is dropped, and the report counts what was dropped and why.
4. **Report**, then an offer to apply the fixes to your own code.

---

## Install

The skill lives in the `v2/grc-ui-code-review/` folder of the `alexwhirley-wk/grc-design-review` repository. Link it into your skills folder:

```bash
git clone git@github.com:alexwhirley-wk/grc-design-review.git ~/src/grc-design-review
ln -s ~/src/grc-design-review/v2/grc-ui-code-review ~/.claude/skills/grc-ui-code-review
```

Then check your setup from a ts-grc checkout:

```bash
bash ~/.claude/skills/grc-ui-code-review/tests/run_tests.sh
```

You need `git`, `python3`, and `jq`. `gh` logged in with access to `Workiva/ts-grc` is needed for PR mode and for the `master` fallback. The Unify MCP server is optional: with it connected, Unify component recommendations are verified against Unify's live docs.

---

## Use

| Type this in Claude Code | To review |
|---|---|
| `/grc-ui-code-review` | Your branch's changes vs `origin/master`. Run it from a ts-grc checkout. This is the main use. |
| `/grc-ui-code-review 12345` | A PR. A number, `#12345`, or the full URL all work. |
| `/grc-ui-code-review packages/foo-client/src/Bar.tsx` | A file or folder, every line |

In branch and PR mode it **only comments on lines you added or changed**. You're never asked to fix code you didn't touch.

### The report

```
**feature/audt-123-import-dialog**
*grc-ui-code-review v2.2.0 · Mode: Branch*
*Rules: ts-grc checkout feature/audt-123-import-dialog @ 1a2b3c4 (2026-11-18), 0 commit(s) behind origin/master*

### 🔴 Must fix
- ImportDialog.tsx:42: error toast fired while the dialog is open. Source: AGENTS.md → Dialog Error Handling.
  Fix: show an inline <Alert> at the top of the dialog content.
- ImportDialog.tsx:58: getToken('radius/card') isn't in the token catalog. Source: semantic.ts.

### 🟡 Worth discussing
- ImportSummary.tsx:17: hand-rolled empty message. Source: DESIGN.md → Empty state presentation. 🎨 designer flag

### ℹ️ Not checked / notes
- 2 findings dropped: not on changed lines.
```

- **🔴 Must fix:** rules the docs state as requirements ("must", "never", "always", "Don't", "Required"), plus every scanner violation.
- **🟡 Worth discussing:** rules phrased as preferences, and calls that need product or design context.
- **ℹ️ Not checked / notes:** skipped files, checks that couldn't run, conflicts between documents, reuse candidates, and areas left to other skills.

### Applying fixes

On your own branch, PR, or files, it offers to apply the fixes. It fixes every 🔴, asks which 🟡s to take, and only touches lines in scope. Then it runs the package's lint, typecheck, and tests. It never commits or pushes unless you ask.

On someone else's PR it only reports. To post a review, use `design-review` from ux-skills, which runs the UX review skills and posts their reviews. It doesn't run this skill yet.

### Running the scanner alone

The scanner works without Claude, for example in a pre-push hook or CI:

```bash
WORK=$(mktemp -d)
bash scripts/fetch_context.sh local "$WORK" .
git diff origin/master -- '*.ts' '*.tsx' > "$WORK/branch.diff"
python3 scripts/custom_styling_check.py packages/foo-client/src --docs "$WORK" --diff "$WORK/branch.diff" --changed-only
```

Exit codes: `0` clean, `1` violations on changed lines, `2` bad input. Add `--json` for machine-readable output, or `--rules` to list each check's source and any disabled checks.

---

## FAQ

**How accurate is it?** Backtested blind on 14 real ts-grc PRs (2026-11-19, v2.0.0): it caught 67% of the human review comments in its areas, and none of its 128 findings were wrong. Most human comments on those PRs were about copy, logic, or Figma details, which this skill doesn't check. v2.1.0 fixes the misses that run found; see `tests/BACKTEST.md`. Treat it as a strong first pass, not as UX sign-off. It can't see Figma or the running app, so a finding can contradict a design decision made there.

**The docs changed. Do I need to update anything?** Usually not. It reads the docs on every run. If a scanner check's source sentence disappears, `tests/run_tests.sh` fails and names the check to update.

**Why does it say my branch is behind?** It read the docs from your checkout. Rebase onto `origin/master` to be checked against the latest rules.

**Cursor?** Only a Claude Code version exists so far.

---

## What's inside

```
grc-ui-code-review/
├── SKILL.md                    # process, reviewer briefs, severity and scope rules, report format
├── README.md
├── scripts/
│   ├── fetch_context.sh        # reads docs, MANIFESTs, and tokens from the checkout (or master); fetches PR files
│   └── custom_styling_check.py # the scanner; each check cites its doc and switches off if the rule disappears
└── tests/
    ├── run_tests.sh            # run after any change
    ├── expected.json           # scanner fixture answers
    ├── fixtures/               # scanner fixtures, a minimal docs snapshot, and audit_rules.tsx
    ├── AUDIT_EXPECTED.md       # answer key for the planted-issue file
    └── BACKTEST.md             # how to compare it with real human reviews
```
