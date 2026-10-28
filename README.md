# 🎀 ✨ grc-design-review

> *Your friendly neighbourhood design reviewer, for anyone who's ever shipped `borderRadius: 4` and felt a little guilty about it.*

`grc-design-review` is a **Claude Code skill** that reads your ts-grc front-end code and tells you where it drifts from the GRC design system. Think of it as a UX teammate who has memorised every design doc and never gets tired of saying "use a token for that."

```
   ╭─────────────────────────────────╮
   │  🔴  must fix                   │
   │  🟡  worth a chat               │
   │  ℹ️   stuff I didn't look at    │
   ╰─────────────────────────────────╯
```

---

## ✨ What it does

Point it at a **PR**, a **folder**, or **your current branch**. It will:

1. **Grab the latest rules.** It fetches them fresh every run, so it never works from last month's docs.
2. **Run a quick scanner.** A fast, repeatable pass for the things that can be checked mechanically: raw hex colours, made-up token names, `@mui` imports, deprecated props, and dialogs where Esc does nothing.
3. **Send in four specialist reviewers, side by side.** Each one reads a single rule source in full and checks the things a scanner can't:
   - 🧭 **Product design** (`documentation/DESIGN.md`): loading and error states, dialog dismissal, disabled buttons, keyboard access
   - 🎨 **Component library and tokens**: surfaces, borders, imports, prop design, real token names
   - 📦 **MANIFESTs**: each touched component's "Don't" list, plus hand-built UI that a GRC component already covers
   - ✍️ **Content style guide**: every user-facing string, with replacement text
4. **Check their work.** It confirms every quoted rule really is in today's docs and that every finding sits on a line you changed. Then it merges duplicates and sets the final severity.
5. **Write you a report** in the 🔴🟡ℹ️ format. Every finding says which rule it's based on, so you can check it yourself.

6. **Suggest a next step** when you're reviewing a PR or branch:
   - 🛠️ **Your own PR or branch:** apply the fixes
   - 💬 **Someone else's PR:** post the findings as one review, with inline comments on the changed lines
   - A review of a file or folder just ends with the report.

It never edits your code, pushes, or comments on a PR until you say yes. Reviews are always shown to you as a full draft first.

---

## 🔮 Where it gets its rules

Nothing is hand-copied into the skill, and **every finding cites one of these documents**. If there's no rule in the docs, there's no comment. Every run pulls the current version of each of these:

