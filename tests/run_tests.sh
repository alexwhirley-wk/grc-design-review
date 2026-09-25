#!/usr/bin/env bash
# Regression tests for grc-design-review. Run after any edit to the skill or scanner:
#   bash tests/run_tests.sh
# Deterministic only — the LLM-level check is tests/fixtures/audit_rules.tsx + tests/AUDIT_EXPECTED.md (run manually).
set -uo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

echo "1. Scanner fixtures"
python3 - "$DIR" <<'PY' || fail=1
import json, subprocess, sys, os
d = sys.argv[1]
expected = json.load(open(f"{d}/tests/expected.json"))
bad = 0
for name, exp in expected.items():
    path = f"{d}/tests/fixtures/{name}"
    out = subprocess.run(["python3", f"{d}/scripts/custom_styling_check.py", path, "--json", "--docs", f"{d}/tests/fixtures/docs"], capture_output=True, text=True).stdout
    got = sorted([f["line"], f["severity"], f["check"]] for f in json.loads(out))
    exp = sorted(exp)
    if got == exp:
        print(f"   PASS {name} ({len(got)} findings)")
    else:
        bad = 1
        print(f"   FAIL {name}")
        for x in exp:
            if x not in got: print(f"      missing: {x}")
        for x in got:
            if x not in exp: print(f"      unexpected: {x}")
sys.exit(bad)
PY

echo "2. Scanner exit codes"
python3 "$DIR/scripts/custom_styling_check.py" "$DIR/tests/fixtures/scanner_clean.tsx" >/dev/null && echo "   PASS clean → 0" || { echo "   FAIL clean should exit 0"; fail=1; }
python3 "$DIR/scripts/custom_styling_check.py" "$DIR/tests/fixtures/scanner_violations.tsx" >/dev/null && { echo "   FAIL violations should exit 1"; fail=1; } || echo "   PASS violations → 1"

echo "2b. Diff awareness (--diff tags only added lines)"
got=$(python3 "$DIR/scripts/custom_styling_check.py" "$DIR/tests/fixtures/scanner_violations.tsx" --json --docs "$DIR/tests/fixtures/docs" --diff "$DIR/tests/fixtures/partial.patch" \
  | python3 -c "import json,sys; print(sorted(f['line'] for f in json.load(sys.stdin) if f['in_diff']))")
[ "$got" = "[13, 20]" ] && echo "   PASS" || { echo "   FAIL got $got, expected [13, 20]"; fail=1; }
got=$(python3 "$DIR/scripts/custom_styling_check.py" "$DIR/tests/fixtures/scanner_violations.tsx" --json --docs "$DIR/tests/fixtures/docs" --diff "$DIR/tests/fixtures/partial.patch" --changed-only \
  | python3 -c "import json,sys; print(sorted(f['line'] for f in json.load(sys.stdin)))")
[ "$got" = "[13, 20]" ] && echo "   PASS --changed-only reports only changed lines" || { echo "   FAIL --changed-only got $got"; fail=1; }
python3 "$DIR/scripts/custom_styling_check.py" /definitely/missing >/dev/null 2>&1; [ $? -eq 2 ] && echo "   PASS missing path → exit 2" || { echo "   FAIL missing path should exit 2"; fail=1; }

echo "2c. Drift guard (a check whose source rule disappears gets disabled)"
TMPD=$(mktemp -d); cp -R "$DIR/tests/fixtures/docs/." "$TMPD/"
sed -i.bak 's/No raw hex, no MUI theme strings/Colors come from tokens/' "$TMPD/documentation/DESIGN.md"
out=$(python3 "$DIR/scripts/custom_styling_check.py" --docs "$TMPD" --rules); rc=$?
dis=$(echo "$out" | python3 -c "import json,sys; print(list(json.load(sys.stdin)['disabled']))")
[ $rc -eq 1 ] && [ "$dis" = "['raw-color']" ] && echo "   PASS raw-color disabled (exit 1) when its rule is reworded" || { echo "   FAIL drift guard: rc=$rc disabled=$dis"; fail=1; }
rm -rf "$TMPD"

