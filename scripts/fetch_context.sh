#!/usr/bin/env bash
# fetch_context.sh — pull the latest ts-grc design docs (and optionally a PR's changed files)
# into a local working dir so the review always runs against current guidance.
#
# Usage:
#   fetch_context.sh docs <out_dir>                     # design docs + all component MANIFESTs
#   fetch_context.sh manifests <out_dir> <Name> [...]   # print local paths of specific components' MANIFESTs
#   fetch_context.sh pr <out_dir> <pr>                  # PR head versions of changed .ts/.tsx files + pr.diff
#                                                       #   <pr> = number, #number, or full PR URL
#
# Requires: gh (authenticated with access to Workiva/ts-grc), jq, base64.

set -euo pipefail

REPO="Workiva/ts-grc"
REF="master"

fetch_file() { # <repo_path> <dest> [ref]
  mkdir -p "$(dirname "$2")"
  gh api "repos/$REPO/contents/$1?ref=${3:-$REF}" --jq .content | base64 --decode > "$2"
}

cmd="${1:?usage: fetch_context.sh docs|manifests|pr <out_dir> ...}"
out="${2:?out_dir required}"
shift 2
mkdir -p "$out"

case "$cmd" in
  docs)
    sha=$(gh api "repos/$REPO/commits/$REF" --jq '.sha[0:7] + " (" + .commit.committer.date[0:10] + ")"')
    {
      echo "ts-grc $REF @ $sha"
      for p in documentation/DESIGN.md packages/component-library/DESIGN.md; do
        fetch_file "$p" "$out/$p"
        last=$(gh api "repos/$REPO/commits?path=$p&per_page=1" --jq '.[0] | .sha[0:7] + " " + .commit.committer.date[0:10]')
        echo "  $p — last changed $last"
      done
    } > "$out/SOURCES.txt"

    # Root AGENTS.md: keep only the Design Tokens section (the rest isn't design guidance).
    fetch_file AGENTS.md "$out/AGENTS.full.md"
    awk '/^### Design Tokens/{f=1; print; next} f && /^##+ /{exit} f' "$out/AGENTS.full.md" > "$out/AGENTS.design-tokens.md"
    rm "$out/AGENTS.full.md"
    echo "  AGENTS.md → Design Tokens section" >> "$out/SOURCES.txt"

    # Index of every component-library MANIFEST, so the reviewer knows what exists to suggest.
    gh api "repos/$REPO/git/trees/$REF?recursive=1" \
      --jq '.tree[].path | select(test("^packages/component-library/src/.*\\.MANIFEST\\.md$"))' \
      > "$out/MANIFEST_INDEX.txt"
    # Fetch every MANIFEST (parallel, ~3s) — the scanner derives deprecations from them.
    i=0
    while read -r p; do
      (fetch_file "$p" "$out/$p") & i=$((i+1)); [ $((i % 8)) -eq 0 ] && wait
    done < "$out/MANIFEST_INDEX.txt"
    wait
    echo "  $(wc -l < "$out/MANIFEST_INDEX.txt" | tr -d ' ') component MANIFESTs fetched" >> "$out/SOURCES.txt"
    # Semantic token catalog — lets the scanner flag unknown and deprecated token names.
    TOK=packages/component-library/src/theme/tokens/semantic.ts
    if fetch_file "$TOK" "$out/tokens/semantic.ts" 2>/dev/null && [ -s "$out/tokens/semantic.ts" ]; then
      last=$(gh api "repos/$REPO/commits?path=$TOK&per_page=1" --jq '.[0] | .sha[0:7] + " " + .commit.committer.date[0:10]')
      echo "  $TOK — last changed $last" >> "$out/SOURCES.txt"
    else
      echo "  token catalog: UNAVAILABLE ($TOK not found)" >> "$out/SOURCES.txt"
    fi

    # Content style guide (UI copy rules). Primary: the Content Strategy team's style guide.
    # Fallback: Unify's content docs (as shipped with the Unify MCP server).
    mkdir -p "$out/content"
    CS_REPO="Workiva/Content_Strategy_Repo"
    cs_ok=1
    for f in SKILL.md voice-and-tone.md patterns.md ui-component-patterns.md editorial-style.md; do
      gh api "repos/$CS_REPO/contents/style-guide/$f" --jq .content 2>/dev/null | base64 --decode > "$out/content/$f" 2>/dev/null
      [ -s "$out/content/$f" ] || cs_ok=0
    done
    if [ $cs_ok -eq 1 ]; then
      last=$(gh api "repos/$CS_REPO/commits?path=style-guide&per_page=1" --jq '.[0] | .sha[0:7] + " " + .commit.committer.date[0:10]')
      echo "  content style guide: $CS_REPO/style-guide — last changed $last" >> "$out/SOURCES.txt"
    else
      rm -f "$out/content/"*
      U_REPO="Workiva/unify-ai"; U_BASE="packages/unify-mcp-server/unify-md/generated"
      for f in foundations/content/voice-and-tone.md foundations/content/content-design.md \
               foundations/content/writing-for-everyone.md layouts/patterns/error-messaging.md; do
        gh api "repos/$U_REPO/contents/$U_BASE/$f" --jq .content 2>/dev/null | base64 --decode > "$out/content/$(basename "$f")" 2>/dev/null
      done
      if ls "$out/content/"*.md >/dev/null 2>&1 && [ -s "$out/content/voice-and-tone.md" ]; then
        echo "  content style guide: FALLBACK Unify content docs ($U_REPO) — no access to $CS_REPO" >> "$out/SOURCES.txt"
      else
        rm -f "$out/content/"*
        echo "  content style guide: UNAVAILABLE (no access to $CS_REPO or $U_REPO)" >> "$out/SOURCES.txt"
      fi
    fi
    cat "$out/SOURCES.txt"
    echo "wrote: $out/documentation/DESIGN.md, $out/packages/component-library/DESIGN.md, $out/AGENTS.design-tokens.md, $out/MANIFEST_INDEX.txt, every MANIFEST under $out/packages/component-library/src/, the token catalog at $out/tokens/semantic.ts, and the content style guide under $out/content/ (if accessible)"
    ;;

  manifests)
    [ -f "$out/MANIFEST_INDEX.txt" ] || { echo "run 'docs' first" >&2; exit 1; }
    for name in "$@"; do
      path=$(grep -E "/${name}\.MANIFEST\.md$" "$out/MANIFEST_INDEX.txt" | head -1 || true)
      if [ -n "$path" ]; then
        [ -s "$out/$path" ] || fetch_file "$path" "$out/$path"
        echo "$out/$path"
      else
        echo "no MANIFEST for $name"
      fi
    done
    ;;

  pr)
    pr="${1:?pr_number, #number, or PR URL required}"
    meta=$(gh pr view "$pr" --repo "$REPO" --json number,headRefOid,files) \
      || { echo "ERROR: could not load PR '$pr' from $REPO (bad number, or no access)" >&2; exit 1; }
    num=$(jq -r .number <<<"$meta"); head=$(jq -r .headRefOid <<<"$meta")
    jq -r '.files[].path' <<<"$meta" > "$out/pr_all_files.txt"
    gh pr diff "$pr" --repo "$REPO" > "$out/pr.diff"
    echo "PR #$num head ${head:0:10} — diff saved to $out/pr.diff"
    skip_re='\.(test|spec|stories)\.|__generated__|\.d\.ts$'
    grep -vE '\.tsx?$' "$out/pr_all_files.txt" | sed 's/^/  skipped (non-TS): /' || true
    grep -E '\.tsx?$' "$out/pr_all_files.txt" | grep -E "$skip_re" | sed 's/^/  skipped (test\/story\/generated): /' || true
    ui=$(grep -E '\.tsx?$' "$out/pr_all_files.txt" | grep -vE "$skip_re" || true)
    if [ -z "$ui" ]; then
      echo "NO_UI_FILES: PR #$num changes no reviewable .ts/.tsx files"
      exit 0
    fi
    n=0
    while read -r p; do
      if fetch_file "$p" "$out/pr/$p" "$head" 2>/dev/null; then echo "  $p"; n=$((n+1)); else echo "  skipped (deleted in PR): $p"; fi
    done <<<"$ui"
    echo "fetched $n UI file(s) to $out/pr/"
    ;;

  *) echo "unknown command: $cmd" >&2; exit 1 ;;
esac
