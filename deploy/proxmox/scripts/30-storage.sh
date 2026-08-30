# Runs ON one Proxmox host per cluster (storage config is cluster-wide in /etc/pve).
# Attaches the NAS as shared storage for backups, ISOs and CT templates.
#
# env in: NAS_STORAGE_ID NAS_STORAGE_HOST NAS_STORAGE_EXPORT
set -euo pipefail

# Remote scripts arrive via `ssh host "bash -s"`, a non-login shell whose PATH
# is not guaranteed to include sbin -- where ip, pvecm, pvesm and pvesh all live.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

for v in NAS_STORAGE_ID NAS_STORAGE_HOST NAS_STORAGE_EXPORT; do
  [[ -n "${!v:-}" ]] || { say "ERROR: $v unset"; exit 1; }
done

if pvesm status --storage "$NAS_STORAGE_ID" >/dev/null 2>&1; then
  say "storage '$NAS_STORAGE_ID' already defined"
else
  # showmount confirms the export exists before we commit it to cluster config;
  # a wrong export path otherwise shows up much later as a failed backup job.
  if command -v showmount >/dev/null 2>&1; then
    if showmount -e "$NAS_STORAGE_HOST" 2>/dev/null | grep -q "$NAS_STORAGE_EXPORT"; then
      say "verified export ${NAS_STORAGE_HOST}:${NAS_STORAGE_EXPORT}"
    else
      say "ERROR: ${NAS_STORAGE_HOST} does not export ${NAS_STORAGE_EXPORT}"
      showmount -e "$NAS_STORAGE_HOST" 2>/dev/null | sed 's/^/      /' || true
      exit 1
    fi
  fi

  pvesm add nfs "$NAS_STORAGE_ID" \
    --server "$NAS_STORAGE_HOST" \
    --export "$NAS_STORAGE_EXPORT" \
    --content backup,iso,vztmpl \
    --options vers=4.1
  say "added NFS storage '$NAS_STORAGE_ID'"
fi

pvesm status --storage "$NAS_STORAGE_ID" | sed 's/^/    /'
