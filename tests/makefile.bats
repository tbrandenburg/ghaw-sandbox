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
