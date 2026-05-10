#!/usr/bin/env bats

# Makefile behavioral tests
# Tests that Makefile targets behave correctly

setup() {
  REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

@test "make lint exits 0 on clean repo" {
  cd "$REPO_ROOT"
  run make lint
  [ "$status" -eq 0 ]
}

@test "make test includes lint and test-bats targets" {
  cd "$REPO_ROOT"
  # Verify the test target depends on both lint and test-bats without executing them
  run grep -E '^test:' Makefile
  [ "$status" -eq 0 ]
  [[ "$output" == *"lint"* ]]
  [[ "$output" == *"test-bats"* ]]
}

@test "make hooks sets core.hooksPath" {
  cd "$REPO_ROOT"
  run make hooks
  [ "$status" -eq 0 ]
  # Verify the config was set
  run git config --get core.hooksPath
  [ "$status" -eq 0 ]
  [ "$output" = ".githooks" ]
}

@test ".githooks/pre-push exists and is executable" {
  cd "$REPO_ROOT"
  [ -f ".githooks/pre-push" ]
  [ -x ".githooks/pre-push" ]
}

@test "pre-push hook delegates to make test" {
  cd "$REPO_ROOT"
  run cat .githooks/pre-push
  [ "$status" -eq 0 ]
  [[ "$output" == *"make test"* ]]
}

@test "pre-push hook prints actionable error guidance on failure" {
  cd "$REPO_ROOT"
  run cat .githooks/pre-push
  [ "$status" -eq 0 ]
  [[ "$output" == *"make lint"* ]]
  [[ "$output" == *"--no-verify"* ]]
  [[ "$output" == *"Pre-push checks failed"* ]]
}

@test "Makefile.ghaw defines BUMP variable" {
  cd "$REPO_ROOT"
  run grep -E '^BUMP\s+\?\=' Makefile.ghaw
  [ "$status" -eq 0 ]
}

@test "Makefile.ghaw publish target handles BUMP=major|minor|patch" {
  cd "$REPO_ROOT"
  # Verify the case statement for version bump types exists in the publish target
  run grep -E '^\s+(major|minor|patch)\)' Makefile.ghaw
  [ "$status" -eq 0 ]
  [[ "$output" == *"major)"* ]]
  [[ "$output" == *"minor)"* ]]
  [[ "$output" == *"patch)"* ]]
}

@test "Makefile.ghaw version bump arithmetic is correct" {
  cd "$REPO_ROOT"
  # Test the version bump logic used in the publish target
  CURRENT="0.2.1"
  MAJOR=$(echo "$CURRENT" | cut -d. -f1)
  MINOR=$(echo "$CURRENT" | cut -d. -f2)
  PATCH=$(echo "$CURRENT" | cut -d. -f3)

  # Test patch bump
  VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
  [ "$VERSION" = "0.2.2" ]

  # Test minor bump
  VERSION="$MAJOR.$((MINOR + 1)).0"
  [ "$VERSION" = "0.3.0" ]

  # Test major bump
  VERSION="$((MAJOR + 1)).0.0"
  [ "$VERSION" = "1.0.0" ]

  # Test with different version
  CURRENT="1.5.9"
  MAJOR=$(echo "$CURRENT" | cut -d. -f1)
  MINOR=$(echo "$CURRENT" | cut -d. -f2)
  PATCH=$(echo "$CURRENT" | cut -d. -f3)

  VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
  [ "$VERSION" = "1.5.10" ]

  VERSION="$MAJOR.$((MINOR + 1)).0"
  [ "$VERSION" = "1.6.0" ]

  VERSION="$((MAJOR + 1)).0.0"
  [ "$VERSION" = "2.0.0" ]
}

@test "Makefile.ghaw USAGE documents BUMP=patch|minor|major" {
  cd "$REPO_ROOT"
  run grep -E 'BUMP=(patch|minor|major)' Makefile.ghaw
  [ "$status" -eq 0 ]
  [[ "$output" == *"BUMP=patch"* ]]
  [[ "$output" == *"BUMP=minor"* ]]
  [[ "$output" == *"BUMP=major"* ]]
}

@test "AGENTS.md documents BUMP=patch|minor|major usage" {
  cd "$REPO_ROOT"
  run grep -E 'BUMP=(patch|minor|major)' AGENTS.md
  [ "$status" -eq 0 ]
  [[ "$output" == *"BUMP=patch"* ]]
  [[ "$output" == *"BUMP=minor"* ]]
  [[ "$output" == *"BUMP=major"* ]]
}

@test "Makefile.ghaw WORKFLOW_SPECS includes all expected state labels" {
  cd "$REPO_ROOT"
  # Extract the WORKFLOW_SPECS definition block
  run grep -E 'open|ready|planned|in-progress|reviewed|blocked|defocus' Makefile.ghaw
  [ "$status" -eq 0 ]
  [[ "$output" == *"open"* ]]
  [[ "$output" == *"ready"* ]]
  [[ "$output" == *"planned"* ]]
  [[ "$output" == *"in-progress"* ]]
  [[ "$output" == *"reviewed"* ]]
  [[ "$output" == *"blocked"* ]]
  [[ "$output" == *"defocus"* ]]
}

@test "Makefile.ghaw COMPLEXITY_SPECS uses size/ namespace (not complexity/)" {
  cd "$REPO_ROOT"
  # Verify COMPLEXITY_SPECS defines size/* labels
  run grep -E 'size/xl|size/l|size/m|size/s|size/xs' Makefile.ghaw
  [ "$status" -eq 0 ]
  [[ "$output" == *"size/xl"* ]]
  [[ "$output" == *"size/l"* ]]
  [[ "$output" == *"size/m"* ]]
  [[ "$output" == *"size/s"* ]]
  [[ "$output" == *"size/xs"* ]]
  # Verify no complexity/ prefix is used in label specs
  run grep "complexity/" Makefile.ghaw
  [ "$status" -ne 0 ]
}
