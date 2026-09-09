#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
setup="$repo_root/.agents/setup"
resume="$repo_root/.agents/resume"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_unverified_mise_is_not_executed() (
  local sandbox
  sandbox="$(mktemp -d)"
  trap 'rm -rf "$sandbox"' EXIT
  mkdir -p "$sandbox/home/.local/bin" "$sandbox/bin"

  cat > "$sandbox/home/.local/bin/mise" <<'EOF'
#!/bin/sh
: > "$HOME/untrusted-mise-ran"
printf '2026.9.3 linux-x64\n'
EOF
  cat > "$sandbox/bin/curl" <<'EOF'
#!/bin/sh
: > "$HOME/download-attempted"
exit 42
EOF
  chmod +x "$sandbox/home/.local/bin/mise" "$sandbox/bin/curl"

  if HOME="$sandbox/home" PATH="$sandbox/bin:/usr/bin:/bin" \
    bash -c 'source "$1"; install_mise' bash "$setup" >/dev/null 2>&1; then
    fail "setup accepted an unverified mise binary"
  fi
  [[ ! -e "$sandbox/home/untrusted-mise-ran" ]] || fail "setup executed an unverified mise binary"
  [[ -e "$sandbox/home/download-attempted" ]] || fail "setup did not replace an unverified mise binary"
)

assert_mise_verification_requires_execute_permission() (
  local sandbox expected_checksum
  sandbox="$(mktemp -d)"
  trap 'rm -rf "$sandbox"' EXIT
  mkdir -p "$sandbox/home/.local/bin"
  printf 'test mise binary\n' > "$sandbox/home/.local/bin/mise"
  expected_checksum="$(sha256sum "$sandbox/home/.local/bin/mise" | awk '{print $1}')"

  HOME="$sandbox/home" bash -c '
    source "$1"
    declare -F mise_is_verified >/dev/null
    chmod +x "$MISE_BIN"
    mise_is_verified "$2"
    chmod -x "$MISE_BIN"
    ! mise_is_verified "$2"
  ' bash "$setup" "$expected_checksum" || fail "mise verification ignores execute permission"
)

assert_profile_paths_are_escaped() (
  local sandbox copied_repo test_home
  sandbox="$(mktemp -d)"
  trap 'rm -rf "$sandbox"' EXIT
  copied_repo="$sandbox/repo-\$(touch PWNED)"
  test_home="$sandbox/home"
  mkdir -p "$copied_repo/.agents" "$test_home/.local/bin"
  cp "$setup" "$copied_repo/.agents/setup"

  cat > "$test_home/.local/bin/mise" <<'EOF'
#!/bin/sh
printf ':\n'
EOF
  chmod +x "$test_home/.local/bin/mise"

  HOME="$test_home" bash -c '
    source "$1"
    configure_login_shell
    cd "$2"
    source "$HOME/.bash_profile"
    [[ ! -e PWNED ]]
  ' bash "$copied_repo/.agents/setup" "$copied_repo" || fail "profile paths allow shell evaluation"
)

for script in "$setup" "$resume"; do
  [[ -x "$script" ]] || fail "$script is missing or is not executable"
  bash -n "$script" || fail "$script is not valid Bash"
done

grep -Fq '"$MISE_BIN" install --locked --yes' "$setup" || fail "setup does not invoke the verified mise binary"
grep -Fq 'uv sync --locked --dev' "$setup" || fail "setup does not sync locked development dependencies"
grep -Fq 'git config --local core.hooksPath' "$setup" || fail "setup does not isolate repository hooks"
grep -Fq 'lefthook install --force' "$setup" || fail "setup does not install commit hooks"
grep -Fq 'sha256sum "$MISE_BIN"' "$setup" || fail "setup does not verify an existing mise binary"
grep -Fq 'mv -- "$staged_bin" "$MISE_BIN"' "$setup" || fail "setup does not replace mise atomically"
grep -Fq "printf -v repo_root_q '%q'" "$setup" || fail "setup does not escape the repository profile path"
grep -Fq -- '--connect-timeout 10' "$setup" || fail "mise bootstrap has no connection timeout"
grep -Fq -- '--retry-max-time 180' "$setup" || fail "mise bootstrap has no retry deadline"
grep -Fq 'MISE_HTTP_DOWNLOAD_TIMEOUT=60s' "$setup" || fail "mise downloads have no bounded timeout"
grep -Fq 'github:tessariq/taskrail' "$repo_root/mise.toml" || fail "Taskrail is not pinned in mise.toml"
[[ -f "$repo_root/mise.lock" ]] || fail "mise.lock is missing"
grep -Fq 'bash scripts/check-orb-setup-test.sh' "$repo_root/.github/workflows/build.yml" \
  || fail "CI does not run the orb setup contract"

if grep -Eq '(mise install|uv sync|lefthook install)' "$resume"; then
  fail "resume reinstalls setup dependencies"
fi

assert_unverified_mise_is_not_executed
assert_mise_verification_requires_execute_permission
assert_profile_paths_are_escaped

printf 'orb setup checks passed\n'
