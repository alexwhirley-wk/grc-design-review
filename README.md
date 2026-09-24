# 🎀✨ grc-design-review

> *Your friendly neighbourhood design reviewer, for anyone who's ever shipped `borderRadius: 4` and felt a little guilty about it.*

`grc-design-review` is a **Claude Code skill** that reads your ts-grc front-end code and tells you, kindly but honestly, where it drifts from the GRC design system. Think of it as a UX teammate who has memorised every design doc and never gets tired of saying "use a token for that."

```
   ╭─────────────────────────────────╮
   │  🔴  must fix                   │
   │  🟡  worth a chat               │
   │  🟢  nice work, keep it up      │
   │  ℹ️   stuff I didn't look at    │
   │        ✿ ♡ ✿                   │
   ╰─────────────────────────────────╯
```

---

## 🌸 What it does

Point it at a **PR**, a **folder**, or **your current branch**. It will:

1. 💌 **Grab the latest rules.** It fetches them fresh every run, so it never works from last month's docs.
2. 🪄 **Run a quick scanner.** A fast, repeatable pass for the things that can be checked mechanically: raw hex colours, made-up token names, `@mui` imports, deprecated props, and dialogs where Esc does nothing.
3. 🔮 **Read your code like a reviewer would.** It checks the things a scanner can't: loading and error states, disabled buttons, focus that gets lost after a dialog closes, and copy that doesn't match the style guide.
4. 💅 **Write you a report** in the 🔴🟡🟢ℹ️ format. Every finding says which rule it's based on, so you can check it yourself.

It only points out problems; it never edits your code, pushes, or comments on your PR.

---

## 👛 Where it gets its rules

Nothing is hand-copied into the skill. Every run pulls the current version of each of these:

