#!/usr/bin/env bash
# Shared helpers for the CTM Proxmox provisioning kit.
# Sourced by bin/ctm-provision. Not executed directly.

set -euo pipefail

_c_red=$'\033[31m'; _c_grn=$'\033[32m'; _c_ylw=$'\033[33m'
_c_blu=$'\033[34m'; _c_dim=$'\033[2m';  _c_off=$'\033[0m'
[[ -t 2 ]] || { _c_red=; _c_grn=; _c_ylw=; _c_blu=; _c_dim=; _c_off=; }

log()  { printf '%s==>%s %s\n'  "$_c_blu" "$_c_off" "$*" >&2; }
ok()   { printf '%s  ok%s %s\n' "$_c_grn" "$_c_off" "$*" >&2; }
warn() { printf '%swarn%s %s\n' "$_c_ylw" "$_c_off" "$*" >&2; }
die()  { printf '%sfail%s %s\n' "$_c_red" "$_c_off" "$*" >&2; exit 1; }
step() { printf '\n%s---- %s ----%s\n' "$_c_dim" "$*" "$_c_off" >&2; }

DRY_RUN="${DRY_RUN:-0}"

# upper <site>  ->  RRSOUTH, for indirect variable lookup
upper() { printf '%s' "${1^^}"; }

# var SITE SUFFIX   ->  value of e.g. RRSOUTH_PVE1_ADDR
var() {
  local name="$(upper "$1")_$2"
  printf '%s' "${!name-}"
}

# require_var SITE SUFFIX -- fail loudly on unset or still-TODO inventory values
require_var() {
  local v; v="$(var "$1" "$2")"
  [[ -n "$v" ]] || die "inventory: $(upper "$1")_$2 is not set"
  [[ "$v" != "TODO" ]] || die "inventory: $(upper "$1")_$2 is still TODO -- fill it in"
  printf '%s' "$v"
}

# require_all SITE SUFFIX... -- validate inventory values in the CALLING shell.
#
# require_var cannot be relied on for this. Used inline as "VAR=$(require_var
# ...)", its die() exits only the command substitution's subshell: the message
# is printed, the caller carries on with an empty value, and the stage reports
# success having configured nothing. Only an assignment propagates the failure,
# and even then `local v="$(...)"` swallows it because `local` is the command
# whose status is reported.
#
# So preconditions are checked here, up front, where exit actually exits.
# A multi-line spec containing TODO anywhere counts as unfilled.
require_all() {
  local site="$1"; shift
  local suffix v missing=()
  for suffix in "$@"; do
    v="$(var "$site" "$suffix")"
    if [[ -z "${v//[[:space:]]/}" ]]; then
      missing+=("$(upper "$site")_${suffix} — not set")
    elif [[ "$v" == *TODO* ]]; then
      missing+=("$(upper "$site")_${suffix} — still contains TODO")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    printf '%sfail%s inventory is incomplete:\n' "$_c_red" "$_c_off" >&2
    printf '       - %s\n' "${missing[@]}" >&2
    exit 1
  fi
}

# ssh_opts -- key auth only, no host-key prompts on a fresh install, short timeout
ssh_opts() {
  printf '%s' \
    "-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new" \
    " -o ServerAliveInterval=15 -o ServerAliveCountMax=4 -i ${SSH_KEY}"
}

# rsh HOST CMD... -- run a command on a remote host
rsh() {
  local host="$1"; shift
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '%s[dry-run]%s %s: %s\n' "$_c_dim" "$_c_off" "$host" "$*" >&2
    return 0
  fi
  # shellcheck disable=SC2046
  ssh $(ssh_opts) "${SSH_USER}@${host}" "$@"
}

# rsh_script HOST SCRIPT [VAR=VAL...] -- ship a script and run it with env vars.
# The script is piped to a remote bash so nothing is left behind on the host.
rsh_script() {
  local host="$1" script="$2"; shift 2
  [[ -f "$script" ]] || die "no such script: $script"

  local env_prefix=""
  local kv
  for kv in "$@"; do
    env_prefix+="$(printf '%q ' "$kv")"
  done

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '%s[dry-run]%s %s: bash %s (%s)\n' \
      "$_c_dim" "$_c_off" "$host" "$(basename "$script")" "$*" >&2
    return 0
  fi

  # shellcheck disable=SC2046
  ssh $(ssh_opts) "${SSH_USER}@${host}" \
    "env ${env_prefix} bash -s" < "$script"
}

# reachable HOST -- true if SSH answers with key auth
reachable() {
  # shellcheck disable=SC2046
  ssh $(ssh_opts) "${SSH_USER}@$1" true 2>/dev/null
}

# confirm PROMPT -- interactive gate for destructive/clustering steps
confirm() {
  [[ "${ASSUME_YES:-0}" == "1" ]] && return 0
  local reply
  printf '%s??%s %s [y/N] ' "$_c_ylw" "$_c_off" "$1" >&2
  read -r reply </dev/tty || return 1
  [[ "$reply" =~ ^[Yy]$ ]]
}

# site_nodes SITE -- echo node short names, one per line
site_nodes() {
  local arr="$(upper "$1")_NODES[@]"
  printf '%s\n' "${!arr}"
}

# node_addr SITE INDEX -- mgmt address of node N (1-based)
node_addr() { require_var "$1" "PVE$2_ADDR"; }
