---
name: grc-design-review
description: Review ts-grc front-end code against the latest GRC design guidelines (pulled live from ts-grc master every run) plus UX-audit rules. Works on a PR number/URL, a local file or directory, or — with no argument — the current branch's diff. Usage: /grc-design-review [<PR number> | <path>]
---

# GRC Design Review

You are a front-end design-system reviewer for `Workiva/ts-grc`. You review changed UI code against the **current** GRC design guidance and report findings by severity.

The design rules are **not** written into this skill. They are fetched on every run, so the review always reflects the latest docs:
- **UI and design rules:** ts-grc `master`.
- **UI copy rules:** the Content Strategy team's style guide (`Workiva/Content_Strategy_Repo/style-guide`). If that isn't accessible, the skill falls back to Unify's content docs. This skill supplies only: the process, a static scanner, the UX-audit rules (which don't live in ts-grc), and the report format.

`SKILL_DIR` below means this skill's base directory (shown when the skill loads). The helper scripts live in `SKILL_DIR/scripts/`.

**Requires:** `gh` authenticated with access to `Workiva/ts-grc` (and ideally `Workiva/Content_Strategy_Repo`), `jq`, and `python3`. Run `bash "$SKILL_DIR/tests/run_tests.sh"` to check the setup.

## Step 0 — Pick the mode

Look at the argument:

| Argument | Mode | Code under review |
|---|---|---|
| A number, `#123`, or a `github.com/Workiva/ts-grc/pull/…` URL (all three can be passed straight to `gh` and the scripts) | **PR** | The PR's changed files at its head commit |
| A path to a file or directory | **Local** | The `.ts`/`.tsx` files at that path |
| Nothing | **Branch** | The current branch's changes, if the cwd is a ts-grc checkout (see below) |

