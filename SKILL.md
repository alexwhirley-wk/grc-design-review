---
name: grc-design-review
description: Review ts-grc front-end code against the latest GRC design guidelines (pulled live from ts-grc master, plus the Content Strategy style guide, every run). Runs one parallel reviewer per rule source (product design, component library and tokens, component MANIFESTs, content style guide), then verifies and merges their findings into one report and offers a next step (fix your own code, or post a review on someone else's PR). Works on a PR number/URL, a local file or directory, or — with no argument — the current branch's diff. Usage: /grc-design-review [<PR number> | <path>]
---

# GRC Design Review

You orchestrate a front-end design-system review for `Workiva/ts-grc`. You gather the context, run the scanner, hand each rule source to its own reviewer agent, then verify, merge and rank what they find into one report.

The design rules are **not** written into this skill. They are fetched on every run, so the review always reflects the latest docs:
- **UI and design rules:** ts-grc `master`.
- **UI copy rules:** the Content Strategy team's style guide (`Workiva/Content_Strategy_Repo/style-guide`). If that isn't accessible, the skill falls back to Unify's content docs.
**Every finding must cite one of those documents.** This skill supplies only the process, the scanners, and the report format; it holds no design rules of its own.

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

**Whose code is it?** This decides the next step offered in Step 7.
- **PR mode:** compare the PR author (`gh pr view <PR> --repo Workiva/ts-grc --json author -q .author.login`) with the user (`gh api user -q .login`). Same login → **own PR**; different → **someone else's PR**.
- **Branch mode:** **own code**.
- **Local mode:** no next step is offered.

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
- If it prints `NO_UI_FILES`, don't run the scanner or the agents. Output the report header, all three headings with `None.`, the line `✅ No front-end files in this PR — nothing to design-review.`, and the skipped files under ℹ️.

**Local / Branch mode:** read the files directly from disk. Skip test files, stories, generated files, and `.d.ts`.

**Big changes.** The scanner and the copy extract still cover every file, since they're cheap. For the reviewer agents' close read, pick up to ~30 files in this order:
1. anything under `packages/component-library/src/`
2. page, dialog, drawer, panel, and section components
3. the largest remaining `.tsx` files

Hooks, utils, types, constants, GraphQL, and analytics files don't need a close *design* read, but their user-facing strings are still covered by the copy agent. List everything that didn't get a close read under ℹ️. If two changed files are identical copies, review one and say so.

## Step 2 — Run the static scanner

```bash
python3 "$SKILL_DIR/scripts/custom_styling_check.py" <files or dirs...> --docs "$WORK" --diff <patch>
```

- PR mode: scan `$WORK/pr` with `--diff "$WORK/pr.diff" --changed-only`.
- Branch mode: pass the changed files with `--diff "$WORK/branch.diff" --changed-only`.
- Local mode: pass the paths, with no `--diff` (everything counts as introduced).

`--docs "$WORK"` ties the scanner to the docs you just fetched:
- Every check that enforces a written rule cites the exact doc phrase it relies on. If that phrase is no longer in today's docs, the check is **disabled** for this run and a `Note:` line says so. Put that note in ℹ️.
- Deprecated components and props come straight from the MANIFESTs (e.g. a `Don't use \`x\` — deprecated` line). Nothing is typed into the scanner by hand.
- Each finding prints a `Source:`: the doc phrase, MANIFEST line, or token catalog entry it's based on. Carry it into the report.

In PR and Branch mode, add `--changed-only`, so the scanner reports only lines the change adds or modifies (see *Scope* below). The scanner exits `2` with an error if a path is missing or there are no files to scan. Treat that as a failed step, never as "clean".

The scanner deterministically catches the following. Each check cites its doc and switches itself off if that rule disappears:
- hard-coded radius and typography values (`borderRadius: 4`, `fontSize: 10`) in `sx`/`style` (DESIGN.md → *Design values*, Token-driven)
- raw hex/rgb/hsl colours and MUI theme strings (`'text.secondary'`, `'divider'`, …) used as CSS values
- `getToken('…')` names that aren't in the live token catalog (🔴), or that it marks `@deprecated` (🟡). Legacy `Core/*` and `GRC/*` names aren't checked.
- `getToken` imported from `@workiva/unify` instead of the component library
- direct `@mui` imports
- `styled(GrcX)` wrappers
- outer background box wrapping a bordered inner box (sections don't get borders)
- 3+ primary buttons in a file
- dialogs with no `onClose` or with `disableEscapeKeyDown`
- deprecated components and props, derived from the MANIFESTs

It does **not** know every MANIFEST "Don't". The reviewer agents catch those.

Save the scanner output to `$WORK/scanner.txt`. Drop clear false positives now and note them for ℹ️. A common one:
- primary buttons on different surfaces (separate dialogs, stepper steps, exclusive branches)

## Step 3 — Extract copy and build the shared brief

List every user-facing message in the change, including `.ts` files like validators, hooks, and config objects:

```bash
python3 "$SKILL_DIR/scripts/extract_copy.py" <files or dirs...> --diff <patch> --changed-only > "$WORK/copy.txt"   # omit both flags in Local mode
```

Then find which `Grc*` components (and component-library hooks) the changed code imports or renders, and look up their MANIFEST paths:

```bash
bash "$SKILL_DIR/scripts/fetch_context.sh" manifests "$WORK" GrcPageSection GrcPageTitle ...
```

Every agent in Step 4 gets the same **shared brief**, plus its own section:
- the mode and what's under review (PR number and title, path, or branch)
- `$WORK`, and the patch path (`$WORK/pr.diff` or `$WORK/branch.diff`; none in Local mode)
- the files for the close read (Step 1), and where they are (`$WORK/pr/` or on disk)
- `$WORK/scanner.txt`: already reported, so don't report those again
- the *Scope* rules, *Severity* rules, and *No rule, no finding* from the **Shared rules** section below, copied in full
- that the agent is read-only: no edits, commits, or comments

Ask each agent to return **findings only**, no prose, each with:
- `file:line` (the line in the head/local file, not the diff hunk)
- **Rule:** the rule text quoted *exactly* from the doc
- **Source:** the doc path and section (e.g. `documentation/DESIGN.md → Dialog dismissal`)
- **Severity:** 🔴 or 🟡, with the word in the rule that justifies it ("must", "prefer", …)
- **Fix:** what to change; replacement text for copy
- whether it's a **designer flag** (hand-rolled UI that duplicates a GRC component)

At most ~12 findings, most important first. Then a short **notes** list (anything it couldn't check, conflicts between docs, `<package>` diverging from the docs).

## Step 4 — Reviewers, one per rule source, in parallel

Launch all four in **one message** (general-purpose agents). Each reads only its own source in full; the coverage areas below say where to look, but the rules come from the docs, not from this list.

1. **Product design** (most capable model). **Reads:** `$WORK/documentation/DESIGN.md`. **Covers:**
   - page composition (`GrcPage*` building blocks, section and heading levels), buttons and "one primary action per surface"
   - **behaviour checks**, the most common misses when the skill was backtested against human reviews. Each names the doc section to apply; read the rule there, don't rely on a paraphrase:
     - **Data states across files** → *Loading state presentation* and *Section-scoped errors*. For each `useQuery`/mutation, follow `loading` and `error` to where they render. Look for a dropped `error` (even when a child only receives `loading`), `if (loading) return null`, and an error shown as endless loading. Read the parent or child file if needed.
     - **Dialog dismissal** → *Dialog dismissal*. Check both halves: what may *not* close the dialog, and what *must*.
     - **Destructive confirmations other than delete** (cancel, archive, discard, replace) → apply *Deletion dialogs* by analogy. Check that error copy agrees with its header and the state it describes.
     - **Accessibility of changed interactive elements** → answer *Integration-level a11y questions* (disabled states, keyboard model, required fields, announcing dynamic changes) for each one the change adds.
2. **Component library and tokens** (most capable model). **Reads:** `$WORK/packages/component-library/DESIGN.md`, `$WORK/AGENTS.design-tokens.md`, `$WORK/tokens/semantic.ts`. **Covers:**
   - tokens and colour (`getToken`, semantic vs `Core/`, no raw hex, no theme strings as CSS values). Before recommending a token name, confirm it exists in `semantic.ts`. Never suggest a token that isn't there; suggest adding one instead.
   - MUI and Unify import rules; barrel and export rules inside `component-library`
   - component bucket decision (theme-only / styled wrapper / novel build)
   - layered containers: surfaces, borders, radius, elevation, and teal reserved for actions
   - prop design (variants over booleans, slots, Unify prop names) and service-agnostic shared components
   - hardcoded strings that bypass `react-intl` (cite AGENTS.md)
3. **MANIFESTs** (most capable model). **Reads:** `$WORK/MANIFEST_INDEX.txt` and the MANIFEST of every component from Step 3, plus:
   - `useDisabledButtonReason` if the diff adds, removes, or changes `disabled` on a button
   - `GrcAiBadge` if the diff renders AI-generated content or a sparkle icon
   - the matching GRC component when the diff hand-rolls something that looks like one (e.g. a custom `Drawer` → `GrcPageDrawer`, a card → the card primitives in the index)
   **Covers:**
   - anything a touched component's MANIFEST lists under "Don't" or anti-patterns, its *A11y checklist*, and deprecated props the scanner missed
   - **reuse and local precedent.** Before recommending that something be built or restyled, search the package, its sibling packages (e.g. `grc-core`), and `MANIFEST_INDEX.txt` for a component or hook that already does it (e.g. a shared loading view), and recommend reusing it. Use the local checkout if you're in one; otherwise use `gh api repos/Workiva/ts-grc/contents/<path>` or `gh search code --repo Workiva/ts-grc`. If sibling code follows a different pattern than the docs, **the docs still win**: report per the docs, and add a note that `<package>` diverges.
   - hand-rolled UI that duplicates a GRC component → designer flag. If no GRC component fits, recommend a component-library ticket instead of custom styling.
   - *Optional:* if the `unify` MCP server is available, `searchDocs` / `getComponentDocs` for questions about Unify (not GRC) components.
4. **Content style guide.** **Reads:** `$WORK/content/` and `$WORK/copy.txt`. From the Content Strategy repo that's `SKILL.md` (start here), `voice-and-tone.md`, `patterns.md`, `ui-component-patterns.md`, and `editorial-style.md`; from the fallback it's Unify's voice-and-tone, content-design, writing-for-everyone, and error-messaging pages.
   - If `SOURCES.txt` says **UNAVAILABLE** and the `unify` MCP server is available, use `searchDocs("voice and tone")` and `searchDocs("error messaging")` instead. Otherwise don't launch this agent; say in ℹ️ that copy wasn't checked against the style guide.
   - **Covers:** every message in `copy.txt`. The sections that usually apply:
     - `SKILL.md` → *Voice and tone*, *Writing rules and house style*, *Error and success messaging*
     - `voice-and-tone.md` → *Tone-shift matrix* (especially Error / failure) and *Voice-audit checklist*
     - `patterns.md` → the pattern that matches the message (*Error messaging*, *Action labels*, *Empty states*, *Notifications*, …)
     - `ui-component-patterns.md` → the component showing the message (*Alerts*, *Modals*, *Buttons*, *Toast alerts*, …)
     - `editorial-style.md` → punctuation and capitalization
   - Copy findings are 🟡 unless the guide states a hard rule ("never", "always", "don't"). Every finding suggests replacement text.

If the close read is over ~15 files, split it between two Product design agents (same brief, half the files each).

## Step 5 — Verify, merge, rank

Don't show the user raw agent output. For every finding:

1. **Verify.**
   - The quoted rule text appears in the cited file under `$WORK` (grep for it). If it doesn't, drop the finding: no rule, no finding.
   - In PR and Branch mode, the cited line is a changed line in the patch (see *Scope*). If not, drop it.
   - In Local mode, the cited file is under the path you were given. Agents may read parent, child, or sibling files for context, but findings in those files are dropped.
   - Any token it recommends exists in `$WORK/tokens/semantic.ts`.
   - For each 🔴 and each behaviour-check finding, open the code and confirm the claim yourself.
2. **Merge.** Combine duplicates across agents and the scanner into one finding, keeping the most specific source. When two sources conflict, apply **Precedence** below and note the conflict in ℹ️.
3. **Rank.** Set the final severity yourself, using the *Severity* rules; don't just take the agent's.
4. **Dropped findings** go in ℹ️ as one count line with the reasons (e.g. "4 agent findings dropped: 3 not on changed lines, 1 rule text not found in docs"). Keep the at-most-one "unchanged code" count line from *Scope*.
5. **Notes:** merge the agents' notes into ℹ️.

## Shared rules

Agents get these rules in their brief; you apply them again in Step 5.

**Precedence:** fetched ts-grc docs > MANIFESTs. For wording, the content style guide governs. If two documents conflict (e.g. DESIGN.md names a token that isn't in `semantic.ts`), follow the more specific source and note the conflict in ℹ️.

**No rule, no finding.** If you can't cite a document for a concern, leave it out. Cite the doc and section for every finding (e.g. *"documentation/DESIGN.md → Accessibility by default"*), so the author can check the rule.

### Severity: 🔴 vs 🟡

- **🔴** covers three things:
  - scanner violations;
  - token, import, barrel, service-agnostic, and removed-prop rules;
  - any rule the fetched docs or a MANIFEST state as a requirement ("must", "never", "always", "Don't", "required", or a stated standard like "Cancel is a text-variant button").
- **🟡** covers:
  - rules the docs phrase as a preference ("prefer", "should", "discouraged", "consider");
  - anything that needs product or design context to judge.
- When in doubt, use 🟡 and say what would make it 🔴.
- Treat each dialog, drawer, and stepper step as its own **surface** for "one primary action per surface".
- Treat only `packages/component-library/` as "shared components" for the service-agnostic and prop-design rules, unless the docs name another package.

### Scope: only lines the change touched

In PR and Branch mode, **comment only on lines the change adds or modifies.** Use the diff to check each finding before it goes in the report.
- A finding must be anchored on a changed line. If a problem only exists in unchanged code, leave it out, even when it's in the same component. Don't label it "pre-existing" or put it in ℹ️.
- A changed line that *causes* a problem elsewhere counts. For example, a new `useQuery` whose `error` is never rendered: anchor the finding on the changed line.
- Lines that were only re-indented or moved don't count as changed.
- A PR that starts *using* an existing component doesn't own that component's issues.
- At most, ℹ️ may carry one count line: "N issues in unchanged code not reported."

In Local mode (a path, no diff) every line of the files under that path is in scope, and nothing outside it.

Line numbers: cite the line in the head/local file (not the diff hunk).

## Step 6 — Report

```
**<PR #N — title | path | branch name>**
*Author: … | Base: …*  (PR mode only)
*Rules: ts-grc master @ <sha> (<date>) — <one line per doc from SOURCES.txt, including the content style guide line>*

### 🔴 Violations (must fix)
Non-negotiables: tokens, MUI imports, barrel rules, service-agnostic, removed props, and anything the docs mark as required.

### 🟡 Concerns (worth discussing)
Guideline deviations that might be intentional. Add "confirm this is intentional" where unsure.

### ℹ️ Not checked / notes
Skipped files, checks that couldn't run, dropped findings, and conflicts between documents.
```

Each finding: `file:line` — the rule and its source (doc section, MANIFEST, token catalog, or style guide section) — what to change.

**Always print all three headings, in this order.** Don't add a section listing what the code gets right. If a section has nothing, write `None.` under it. Never omit or reorder a heading. If there are no 🔴 or 🟡 findings, add `✅ No design issues introduced.` directly under the Rules line.

**Group by theme when a section has more than 5 findings.** Use `####` subheadings named for the pattern (e.g. `#### Disabled controls`, `#### Cancel button variant`, `#### Loading / error / empty states`, `#### UI copy`). Put the shared rule source on one line under the subheading, and don't repeat it in every bullet. When the same fix applies to many places, write one bullet and list the `file:line`s under it. With 5 or fewer findings, use a flat list. Group by theme, not by which agent found it.

Mark hand-rolled UI that duplicates a GRC component as a **designer flag**, so it can go to UX as well as the author.

## Step 7 — Suggest a next step

In PR and Branch mode, after the report, add one line, `**Next step:** …`, offering the action that fits whose code it is (Step 0). It's an offer: don't edit or comment until the user says yes. If there are no 🔴 or 🟡 findings, skip this line, except on someone else's PR, where you may offer to post a short "no design issues" comment. In Local mode, end with the report.

| Whose code | Offer |
|---|---|
| **Own PR** or **own code** (Branch) | Apply the fixes |
| **Someone else's PR** | Post the findings as a review on the PR |

**Apply the fixes** (after the user says yes):
- Fix every 🔴. For 🟡, ask which ones to take; don't guess intent.
- Only touch lines in scope (*Scope*). Never edit someone else's PR branch.
- Run the package's lint, typecheck, and tests on what you changed, and report the results.
- Don't commit or push unless asked.

**Post a review** (outward-facing, so draft it first):
1. Draft **one** review, not separate comments:
   - **Inline comments** on the exact `path` and `line` (RIGHT side of the diff) for each finding. Each one leads with the severity in bold (**Must fix** / **Worth discussing**), then the rule and its source, then the fix (a ```` ```suggestion ```` block where it's short).
   - **The body:** a one-line summary, then any finding that can't anchor on a diff line. Leave out ℹ️.
   - Collegial and specific. No review-tool or agent jargon.
2. Show the user the full draft (body plus every inline comment with its `file:line`) and ask whether to post it. Default event is `COMMENT`; use `REQUEST_CHANGES` or `APPROVE` only if the user says so.
3. Post it as one review:
   ```bash
   gh api repos/Workiva/ts-grc/pulls/<PR>/reviews --input "$WORK/review.json"
   ```
   `review.json` is `{ "commit_id": "<headRefOid>", "event": "COMMENT", "body": "...", "comments": [{ "path": "...", "line": N, "side": "RIGHT", "body": "..." }] }`. A comment on a line outside the diff fails the whole request; move it into the body instead.
4. Report the review's URL.

Clean up with `rm -rf "$WORK"` when the review is finished and no next step is pending; keep it while one is, since posting needs `$WORK`.
