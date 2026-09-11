#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="$repo_root/opencode.json"
launcher="$repo_root/scripts/opencode"
syncer="$repo_root/scripts/sync-opencode-skills.py"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

for script in "$launcher" "$syncer"; do
  [[ -x "$script" ]] || fail "$script is missing or is not executable"
done

python3 -m json.tool "$config" >/dev/null || fail "opencode.json is not valid JSON"
jq -e '
  .autoupdate == false and
  .share == "disabled" and
  .model == "zai-coding-plan/glm-5.3" and
  .agent.build.model == "zai-coding-plan/glm-5.3" and
  .agent.build.variant == "max" and
  .agent.plan.model == "zai-coding-plan/glm-5.3" and
  .agent.plan.variant == "max" and
  .provider["zai-coding-plan"].options.timeout == 900000
' "$config" >/dev/null || fail "OpenCode defaults are not the documented GLM-5.3 max profile"

if grep -Eq '(ZAI_API_KEY|ZHIPU_API_KEY)[[:space:]]*[:=][[:space:]]*[^"{]' "$config"; then
  fail "OpenCode config appears to persist an API key"
fi

assert_runtime_sync_and_launch_are_private() (
  local sandbox private_name private_marker output
  sandbox="$(mktemp -d)"
  trap 'rm -rf "$sandbox"' EXIT
  private_name="private-test-$RANDOM-$RANDOM"
  private_marker="PRIVATE_SKILL_BODY_$RANDOM$RANDOM"
  mkdir -p "$sandbox/bin" "$sandbox/home/.local/bin" "$sandbox/private/$private_name" "$sandbox/builtin/ignored"
  cat > "$sandbox/private/$private_name/SKILL.md" <<EOF
---
name: $private_name
description: Private test fixture.
---
$private_marker
EOF
  cat > "$sandbox/builtin/ignored/SKILL.md" <<'EOF'
---
name: ignored
description: Must not be synchronized.
---
ignored
EOF

  cat > "$sandbox/bin/amp" <<EOF
#!/usr/bin/env bash
[[ -z "\${ZAI_API_KEY:-}" && -z "\${ZHIPU_API_KEY:-}" ]] || exit 42
cat <<'JSON'
{"skills":[
  {"name":"$private_name","baseDir":"file://$sandbox/private/$private_name","source":"global-user"},
  {"name":"ignored","baseDir":"file://$sandbox/builtin/ignored","source":"builtin"}
]}
JSON
EOF
  cat > "$sandbox/home/.local/bin/mise" <<'EOF'
#!/usr/bin/env bash
printf 'args:'
printf ' <%s>' "$@"
printf '\nZAI_present=%s\n' "$([[ -n "${ZAI_API_KEY:-}" ]] && printf yes || printf no)"
printf 'ZHIPU_present=%s\n' "$([[ -n "${ZHIPU_API_KEY:-}" ]] && printf yes || printf no)"
EOF
  cat > "$sandbox/bin/opencode" <<EOF
#!/usr/bin/env bash
: > "$sandbox/unpinned-opencode-ran"
exit 99
EOF
  chmod +x "$sandbox/bin/amp" "$sandbox/bin/opencode" "$sandbox/home/.local/bin/mise"

  output="$(
    HOME="$sandbox/home" XDG_CONFIG_HOME="$sandbox/config" XDG_STATE_HOME="$sandbox/state" \
      PATH="$sandbox/bin:/usr/bin:/bin" ZAI_API_KEY="test-secret-$RANDOM" \
      "$launcher" --profile glm-5.3-high run "Reply with OK"
  )"

  [[ "$output" == *'args: <exec> <--> <opencode> <run> <--model> <zai-coding-plan/glm-5.3> <--variant> <high> <Reply with OK>'* ]] \
    || fail "the GLM-5.3 high profile did not select the expected model and variant"
  [[ "$output" == *'ZAI_present=no'* && "$output" == *'ZHIPU_present=yes'* ]] \
    || fail "the launcher did not expose only OpenCode's supported credential variable"
  [[ -L "$sandbox/config/opencode/skills/$private_name" ]] || fail "private skill was not linked at runtime"
  [[ "$(readlink "$sandbox/config/opencode/skills/$private_name")" == "$sandbox/private/$private_name" ]] \
    || fail "private skill link does not target Amp's runtime cache"
  [[ ! -e "$sandbox/config/opencode/skills/ignored" ]] || fail "non-user skill was synchronized"
  [[ ! -e "$sandbox/unpinned-opencode-ran" ]] || fail "launcher bypassed the mise-pinned OpenCode"
  [[ "$output" != *"$private_name"* && "$output" != *"$private_marker"* && "$output" != *"test-secret-"* ]] \
    || fail "launcher output exposed private inventory or secret material"
  ! git -C "$repo_root" grep -Fq "$private_marker" -- || fail "private skill content entered a tracked file"

  output="$(
    HOME="$sandbox/home" XDG_CONFIG_HOME="$sandbox/config" XDG_STATE_HOME="$sandbox/state" \
      PATH="$sandbox/bin:/usr/bin:/bin" ZAI_API_KEY="another-test-secret" \
      "$launcher" run --model future-provider/future-model --variant future-effort "Reply with OK"
  )"
  [[ "$output" == *'args: <exec> <--> <opencode> <run> <--model> <future-provider/future-model> <--variant> <future-effort> <Reply with OK>'* ]] \
    || fail "native future model and variant arguments were rewritten"
)