| | Source | What it's used for |
|---|---|---|
| 🌷 | `ts-grc` → `documentation/DESIGN.md` | Product-wide design rules: buttons, dialogs, loading and error states, empty values, accessibility |
| 🧸 | `ts-grc` → `packages/component-library/DESIGN.md` | Component rules: layered containers, borders, radius, when to wrap or theme or build, import rules |
| 💎 | `ts-grc` → `AGENTS.md` (Design Tokens) | The `getToken()` rules: semantic tokens only, no raw hex, no `'error.main'` |
| 🍬 | `ts-grc` → `theme/tokens/semantic.ts` | The real token catalog, so it can tell whether `radius/card` actually exists (it doesn't 👀) and which tokens are deprecated |
| 💝 | `ts-grc` → every component `*.MANIFEST.md` | When to use each GRC component, its "Don't" list, and deprecated props |
| 🦢 | `Content_Strategy_Repo` → `style-guide/` | The content style guide: voice and tone, "Couldn't [action]" messages, error messages that say how to fix things. Falls back to Unify's content docs if you don't have access |
| 🪞 | Skye Selbiger's GRC UX audit | A small set of patterns that aren't written down in ts-grc yet: button variants, drawer layout, empty states, where the AI sparkle icon goes. This is the only part stored inside the skill, and each rule cites its audit finding number |

> 🦄 **It won't enforce outdated rules.** Each scanner check that enforces a written rule quotes the exact sentence it relies on. If that sentence is ever removed or reworded in the docs, the check **switches itself off** and the report says so.

---

## 🧁 What the output looks like

Here's a trimmed example from a real run:

```markdown
**PR #11794 — CPM Import - Full Page**
*Author: jimtremper-wk | Base: master*
*Rules: ts-grc master @ 038e1ec (2026-09-24) — DESIGN.md ×2, AGENTS.md → Design Tokens,
 30 MANIFESTs, token catalog, content style guide @ 5d932ea*

### 🔴 Violations (must fix)
- `ImportPerformanceDetailsPage.tsx:34`: `defaultExpanded` on `GrcBreadcrumbs`.
  Source: GrcBreadcrumbs MANIFEST → Don't ("deprecated and ignored"). Fix: delete the prop.
- `usePerformanceDetailsImportValidation.ts:37`: if the query fails, the user sees
  "Loading control data — please wait" forever.
  Source: DESIGN.md → Section-scoped errors. Fix: show an inline error with a Retry button.

### 🟡 Concerns (worth discussing)
#### UI copy
Source: content style guide → patterns.md → Error messaging
- `performanceDetailsValidators.ts:14`: says what went wrong but not how to fix it.
  Try: `Control ID "{controlId}" isn't in this workspace. Check the ID and try again.`
- `usePerformanceDetailsImportData.ts:64`: shows an "internal control ID" to users.
  Source: voice-and-tone.md → Vocabulary ("Never expose … raw IDs")

### 🟢 Looks good
- The Mapping step warns after the fact instead of disabling Next. 💖
- One primary action on the results screen, and every string goes through react-intl.

### ℹ️ Not checked / notes
- Shared components this PR only *uses* (DataImportRoot, ImportExitConfirmationDialog)
  weren't reviewed.
```

**A few things are always true:**
- 🌈 **All four sections always appear**, in the same order. An empty one just says `None.`
- 🍓 **Every finding gives a `file:line`,** the rule it's based on, and what to change.
- 🫧 **Big sections get grouped by theme** (for example `#### Disabled controls`), so 12 Cancel-button fixes become one bullet.
- 🌼 **In PR mode, problems the PR didn't cause are labelled pre-existing,** so you're not asked to fix other people's code.
- 🩰 **Hand-built UI that duplicates a GRC component gets a designer flag,** so UX sees it too.

---

## 💕 Install

```bash
git clone git@github.com:alexwhirley-wk/grc-design-review.git ~/.claude/skills/grc-design-review
bash ~/.claude/skills/grc-design-review/tests/run_tests.sh
```

The test script checks your setup. You'll need:
- 🐱 `gh`, logged in with access to `Workiva/ts-grc`. Access to `Workiva/Content_Strategy_Repo` is also recommended.
- 🎀 `jq`
- 🌸 `python3`

## 🦋 Use

In Claude Code:

| Type this | To review |
|---|---|
| `/grc-design-review 11794` | a PR (a number, `#11794`, or the full URL all work) |
| `/grc-design-review packages/foo/src` | a file or folder |
| `/grc-design-review` | your branch's changes vs `origin/master` (run it from a ts-grc checkout) |

It runs start to finish without stopping to ask questions. The one exception: if you give it nothing to review, it asks what you'd like reviewed.

> 🐇 **Big folders get a lighter review.** The scanner and the copy check cover *every* file. The careful read, where it catches things like lost focus and swallowed errors, is capped at about 15 files per run. That's plenty for a normal PR. For a whole package (say, 100+ files), you'll get deeper results by reviewing a few subfolders one at a time:
> ```
> /grc-design-review packages/audit-planning-v2/src/components
> /grc-design-review packages/audit-planning-v2/src/timeline
> ```
> The ℹ️ section always lists which files got the careful read, so you can see what was left out.

---

## 💭 FAQ

**Is it always right?** Not always. When it flags something it's usually right: in blind tests against real human reviews, it made no wrong 🟡 calls in 63 checked. But it doesn't catch everything, and it can't see Figma or the running app. Treat it as a strong first pass, not as UX sign-off. 💗

**Why did it say something is 🔴?** Because the docs state that rule as a requirement ("must", "never", "always"). If a rule is phrased as a preference, it's 🟡.

**The docs changed. Do I need to update anything?** Usually not; it picks up changes on the next run. If the docs remove a rule the scanner was enforcing, `tests/run_tests.sh` fails and tells you which check to update.

**Can it fix things for me?** Not on its own. It only reviews. You can ask Claude to apply the fixes afterwards.

---

## 🎁 What's inside

```
grc-design-review/
├── SKILL.md                    # the review process and report format
├── scripts/
│   ├── fetch_context.sh        # fetches the docs, tokens, style guide, and PR files
│   ├── custom_styling_check.py # the scanner (checks tied to the docs, switches off if a rule disappears)
│   └── extract_copy.py         # collects every user-facing string for the copy review
└── tests/
    ├── run_tests.sh            # 🧪💗 run after any change
    ├── AUDIT_EXPECTED.md       # answer key for the planted-issue test file
    └── BACKTEST.md             # how it compares with real human reviews
```

<sub>Made with 🩷 and way too many `getToken()` calls.</sub>
