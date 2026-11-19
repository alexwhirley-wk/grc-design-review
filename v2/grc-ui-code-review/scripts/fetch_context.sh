#!/usr/bin/env bash
# fetch_context.sh — gather the ts-grc docs grc-ui-code-review checks against, plus a PR's changed files.
#
# The docs come from the ts-grc checkout under review whenever there is one ("local"), so the skill
# reads only the repository it is reviewing. "docs" fetches the same files from master on GitHub, and
# is the fallback when there's no checkout (for example, reviewing a PR from another directory).
#
# Usage:
#   fetch_context.sh local <out_dir> <ts-grc checkout>    # copy docs + MANIFESTs + token catalog from a checkout
#   fetch_context.sh docs <out_dir>                       # same files, fetched from ts-grc master
#   fetch_context.sh manifests <out_dir> <Name> [...]     # print local paths of specific components' MANIFESTs
#   fetch_context.sh pr <out_dir> <pr>                    # PR head versions of changed .ts/.tsx files + pr.diff
#                                                         #   <pr> = number, #number, or full PR URL
#
# Both "local" and "docs" write the same layout:
#   SOURCES.txt, documentation/DESIGN.md, packages/component-library/DESIGN.md, AGENTS.md,
#   AGENTS.design-tokens.md, MANIFEST_INDEX.txt, every component MANIFEST, tokens/semantic.ts
#
# Requires: git for "local"; gh (authenticated with access to Workiva/ts-grc), jq, base64 for the rest.

set -euo pipefail

REPO="Workiva/ts-grc"
REF="master"
DOCS=(documentation/DESIGN.md packages/component-library/DESIGN.md AGENTS.md)
TOK=packages/component-library/src/theme/tokens/semantic.ts
MANIFEST_RE='^packages/component-library/src/.*\\.MANIFEST\\.md$'

fetch_file() { # <repo_path> <dest> [ref]
  mkdir -p "$(dirname "$2")"
  gh api "repos/$REPO/contents/$1?ref=${3:-$REF}" --jq .content | base64 --decode > "$2"
}

extract_tokens_section() { # <out_dir>: keep only AGENTS.md → Design Tokens (the scanner cites it)
  awk '/^### Design Tokens/{f=1; print; next} f && /^##+ /{exit} f' "$1/AGENTS.md" > "$1/AGENTS.design-tokens.md"
}

cmd="${1:?usage: fetch_context.sh local|docs|manifests|pr <out_dir> ...}"
out="${2:?out_dir required}"
shift 2
mkdir -p "$out"

case "$cmd" in
  local)
    src="${1:?ts-grc checkout path required}"
    git -C "$src" remote get-url origin 2>/dev/null | grep -q 'Workiva/ts-grc' \
      || { echo "ERROR: $src is not a Workiva/ts-grc checkout" >&2; exit 1; }
    head=$(git -C "$src" log -1 --format='%h (%cd)' --date=short)
    branch=$(git -C "$src" branch --show-current 2>/dev/null || true)
    behind=$(git -C "$src" rev-list --count HEAD..origin/master 2>/dev/null || echo "?")
    {
      echo "ts-grc checkout ${branch:-detached} @ $head, $behind commit(s) behind origin/master"
      for p in "${DOCS[@]}"; do
        [ -s "$src/$p" ] || { echo "  $p: MISSING in checkout"; continue; }
        mkdir -p "$out/$(dirname "$p")"; cp "$src/$p" "$out/$p"
        echo "  $p — last changed $(git -C "$src" log -1 --format='%h %cd' --date=short -- "$p")"
      done
    } > "$out/SOURCES.txt"
    [ -s "$out/AGENTS.md" ] && extract_tokens_section "$out"
    (cd "$src" && git ls-files 'packages/component-library/src/*.MANIFEST.md') > "$out/MANIFEST_INDEX.txt"
    while read -r p; do mkdir -p "$out/$(dirname "$p")"; cp "$src/$p" "$out/$p"; done < "$out/MANIFEST_INDEX.txt"
    echo "  $(wc -l < "$out/MANIFEST_INDEX.txt" | tr -d ' ') component MANIFESTs" >> "$out/SOURCES.txt"
    if [ -s "$src/$TOK" ]; then
      mkdir -p "$out/tokens"; cp "$src/$TOK" "$out/tokens/semantic.ts"
      echo "  $TOK — last changed $(git -C "$src" log -1 --format='%h %cd' --date=short -- "$TOK")" >> "$out/SOURCES.txt"
    else
      echo "  token catalog: UNAVAILABLE ($TOK not found)" >> "$out/SOURCES.txt"
    fi
    cat "$out/SOURCES.txt"
    ;;

  docs)
    sha=$(gh api "repos/$REPO/commits/$REF" --jq '.sha[0:7] + " (" + .commit.committer.date[0:10] + ")"')
    {
      echo "ts-grc $REF @ $sha (fetched from GitHub; no local checkout)"
      for p in "${DOCS[@]}"; do
        fetch_file "$p" "$out/$p"
        last=$(gh api "repos/$REPO/commits?path=$p&per_page=1" --jq '.[0] | .sha[0:7] + " " + .commit.committer.date[0:10]')
        echo "  $p — last changed $last"
      done
    } > "$out/SOURCES.txt"
    extract_tokens_section "$out"
    gh api "repos/$REPO/git/trees/$REF?recursive=1" --jq ".tree[].path | select(test(\"$MANIFEST_RE\"))" \
      > "$out/MANIFEST_INDEX.txt"
    i=0
    while read -r p; do
      (fetch_file "$p" "$out/$p") & i=$((i+1)); [ $((i % 8)) -eq 0 ] && wait
    done < "$out/MANIFEST_INDEX.txt"
    wait
    echo "  $(wc -l < "$out/MANIFEST_INDEX.txt" | tr -d ' ') component MANIFESTs fetched" >> "$out/SOURCES.txt"
    if fetch_file "$TOK" "$out/tokens/semantic.ts" 2>/dev/null && [ -s "$out/tokens/semantic.ts" ]; then
      last=$(gh api "repos/$REPO/commits?path=$TOK&per_page=1" --jq '.[0] | .sha[0:7] + " " + .commit.committer.date[0:10]')
      echo "  $TOK — last changed $last" >> "$out/SOURCES.txt"
    else
      echo "  token catalog: UNAVAILABLE ($TOK not found)" >> "$out/SOURCES.txt"
    fi
    cat "$out/SOURCES.txt"
    ;;

  manifests)
    [ -f "$out/MANIFEST_INDEX.txt" ] || { echo "run 'local' or 'docs' first" >&2; exit 1; }
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