echo "2d. Copy extractor"
got=$(python3 "$DIR/scripts/extract_copy.py" "$DIR/tests/fixtures/copy_messages.tsx" --json | python3 -c "import json,sys; print([m['text'] for m in json.load(sys.stdin)])")
exp="['Import {count} steps?', \"Couldn't update the control\", 'Loading control data — please wait', 'Multi line message', \"It's escaped\"]"
[ "$got" = "$exp" ] && echo "   PASS 5 message forms extracted" || { echo "   FAIL got $got"; fail=1; }

echo "3. Portability (no machine-specific paths in shipped files)"
if grep -rnE --exclude-dir=__pycache__ "/Users/|Obsidian|alexwhirley" "$DIR/SKILL.md" "$DIR/scripts" >/dev/null; then
  grep -rnE --exclude-dir=__pycache__ "/Users/|Obsidian|alexwhirley" "$DIR/SKILL.md" "$DIR/scripts" | sed 's/^/   FAIL /'; fail=1
else echo "   PASS"; fi

echo "4. Prerequisites"
for c in gh jq python3; do command -v $c >/dev/null && echo "   PASS $c installed" || { echo "   FAIL $c missing"; fail=1; }; done
gh auth status >/dev/null 2>&1 && echo "   PASS gh authenticated" || { echo "   FAIL gh not authenticated (gh auth login)"; fail=1; }
gh api repos/Workiva/ts-grc --jq .full_name >/dev/null 2>&1 && echo "   PASS ts-grc access" || { echo "   FAIL no access to Workiva/ts-grc"; fail=1; }

echo "5. Live doc fetch (the doc paths still exist on master)"
W=$(mktemp -d)
if bash "$DIR/scripts/fetch_context.sh" docs "$W" >/dev/null 2>&1 \
   && [ -s "$W/documentation/DESIGN.md" ] && [ -s "$W/packages/component-library/DESIGN.md" ] \
   && grep -q "Design Tokens" "$W/AGENTS.design-tokens.md" && [ -s "$W/MANIFEST_INDEX.txt" ]; then
  echo "   PASS ($(wc -l < "$W/MANIFEST_INDEX.txt" | tr -d ' ') MANIFESTs fetched)"
else echo "   FAIL — a doc moved or was renamed in ts-grc; update fetch_context.sh"; fail=1; fi

echo "5b. Content style guide reachable"
src=$(grep "content style guide" "$W/SOURCES.txt")
case "$src" in
  *UNAVAILABLE*) echo "   FAIL $src"; fail=1 ;;
  *FALLBACK*) echo "   WARN $src — copy is checked against Unify's content docs instead" ;;
  *) echo "   PASS $(echo "$src" | sed 's/^ *//')" ;;
esac

echo "6. Live rule sources (every doc-backed scanner check still matches today's docs)"
rules=$(python3 "$DIR/scripts/custom_styling_check.py" --docs "$W" --rules); rc=$?
if [ $rc -eq 0 ]; then echo "   PASS all cited rules found on master"
else echo "$rules" | python3 -c "import json,sys; [print(f'   FAIL {k}: {v}') for k,v in json.load(sys.stdin)['disabled'].items()]"
  echo "   → The docs changed. Update or remove that check's RULE_SOURCES entry in scripts/custom_styling_check.py."; fail=1; fi
echo "$rules" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"   INFO {d['tokens']} semantic tokens loaded, {len(d['deprecated_tokens'])} deprecated\")"
[ "$(echo "$rules" | python3 -c "import json,sys; print(json.load(sys.stdin)['tokens'])")" -gt 50 ] || { echo "   FAIL token catalog missing or unparseable — check semantic.ts path/format"; fail=1; }
echo "$rules" | python3 -c "import json,sys; d=json.load(sys.stdin)['deprecated']; print(f'   INFO {len(d)} deprecation(s) derived from MANIFESTs: ' + ', '.join(x['component']+('.'+x['prop'] if x['prop'] else '') for x in d))"
rm -rf "$W"

echo; [ $fail -eq 0 ] && echo "ALL PASS" || echo "FAILURES ABOVE"
exit $fail