| Source | What it's used for |
|---|---|
| `ts-grc` → `documentation/DESIGN.md` | Product-wide design rules: buttons, dialogs, loading and error states, empty values, accessibility |
| `ts-grc` → `packages/component-library/DESIGN.md` | Component rules: layered containers, borders, radius, when to wrap or theme or build, import rules |
| `ts-grc` → `AGENTS.md` (Design Tokens) | The `getToken()` rules: semantic tokens only, no raw hex, no `'error.main'` |
| `ts-grc` → `theme/tokens/semantic.ts` | The real token catalog, so it can tell whether `radius/card` actually exists (it doesn't 👀) and which tokens are deprecated |
| `ts-grc` → every component `*.MANIFEST.md` | When to use each GRC component, its "Don't" list, and deprecated props |
| `Content_Strategy_Repo` → `style-guide/` | The content style guide: voice and tone, "Couldn't [action]" messages, error messages that say how to fix things. Falls back to Unify's content docs if you don't have access |

> **It won't enforce outdated rules.** Each scanner check quotes the exact sentence it relies on. If that sentence is ever removed or reworded in the docs, the check **switches itself off** and the report says so.

---

## 🌸 What the output looks like

Every report has a short header followed by the same three sections, always in this order:

> **📋 Header.** Shows what was reviewed (a PR, a folder, or your branch), plus a **Rules** line recording exactly which version of each doc was used. That way you always know which rules a review was checked against.

> **🔴 Violations (must fix).** Things the docs state as **requirements**: rules that say "must", "never", "always", or "Don't", or give a stated standard like "Cancel is a text-variant button". These include token and import rules, deprecated props, and made-up token names.
>
>*e.g.* `Dialog.tsx:34`: the Cancel button is `outlined`. **Source:** DESIGN.md → *Primary action in a dialog footer*. **Fix:** use `variant="text"`.

> **🟡 Concerns (worth discussing).** Things the docs phrase as a **preference** ("prefer", "should", "discouraged"), plus anything that needs product or design context to judge. UI copy suggestions from the content style guide land here too, with replacement text you can paste in.
>
> *e.g.* `validators.ts:14`: the error says what went wrong but not how to fix it. **Try:** `Control ID "{id}" isn't in this workspace. Check the ID and try again.`

> **ℹ️ Not checked / notes.** What the review *didn't* cover: files it skipped, checks that couldn't run, and places where two documents disagree with each other.
>
> *e.g.* Shared components this PR only *uses* weren't reviewed.

**A few things are always true:**
- **All three sections always appear**, in the same order. An empty one just says `None.`
- **Every finding gives a `file:line`,** the rule it's based on, and what to change.
- **Big sections get grouped by theme** (for example `#### Disabled controls`), so 12 Cancel-button fixes become one bullet.
- **In PR mode, it only comments on lines the PR changed.** Existing code isn't reviewed, so you're never asked to fix someone else's work.
- **Hand-built UI that duplicates a GRC component gets a designer flag,** so UX sees it too.

---

## 💕 Install

```bash
git clone git@github.com:alexwhirley-wk/grc-design-review.git ~/.claude/skills/grc-design-review
bash ~/.claude/skills/grc-design-review/tests/run_tests.sh
```

The test script checks your setup. You'll need:
-  `gh`, logged in with access to `Workiva/ts-grc`. Access to `Workiva/Content_Strategy_Repo` is also recommended.
-  `jq`
-  `python3`

## 🦋 Use

In Claude Code:

| Type this | To review |
|---|---|
| `/grc-design-review 11794` | a PR (a number, `#11794`, or the full URL all work) |
| `/grc-design-review packages/foo/src` | a file or folder |
| `/grc-design-review` | your branch's changes vs `origin/master` (run it from a ts-grc checkout) |

It runs start to finish without stopping to ask questions. The one exception: if you give it nothing to review, it asks what you'd like reviewed.

> **It runs four reviewer agents in parallel,** so a run uses more tokens than a single pass would, but it finishes sooner and each reviewer has room to read its docs in full.

> **Big folders get a lighter review.** The scanner and the copy check cover *every* file. The careful read, where it catches things like lost focus and swallowed errors, is capped at about 30 files per run. That's plenty for a normal PR. For a whole package (say, 100+ files), you'll get deeper results by reviewing a few subfolders one at a time:
> ```
> /grc-design-review packages/audit-planning-v2/src/components
> /grc-design-review packages/audit-planning-v2/src/timeline
> ```
> The ℹ️ section always lists which files got the careful read, so you can see what was left out.

---

## 💭 FAQ

**Is it always right?** Not always. When it flags something it's usually right: in blind tests against real human reviews, it made no wrong 🟡 calls in 63 checked. But it doesn't catch everything, and it can't see Figma or the running app. Treat it as a strong first pass, not as UX sign-off.

**The docs changed. Do I need to update anything?** Usually not; it picks up changes on the next run. If the docs remove a rule the scanner was enforcing, `tests/run_tests.sh` fails and tells you which check to update.

**Can it fix things for me?** Yes, on your own code. At the end it offers to apply the fixes: all the 🔴s, plus whichever 🟡s you choose. It won't commit or push unless you ask.

---

## 🎁 What's inside

```
grc-design-review/
├── SKILL.md                    # the review process, the four reviewer briefs, and the report format
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
