# Runs ON one node per cluster -- storage config lives in /etc/pve and is
# cluster-wide, so adding it twice is redundant, not harmful.
#
# Adds every storage in the spec that is not already defined. Never edits or
# removes an existing definition: a wrong edit here detaches running guests
# from their disks.
#
# env in: STORAGES -- newline-separated records, fields separated by |
#           type|id|server|path|content|extra
#         type   nfs | cifs | iscsi | lvm
#         path   nfs: export   cifs: share   iscsi: target IQN   lvm: vgname
#         extra  additional pvesm flags, passed through verbatim
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

[[ -n "${STORAGES:-}" ]] || { say "STORAGES unset -- nothing to do"; exit 0; }
command -v pvesm >/dev/null 2>&1 || { say "ERROR: pvesm not found"; exit 1; }

added=0 skipped=0
while IFS='|' read -r type id server path content extra; do
  [[ -z "${type// }" || "$type" == \#* ]] && continue

  for req in type id; do
    [[ -n "${!req}" ]] || { say "ERROR: record missing $req: $type|$id"; exit 1; }
  done

  if pvesm status --storage "$id" >/dev/null 2>&1; then
    say "${id}: already defined -- left untouched"
    skipped=$((skipped+1))
    continue
  fi

  case "$type" in
    nfs)
      [[ -n "$server" && -n "$path" ]] || { say "ERROR: ${id}: nfs needs server and export"; exit 1; }
      # Confirm the export really exists before committing it to cluster
      # config; a wrong path otherwise surfaces later as a failed backup job.
      if command -v showmount >/dev/null 2>&1; then
        if showmount -e "$server" 2>/dev/null | awk '{print $1}' | grep -qx "$path"; then
          say "${id}: verified export ${server}:${path}"
        else
          say "ERROR: ${id}: ${server} does not export ${path}. It offers:"
          showmount -e "$server" 2>/dev/null | sed 's/^/        /' || say "        (showmount returned nothing)"
          exit 1
        fi
      fi
      # shellcheck disable=SC2086
      pvesm add nfs "$id" --server "$server" --export "$path" \
        ${content:+--content "$content"} $extra
      ;;
    cifs)
      [[ -n "$server" && -n "$path" ]] || { say "ERROR: ${id}: cifs needs server and share"; exit 1; }
      # Credentials must come from --username/--password in extra. Putting a
      # password in the inventory is why inventory/sites.sh is gitignored.
      # shellcheck disable=SC2086
      pvesm add cifs "$id" --server "$server" --share "$path" \
        ${content:+--content "$content"} $extra
      ;;
    iscsi)
      [[ -n "$server" && -n "$path" ]] || { say "ERROR: ${id}: iscsi needs portal and target IQN"; exit 1; }
      # content is normally 'none' -- an iSCSI storage usually carries an LVM
      # storage on top rather than holding images directly.
      # shellcheck disable=SC2086
      pvesm add iscsi "$id" --portal "$server" --target "$path" \
        --content "${content:-none}" $extra
      ;;
    lvm)
      [[ -n "$path" ]] || { say "ERROR: ${id}: lvm needs a vgname"; exit 1; }
      # shellcheck disable=SC2086
      pvesm add lvm "$id" --vgname "$path" \
        ${content:+--content "$content"} $extra
      ;;
    *)
      say "ERROR: ${id}: unsupported storage type '${type}'"
      exit 1
      ;;
  esac

  say "${id}: added (${type})"
  added=$((added+1))
done <<< "$STORAGES"

say "storage: ${added} added, ${skipped} already present"
pvesm status 2>/dev/null | sed 's/^/    /'