assert_invalid_profile_fails_closed() (
  local sandbox output sentinel
  sandbox="$(mktemp -d)"
  trap 'rm -rf "$sandbox"' EXIT
  sentinel="invalid-profile-secret-$RANDOM"
  mkdir -p "$sandbox/bin"
  cat > "$sandbox/bin/amp" <<'EOF'
#!/usr/bin/env bash
printf '{"skills":[]}'
EOF
  cat > "$sandbox/bin/opencode" <<'EOF'
#!/usr/bin/env bash
exit 99
EOF
  chmod +x "$sandbox/bin/amp" "$sandbox/bin/opencode"

  if output="$(
    HOME="$sandbox/home" XDG_CONFIG_HOME="$sandbox/config" XDG_STATE_HOME="$sandbox/state" \
      PATH="$sandbox/bin:/usr/bin:/bin" ZAI_API_KEY="$sentinel" \
      "$launcher" --profile glm-5.3-medium run test 2>&1
  )"; then
    fail "unsupported medium reasoning profile was accepted"
  fi
  [[ "$output" != *"$sentinel"* ]] || fail "invalid-profile diagnostic exposed the key"
)

assert_launcher_requires_pinned_mise() (
  local sandbox output
  sandbox="$(mktemp -d)"
  trap 'rm -rf "$sandbox"' EXIT
  mkdir -p "$sandbox/bin" "$sandbox/home/.local/bin"
  cat > "$sandbox/bin/amp" <<'EOF'
#!/usr/bin/env bash
printf '{"skills":[]}'
EOF
  cat > "$sandbox/home/.local/bin/mise" <<'EOF'
#!/usr/bin/env bash
printf 'mise args:'
printf ' <%s>' "$@"
printf '\n'
EOF
  chmod +x "$sandbox/bin/amp" "$sandbox/home/.local/bin/mise"

  output="$(
    HOME="$sandbox/home" XDG_CONFIG_HOME="$sandbox/config" XDG_STATE_HOME="$sandbox/state" \
      PATH="$sandbox/bin:/usr/bin:/bin" ZAI_API_KEY="mise-fallback-secret" \
      "$launcher" --profile glm-5.3-flash-low run "Reply with OK"
  )"
  [[ "$output" == *'mise args: <exec> <--> <opencode> <run> <--model> <zai-coding-plan/glm-5.3-flash>'* ]] \
    || fail "launcher did not use pinned mise when the OpenCode shim was absent"
  [[ "$output" != *"mise-fallback-secret"* ]] || fail "mise fallback output exposed the key"
)

