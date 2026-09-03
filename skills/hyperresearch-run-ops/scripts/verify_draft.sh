#!/usr/bin/env bash
# Verify a hyperresearch step-10 draft before step 11 (synthesis).
# Usage: verify_draft.sh <draft.md> [<vault_root>]
# Checks: length in range (2000-5000 words), H2 sections listed (check order
# yourself against prompt-decomposition.json required_section_headings),
# zero pipeline vocabulary, and every [[wikilink]] resolves to a vault note.
# Exit code 0 = all checks passed; 1 = at least one check failed.
set -u
DRAFT="${1:?usage: verify_draft.sh <draft.md> [<vault_root>]}"
ROOT="${2:-$HOME}"
NOTES="$ROOT/research/notes"
FAIL=0

words=$(wc -w < "$DRAFT")
echo "words: $words (target 2000-5000)"
if [ "$words" -ge 2000 ] && [ "$words" -le 5000 ]; then
  echo "  length: ok"
else
  echo "  ! LENGTH OUT OF RANGE"; FAIL=1
fi

echo "-- H2 sections (verify order vs required_section_headings):"
if grep -n "^## " "$DRAFT"; then :; else echo "  ! NO H2 SECTIONS"; FAIL=1; fi

echo "-- pipeline vocabulary (must be 0):"
if grep -ci "hyperresearch\|evidence digest\|locus\|committed" "$DRAFT"; then
  echo "  ! PIPELINE VOCABULARY PRESENT"; FAIL=1
else
  echo "  0 (ok)"
fi

echo "-- wikilinks:"
total=0
while read -r id; do
  [ -z "$id" ] && continue
  total=$((total+1))
  if [ -f "$NOTES/$id.md" ]; then
    echo "  ok   $id"
  else
    echo "  !! MISSING NOTE  $id"; FAIL=1
  fi
done < <(grep -oE '\[\[[a-zA-Z0-9_-]+\]\]' "$DRAFT" | sort -u | tr -d '[]')
echo "  $total unique wikilinks checked"

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: draft verified"
else
  echo "FAIL: see issues above"
fi
exit "$FAIL"
