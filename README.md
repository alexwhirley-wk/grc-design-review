# grc-design-review

A Claude Code skill that reviews `Workiva/ts-grc` front-end code against the **current** GRC design guidance. On every run it fetches:
- both `DESIGN.md` files, the Design Tokens section of `AGENTS.md`, every component MANIFEST, and the semantic token catalog, all from ts-grc `master`
- the Content Strategy team's style guide, used for UI copy

No design rules are hand-copied into the skill, so it stays in step with the docs.

## Install

```bash
git clone git@github.com:alexwhirley-wk/grc-design-review.git ~/.claude/skills/grc-design-review
bash ~/.claude/skills/grc-design-review/tests/run_tests.sh   # checks prerequisites + access
```

**Prerequisites:**
- `gh`, logged in with access to `Workiva/ts-grc`. Access to `Workiva/Content_Strategy_Repo` is also recommended; without it, copy is checked against Unify's content docs instead.
- `jq`
- `python3`

## Use

In Claude Code:

| Command | Reviews |
|---|---|
| `/grc-design-review 11794` (or a PR URL) | a PR |
| `/grc-design-review packages/foo/src` | local files or a directory |
| `/grc-design-review` | your current branch's changes vs `origin/master` (run it from a ts-grc checkout) |

The report always has four sections: 🔴 Violations, 🟡 Concerns, 🟢 Looks good, and ℹ️ Not checked. Each finding cites its source: a doc section, a MANIFEST, the style guide, a UX-audit finding, or "heuristic".

## What's inside

- `SKILL.md`: the review process, severity rubric, embedded UX-audit rules, and report format
- `scripts/fetch_context.sh`: fetches the docs, MANIFESTs, token catalog, style guide, and PR files through `gh`
- `scripts/custom_styling_check.py`: the deterministic scanner. Its doc-backed checks cite the exact rule they enforce and switch themselves off if that rule disappears from the docs.
- `scripts/extract_copy.py`: lists every user-facing message, for the copy pass
- `tests/`: the regression suite (`run_tests.sh`), the planted-issue answer key, and the backtest against human reviews

## Updating

After changing anything, run `bash tests/run_tests.sh`. It also fails if a doc rule the scanner cites has changed on ts-grc master, and tells you which check to update.