**Branch mode details:**
- It's a ts-grc checkout if `git remote get-url origin` contains `Workiva/ts-grc`. If it isn't, or the cwd isn't a git repo, ask for a PR number or path and stop.
- Run `git fetch origin master --quiet` first, so the comparison isn't against a stale master.
- Files = `git diff --name-only origin/master...HEAD -- '*.ts' '*.tsx'`, plus `.ts`/`.tsx` entries from `git status --porcelain` (ignore deleted `D` entries). Save the diff for Step 2 with `git diff origin/master -- '*.ts' '*.tsx' > "$WORK/branch.diff"`.
- If the list is empty (e.g. you're on `master` with no local changes), say *"No changed .ts/.tsx files vs origin/master on `<branch>` — pass a PR number or path."* and stop.

Create a working dir: `WORK=$(mktemp -d)` (any temp dir works).

## Step 1 — Fetch context and code (run in parallel)

```bash
bash "$SKILL_DIR/scripts/fetch_context.sh" docs "$WORK"
```

This writes:
- `$WORK/SOURCES.txt`: the master commit, when each doc last changed, and which content guide was used
- both `DESIGN.md` files
- `AGENTS.design-tokens.md`: the Design Tokens section of the root `AGENTS.md`
- every component MANIFEST, plus `MANIFEST_INDEX.txt`
- `$WORK/tokens/semantic.ts`: the semantic token catalog
- `$WORK/content/`: the content style guide files

**PR mode**, also run:

```bash
gh pr view <PR> --repo Workiva/ts-grc --json number,title,author,baseRefName,headRefOid,url
bash "$SKILL_DIR/scripts/fetch_context.sh" pr "$WORK" <PR>
```

The script writes the changed UI files at head to `$WORK/pr/` and the full diff to `$WORK/pr.diff`. It already skips tests, stories, generated files, and non-TS files, and lists what it skipped.
- If the script fails (bad PR number, no access), show its error and stop.
- If it prints `NO_UI_FILES`, don't run the scanner. Output the report header, all four headings with `None.`, the line `✅ No front-end files in this PR — nothing to design-review.`, and the skipped files under ℹ️.

**Local / Branch mode:** read the files directly from disk. Skip test files, stories, generated files, and `.d.ts`.

**Big changes (more than ~15 UI files).** The scanner still covers every file, since it's cheap. For the close read, pick up to ~15 files in this order:
1. anything under `packages/component-library/src/`
2. page, dialog, drawer, panel, and section components
3. the largest remaining `.tsx` files

Hooks, utils, types, constants, GraphQL, and analytics files don't need a close *design* read, but their user-facing strings are still covered by the copy pass in Step 4. List everything you didn't read closely under ℹ️. If two changed files are identical copies, review one and say so.

## Step 2 — Run the static scanner

```bash
python3 "$SKILL_DIR/scripts/custom_styling_check.py" <files or dirs...> --docs "$WORK" --diff <patch>
```

- PR mode: scan `$WORK/pr` with `--diff "$WORK/pr.diff"`.
- Branch mode: pass the changed files with `--diff "$WORK/branch.diff"`.
- Local mode: pass the paths, with no `--diff` (everything counts as introduced).

`--docs "$WORK"` ties the scanner to the docs you just fetched:
- Every check that enforces a written rule cites the exact doc phrase it relies on. If that phrase is no longer in today's docs, the check is **disabled** for this run and a `Note:` line says so. Put that note in ℹ️.
- Deprecated components and props come straight from the MANIFESTs (e.g. a `Don't use \`x\` — deprecated` line). Nothing is typed into the scanner by hand.
- Each finding prints a `Source:`, which is either the doc phrase, the UX-audit number, or `heuristic`. Carry it into the report.

With `--diff`, findings on lines the change didn't add are tagged `(pre-existing)`. Apply the scope rules in Step 4 to them. The scanner exits `2` with an error if a path is missing or there are no files to scan. Treat that as a failed step, never as "clean".

The scanner deterministically catches:
- inline `style={}`: visual props = 🔴, layout-only = 🟡, which is usually fine when the values are computed per element
- `styled(GrcX)` wrappers
- structural `sx` accumulation (3 structural props = 🟡, 4 or more = 🔴)
- layered containers built by hand
- `maxHeight` on non-scrolling structural boxes
- 3+ primary buttons in a file
- direct `@mui` imports
- raw hex/rgb/hsl colours and MUI theme strings (`'text.secondary'`, `'divider'`, …) used as CSS values in `sx`/`style`
- `getToken` imported from `@workiva/unify` instead of the component library
- `getToken('…')` names that aren't in the live token catalog (🔴), or that it marks `@deprecated` (🟡). Legacy `Core/*` and `GRC/*` names aren't checked.
- dialogs with no `onClose` or with `disableEscapeKeyDown` (Esc must work)
- deprecated components and props, derived from the MANIFESTs on every run

It does **not** know every MANIFEST "Don't". Those are yours to catch in Step 4.

Fold the scanner output into the report. Don't re-report the same issue from the LLM pass. Drop clear false positives and say so in ℹ️. Common ones:
- primary buttons on different surfaces (separate dialogs, stepper steps, exclusive branches)
- inline `style` that an MUI API requires (e.g. virtualized listbox rows)

## Step 3 — Load the rulebook

1. **Read in full:** `$WORK/documentation/DESIGN.md`, `$WORK/packages/component-library/DESIGN.md`, `$WORK/AGENTS.design-tokens.md`. These are the source of truth.
2. **Fetch the relevant MANIFESTs.** Each one is short, component-specific guidance (when to use it, anti-patterns, a11y checklist). Fetch them for:
   - every `Grc*` component (or component-library hook) the changed code imports or renders;
   - any component you're about to recommend as a replacement for hand-rolled UI (check `MANIFEST_INDEX.txt` to see what exists);
   - `useDisabledButtonReason` if the diff adds, removes, or changes `disabled` on a button;
   - `GrcAiBadge` if the diff renders AI-generated content or a sparkle icon;
   - the matching GRC component when the diff hand-rolls something that looks like one (e.g. a custom `Drawer` → `GrcPageDrawer`, a card → the card primitives in the index).

   All MANIFESTs are already in `$WORK` from Step 1. To get a component's path:

   ```bash
   bash "$SKILL_DIR/scripts/fetch_context.sh" manifests "$WORK" GrcPageSection GrcPageTitle ...
   ```

3. **Read the content style guide** in `$WORK/content/`. From the Content Strategy repo that's `SKILL.md` (start here), `voice-and-tone.md`, `patterns.md`, `ui-component-patterns.md`, and `editorial-style.md`; from the fallback it's Unify's voice-and-tone, content-design, writing-for-everyone, and error-messaging pages.
   - If `SOURCES.txt` says **UNAVAILABLE** and the `unify` MCP server is available, use `searchDocs("voice and tone")` and `searchDocs("error messaging")` instead.
   - Otherwise say in ℹ️ that copy wasn't checked against the style guide.
4. *Optional:* if the `unify` MCP server is available, use `searchDocs` / `getComponentDocs` for questions about Unify (not GRC) components.

## Step 4 — Review

Apply the fetched docs to the changed code. Use the areas below as a **coverage map**, so nothing gets skipped. The actual rules come from the docs, not from this list:

- Tokens and colour (`getToken`, semantic vs `Core/`, no raw hex, no theme strings as CSS values). Before recommending a token name, confirm it exists in `$WORK/tokens/semantic.ts`. Never suggest a token that isn't there; suggest adding one instead.
- MUI and Unify import rules
- Barrel and export rules inside `component-library`
- Component bucket decision (theme-only / styled wrapper / novel build)
- Layered containers: surfaces, borders, radius, elevation, and teal reserved for actions
- Page composition (`GrcPage*` building blocks, section and heading levels)
- Prop design (variants over booleans, slots, Unify prop names)
- Accessibility: disabled states, live regions, keyboard access, accessible names
- Service-agnostic shared components
- Anything a touched component's MANIFEST lists under "Don't" or anti-patterns

**Behaviour checks.** The markup can look fine while the behaviour is wrong. These were the most common misses when the skill was backtested against human reviews. Each item names the doc section to apply. Read the rule there; don't rely on a paraphrase here.
- **Data states across files** → documentation/DESIGN.md → *Loading state presentation* and *Section-scoped errors*. For each `useQuery`/mutation, follow `loading` and `error` to where they render. Look for a dropped `error` (even when a child only receives `loading`), `if (loading) return null`, and an error shown as endless loading. Read the parent or child file if needed.
- **Dialog dismissal** → documentation/DESIGN.md → *Dialog dismissal*. Check both halves of the rule: what may *not* close the dialog, and what *must*.
- **Destructive confirmations other than delete** (cancel, archive, discard, replace) → apply documentation/DESIGN.md → *Deletion dialogs* by analogy. Check that error copy agrees with its header and the state it describes.
- **General a11y heuristics.** These aren't written GRC rules, so they can be 🟡 at most and must be cited as "a11y heuristic":
  - focus lost when the clicked button becomes disabled or loading;
  - no `aria-busy` / `role="status"` while work is in flight (see also DESIGN.md → *Integration-level a11y questions* #6);
  - `autoFocus` on components that ignore it (e.g. `Autocomplete`);
  - popovers that close on Esc but not on blur;
  - `overflow: hidden` clipping a focus ring;
  - `role="listbox"` not directly owning its `role="option"` elements in virtualized lists;
  - `DialogActions` with 3+ buttons or long labels, which should be checked at a narrow width and in pseudo-locale.

**Copy pass.** UI copy is design, and reviewers flag it often. List every user-facing message in the change, including `.ts` files like validators, hooks, and config objects:

```bash
python3 "$SKILL_DIR/scripts/extract_copy.py" <files or dirs...> --diff <patch>   # omit --diff in Local mode
```

Review each message **added by this change** against the content style guide. Read the rules in the guide itself rather than relying on a summary here. The sections that usually apply:
- `SKILL.md` → *Voice and tone*, *Writing rules and house style*, *Error and success messaging*
- `voice-and-tone.md` → *Tone-shift matrix* (especially Error / failure) and *Voice-audit checklist*
- `patterns.md` → the pattern that matches the message (*Error messaging*, *Action labels*, *Empty states*, *Notifications*, …)
- `ui-component-patterns.md` → the component showing the message (*Alerts*, *Modals*, *Buttons*, *Toast alerts*, …)
- `editorial-style.md` → punctuation and capitalization

Cite the guide file and section (e.g. *content/patterns.md → Error messaging*) and suggest replacement text. Copy findings are 🟡 unless the guide states a hard rule ("never", "always", "don't"). Group them under `#### UI copy` when there are more than a few. Hardcoded strings that bypass `react-intl` are an i18n issue: cite AGENTS.md.

**Precedence:** fetched ts-grc docs > MANIFESTs > UX-audit rules below. For wording, the content style guide governs. If an audit rule conflicts with current docs, follow the docs and mention the conflict in ℹ️.

Cite the doc and section for every docs-based finding (e.g. *"documentation/DESIGN.md → Accessibility by default"*), so the author can check the rule.

### UX-audit rules (embedded — not in ts-grc)

These come from Skye Selbiger's GRC UX audit (`skyebselbiger-wk/Prototypes/Audit/findings.json`, June 2026). Finding numbers are cited so you can trace them back.

**Buttons and actions**
- `variant="text"` is only for cancel, dismiss, back, and nav links. Edit, Add, Save, Update and other non-cancel secondaries should be `variant="outlined"`. (#92, #93, #116, #166, #181, #193)
- Destructive confirms (Delete/Remove/Discard/Disconnect/Clear) use `variant="contained" color="error"`. (#64, #98)
- Don't disable submit/confirm buttons. Keep them enabled and show validation on click. If a disabled state is truly unavoidable, defer to the current DESIGN.md disabled-state guidance and the `useDisabledButtonReason` MANIFEST. (#68, #141, #178, #204)
- The trigger label, modal title, and submit label should use the same action name. (#199, #205)
- At most one primary (`contained`) action visible per surface. (#74, #157)

**Layout**
- No `maxHeight` on section containers. It makes padding shift when content height changes. (#3, #59)

**Drawers**
- The title sits in the same header row as the close button, not below a divider. (#28, #41)
- The drawer content area is white, not the gray section background. (#41)

**Empty states**
- A "Learn more" / help link goes *after* the primary action, never before it. (#119, #128)
- Every empty state has an icon that fits its content type. (#54)
- Hide (don't just disable) export and bulk actions when there's no data. (#120, #149)

**AI content**
- The sparkle/AI icon leads (left of the label), never trails. (#32, #40, #100)
- AI-generated *values* should carry `GrcAiBadge` beside the value. Flag hand-rolled sparkle-plus-label chips. Details are in the MANIFEST.

### Severity: 🔴 vs 🟡

- **🔴** covers three things:
  - scanner violations;
  - token, import, barrel, service-agnostic, and removed-prop rules;
  - any rule the fetched docs or a MANIFEST state as a requirement ("must", "never", "always", "Don't", "required", or a stated standard like "Cancel is a text-variant button").
- **🟡** covers:
  - rules the docs phrase as a preference ("prefer", "should", "discouraged", "consider");
  - UX-audit rules the docs don't restate;
  - anything that needs product or design context to judge.
- When in doubt, use 🟡 and say what would make it 🔴.
- Treat each dialog, drawer, and stepper step as its own **surface** for "one primary action per surface".
- Treat only `packages/component-library/` as "shared components" for the service-agnostic and prop-design rules, unless the docs name another package.

### Scope: new vs. pre-existing issues

The scanner and your reading cover whole files, so you will find issues the PR didn't introduce. Classify by whether the line is in the diff:
- **Introduced or modified by this change** → 🔴 / 🟡 as normal.
- **Pre-existing, in code the change touches or sits right next to** (same component/footer/dialog) → 🟡 labeled *"pre-existing — optional while you're here"*.
- **Pre-existing, elsewhere in the file** → ℹ️ only.
- Lines that were only re-indented or moved count as pre-existing.
- A PR that starts *using* an existing component doesn't own that component's existing issues: ℹ️ at most.

In Local mode (a path, no diff) everything counts as "introduced".

Line numbers: cite the line in the head/local file (not the diff hunk).

## Step 5 — Report

```
**<PR #N — title | path | branch name>**
*Author: … | Base: …*  (PR mode only)
*Rules: ts-grc master @ <sha> (<date>) — <one line per doc from SOURCES.txt, including the content style guide line>*

### 🔴 Violations (must fix)
Non-negotiables: tokens, MUI imports, barrel rules, service-agnostic, removed props, and anything the docs mark as required.

### 🟡 Concerns (worth discussing)
Guideline deviations that might be intentional. Add "confirm this is intentional" where unsure.

### 🟢 Looks good
Tricky guidelines the code follows correctly.

### ℹ️ Not checked / notes
Skipped files, checks that couldn't run, and doc-vs-audit conflicts.
```

Each finding: `file:line` — the rule and its source (doc section or audit #) — what to change.

**Always print all four headings, in this order.** If a section has nothing, write `None.` under it. Never omit or reorder a heading. If there are no 🔴 or 🟡 findings introduced by this change, add `✅ No design issues introduced.` directly under the Rules line (optional pre-existing 🟡s don't block it).

**Group by theme when a section has more than 5 findings.** Use `####` subheadings named for the pattern (e.g. `#### Disabled controls`, `#### Cancel button variant`, `#### Loading / error / empty states`). Put the shared rule source on one line under the subheading, and don't repeat it in every bullet. When the same fix applies to many places, write one bullet and list the `file:line`s under it. With 5 or fewer findings, use a flat list.

Mark hand-rolled UI that duplicates a GRC component as a **designer flag**, so it can go to UX as well as the author. If no GRC component fits, recommend filing a component-library ticket instead of shipping custom styling.

Clean up with `rm -rf "$WORK"` when done.
