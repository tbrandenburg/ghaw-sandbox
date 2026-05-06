#!/usr/bin/env bats

# Workflow structural validation tests
# Validates that workflow YAML files contain required structural keys

setup() {
  REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

# Check that a YAML file contains a top-level key
has_yaml_key() {
  local file="$1"
  local key="$2"
  grep -q "^${key}:" "$file"
}

@test "all workflows have name, on, and jobs keys" {
  cd "$REPO_ROOT"
  local failures=0
  for f in .github/workflows/*.yml; do
    if [ ! -f "$f" ]; then
      continue
    fi
    if ! has_yaml_key "$f" "name"; then
      echo "FAIL: $f missing 'name' key" >&2
      failures=$((failures + 1))
    fi
    if ! has_yaml_key "$f" "on"; then
      echo "FAIL: $f missing 'on' key" >&2
      failures=$((failures + 1))
    fi
    if ! has_yaml_key "$f" "jobs"; then
      echo "FAIL: $f missing 'jobs' key" >&2
      failures=$((failures + 1))
    fi
  done
  [ "$failures" -eq 0 ]
}

@test "core-opencode-run.yml declares required inputs" {
  cd "$REPO_ROOT"
  local f=".github/workflows/core-opencode-run.yml"
  [ -f "$f" ]
  grep -q "inputs:" "$f"
}

@test "CI workflow has lint job" {
  cd "$REPO_ROOT"
  grep -q "lint:" .github/workflows/ci.yml
}

@test "no workflow files are empty" {
  cd "$REPO_ROOT"
  local failures=0
  for f in .github/workflows/*.yml; do
    if [ ! -f "$f" ]; then
      continue
    fi
    if [ ! -s "$f" ]; then
      echo "FAIL: $f is empty" >&2
      failures=$((failures + 1))
    fi
  done
  [ "$failures" -eq 0 ]
}
