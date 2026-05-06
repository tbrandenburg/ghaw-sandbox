#!/usr/bin/env bats

# Agent prompt smoke tests
# Validates that command prompts and agent files have proper YAML frontmatter

setup() {
  REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

# Check that a file has YAML frontmatter delimited by ---
has_frontmatter() {
  local file="$1"
  local line_count
  line_count=$(head -n 1 "$file" | grep -c '^---$' || true)
  [ "$line_count" -eq 1 ]
}

# Check that frontmatter contains a specific key
has_frontmatter_key() {
  local file="$1"
  local key="$2"
  # Extract content between first --- and second ---
  sed -n '2,/^---$/p' "$file" | grep -q "^${key}:"
}

@test "all command prompts have valid YAML frontmatter" {
  cd "$REPO_ROOT"
  local failures=0
  for f in .opencode/commands/*.md; do
    if [ ! -f "$f" ]; then
      continue
    fi
    if ! head -n 1 "$f" | grep -q '^---$'; then
      echo "FAIL: $f missing frontmatter opening ---" >&2
      failures=$((failures + 1))
    fi
    if ! has_frontmatter_key "$f" "description"; then
      echo "FAIL: $f missing 'description' in frontmatter" >&2
      failures=$((failures + 1))
    fi
  done
  [ "$failures" -eq 0 ]
}

@test "all agent files have valid YAML frontmatter with description" {
  cd "$REPO_ROOT"
  local failures=0
  for f in .opencode/agent/*.md; do
    if [ ! -f "$f" ]; then
      continue
    fi
    if ! head -n 1 "$f" | grep -q '^---$'; then
      echo "FAIL: $f missing frontmatter opening ---" >&2
      failures=$((failures + 1))
    fi
    if ! has_frontmatter_key "$f" "description"; then
      echo "FAIL: $f missing 'description' in frontmatter" >&2
      failures=$((failures + 1))
    fi
  done
  [ "$failures" -eq 0 ]
}

@test "RELEASE_NOTES.md has structured sections" {
  cd "$REPO_ROOT"
  [ -f "RELEASE_NOTES.md" ]
  grep -q "^## Features" RELEASE_NOTES.md
  grep -q "^## Fixes" RELEASE_NOTES.md
  grep -q "^## Breaking Changes" RELEASE_NOTES.md
}
