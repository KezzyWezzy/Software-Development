#!/usr/bin/env bash
# Section-aware comparison of two ctm-capture snapshots.
# Sourced by bin/ctm-provision.

# Sections whose contents legitimately differ between two healthy hosts.
# Reported, but never counted as drift.
_expected_diff_re='^(identity|cpu and memory class|block devices and pools|quorum)'

# Sections where addressing differs by design but STRUCTURE must match.
# Compared with host addresses masked.
_addr_sensitive_re='^(/etc/network/interfaces|cluster|storage configuration)'

# Replace IPv4 addresses and hostnames with placeholders so that a structural
# comparison is not swamped by every host having its own address.
_mask_addrs() {
  sed -E -e 's/\b([0-9]{1,3}\.){3}[0-9]{1,3}\b/<IP>/g' \
         -e 's/\b(pve|node)[0-9]+\b/<NODE>/g'
}

# _split_sections FILE OUTDIR -- one file per '##### ' section, numbered so
# ordering is preserved.
_split_sections() {
  awk -v dir="$2" '
    /^##### / {
      n++; name=substr($0,7); gsub(/[^a-zA-Z0-9]+/,"_",name);
      f=sprintf("%s/%03d_%s", dir, n, name);
      titles[n]=substr($0,7);
      print substr($0,7) > (f ".title");
      next
    }
    n { print >> (f ".body") }
  ' "$1"
}

# compare_captures BASELINE CANDIDATE -- prints a report, returns 1 on drift.
compare_captures() {
  local base="$1" cand="$2"
  local tmp; tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN

  mkdir -p "$tmp/b" "$tmp/c"
  _split_sections "$base" "$tmp/b"
  _split_sections "$cand" "$tmp/c"

  local drift=0 f title bb cc title_l
  for f in "$tmp"/b/*.title; do
    title="$(cat "$f")"
    title_l="$(printf '%s' "$title" | tr '[:upper:]' '[:lower:]')"
    bb="${f%.title}.body"
    cc="$tmp/c/$(basename "${f%.title}").body"
    [[ -f "$bb" ]] || bb=/dev/null
    [[ -f "$cc" ]] || cc=/dev/null

    if [[ "$title_l" =~ $_expected_diff_re ]]; then
      if ! diff -q "$bb" "$cc" >/dev/null 2>&1; then
        printf '  %s~ differs (expected)%s  %s\n' "$_c_dim" "$_c_off" "$title"
      fi
      continue
    fi

    if [[ "$title_l" =~ $_addr_sensitive_re ]]; then
      # Structural comparison with addresses masked.
      if diff -q <(_mask_addrs < "$bb") <(_mask_addrs < "$cc") >/dev/null 2>&1; then
        printf '  %s[ ok ]%s %s %s(structure matches; addresses differ)%s\n' \
          "$_c_grn" "$_c_off" "$title" "$_c_dim" "$_c_off"
      else
        printf '  %s[DRIFT]%s %s %s(structural)%s\n' \
          "$_c_red" "$_c_off" "$title" "$_c_dim" "$_c_off"
        diff -u <(_mask_addrs < "$bb") <(_mask_addrs < "$cc") \
          | tail -n +3 | sed 's/^/        /'
        drift=1
      fi
      continue
    fi

    # Everything else must match byte for byte.
    if diff -q "$bb" "$cc" >/dev/null 2>&1; then
      printf '  %s[ ok ]%s %s\n' "$_c_grn" "$_c_off" "$title"
    else
      printf '  %s[DRIFT]%s %s\n' "$_c_red" "$_c_off" "$title"
      diff -u "$bb" "$cc" | tail -n +3 | sed 's/^/        /'
      drift=1
    fi
  done

  # Sections present on the candidate but absent from the baseline.
  for f in "$tmp"/c/*.title; do
    [[ -f "$tmp/b/$(basename "$f")" ]] && continue
    printf '  %s[DRIFT]%s %s (present on candidate, absent from baseline)\n' \
      "$_c_red" "$_c_off" "$(cat "$f")"
    drift=1
  done

  return $drift
}