assert_sync_cleanup_and_path_guards() (
  local sandbox encoded_source manifest private_name
  sandbox="$(mktemp -d)"
  trap 'rm -rf "$sandbox"' EXIT
  private_name="encoded-skill"
  encoded_source="$sandbox/private cache/$private_name"
  manifest="$sandbox/state/merge-carlo/opencode-user-skill-links.json"
  mkdir -p "$sandbox/bin" "$encoded_source" "$sandbox/state/merge-carlo"
  printf '%s\n' '---' "name: $private_name" 'description: Private test fixture.' '---' > "$encoded_source/SKILL.md"
  cat > "$sandbox/bin/amp" <<EOF
#!/usr/bin/env bash
cat "$sandbox/inventory.json"
EOF
  chmod +x "$sandbox/bin/amp"
  cat > "$sandbox/inventory.json" <<EOF
{"skills":[{"name":"$private_name","baseDir":"file://$sandbox/private%20cache/$private_name","source":"global-user"}]}
EOF

  HOME="$sandbox/home" XDG_CONFIG_HOME="$sandbox/config" XDG_STATE_HOME="$sandbox/state" \
    PATH="$sandbox/bin:/usr/bin:/bin" "$syncer" --quiet
  [[ "$(readlink "$sandbox/config/opencode/skills/$private_name")" == "$encoded_source" ]] \
    || fail "percent-encoded User Skill path was not linked correctly"
  printf '{"skills":[]}' > "$sandbox/inventory.json"
  HOME="$sandbox/home" XDG_CONFIG_HOME="$sandbox/config" XDG_STATE_HOME="$sandbox/state" \
    PATH="$sandbox/bin:/usr/bin:/bin" "$syncer" --quiet
  [[ ! -e "$sandbox/config/opencode/skills/$private_name" ]] || fail "stale managed skill link was not removed"

  printf '{"../outside":"%s"}\n' "$sandbox/target" > "$manifest"
  if HOME="$sandbox/home" XDG_CONFIG_HOME="$sandbox/config" XDG_STATE_HOME="$sandbox/state" \
    PATH="$sandbox/bin:/usr/bin:/bin" "$syncer" --quiet 2>/dev/null; then
    fail "traversing manifest key was accepted"
  fi
  printf '{}\n' > "$manifest"

  if (
    cd "$repo_root"
    HOME="$sandbox/home" XDG_CONFIG_HOME="relative-config" XDG_STATE_HOME="$sandbox/state" \
      PATH="$sandbox/bin:/usr/bin:/bin" "$syncer" --quiet 2>/dev/null
  ); then
    fail "relative XDG_CONFIG_HOME was accepted"
  fi
  [[ ! -e "$repo_root/relative-config" ]] || fail "relative XDG path wrote private links into the repository"

  if HOME="$sandbox/home" XDG_CONFIG_HOME="$repo_root/.private-opencode-test" XDG_STATE_HOME="$sandbox/state" \
    PATH="$sandbox/bin:/usr/bin:/bin" "$syncer" --quiet 2>/dev/null; then
    fail "absolute in-repository XDG_CONFIG_HOME was accepted"
  fi
  [[ ! -e "$repo_root/.private-opencode-test" ]] \
    || fail "absolute XDG path wrote private links into the repository"
)

assert_predictable_temp_paths_are_never_touched() (
  local sandbox module_driver
  sandbox="$(mktemp -d)"
  trap 'rm -rf "$sandbox"' EXIT
  mkdir -p "$sandbox/bin" "$sandbox/config/opencode/skills" "$sandbox/state/merge-carlo" "$sandbox/private/temp-skill"
  printf '%s\n' '---' 'name: temp-skill' 'description: Private test fixture.' '---' \
    > "$sandbox/private/temp-skill/SKILL.md"
  cat > "$sandbox/bin/amp" <<EOF
#!/usr/bin/env bash
printf '%s' '{"skills":[{"name":"temp-skill","baseDir":"file://$sandbox/private/temp-skill","source":"global-user"}]}'
EOF
  chmod +x "$sandbox/bin/amp"
  printf 'do not delete\n' > "$sandbox/config/opencode/skills/.temp-skill.4242.tmp"
  printf 'do not overwrite\n' > "$sandbox/victim"
  ln -s "$sandbox/victim" \
    "$sandbox/state/merge-carlo/.opencode-user-skill-links.json.4242.tmp"
  module_driver="$sandbox/run-sync.py"
  cat > "$module_driver" <<EOF
import importlib.util
spec = importlib.util.spec_from_file_location("syncer", "$syncer")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
module.os.getpid = lambda: 4242
module.sync()
EOF
  HOME="$sandbox/home" XDG_CONFIG_HOME="$sandbox/config" XDG_STATE_HOME="$sandbox/state" \
    PATH="$sandbox/bin:/usr/bin:/bin" python3 "$module_driver"
  grep -Fq 'do not delete' "$sandbox/config/opencode/skills/.temp-skill.4242.tmp" \
    || fail "skill sync deleted an unowned temporary path"
  grep -Fq 'do not overwrite' "$sandbox/victim" || fail "manifest write followed an unowned temporary symlink"
)

assert_runtime_sync_and_launch_are_private
assert_invalid_profile_fails_closed
assert_launcher_requires_pinned_mise
assert_sync_cleanup_and_path_guards
assert_predictable_temp_paths_are_never_touched

grep -Fq 'opencode = "1.18.30"' "$repo_root/mise.toml" || fail "OpenCode is not pinned in mise.toml"
grep -Fq '[[tools.opencode]]' "$repo_root/mise.lock" || fail "OpenCode is not present in mise.lock"
grep -Fq 'bash scripts/check-opencode-setup-test.sh' "$repo_root/mise.toml" \
  || fail "the full local gate does not validate OpenCode setup"
grep -Fq 'bash scripts/check-opencode-setup-test.sh' "$repo_root/.github/workflows/build.yml" \
  || fail "CI does not validate OpenCode setup"

printf 'OpenCode setup checks passed\n'
