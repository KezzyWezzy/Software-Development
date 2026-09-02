#!/usr/bin/env bash
# Runs ON a Proxmox host, straight after a manual PVE install.
# Idempotent: re-running changes nothing that is already correct.
#
# env in: TIMEZONE NTP_SERVERS OFFLINE_BUNDLE_PATH
set -euo pipefail

# Remote scripts arrive via `ssh host "bash -s"`, a non-login shell whose PATH
# is not guaranteed to include sbin -- where ip, pvecm, pvesm and pvesh all live.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
say() { printf '  %s\n' "$*"; }

# --- 1. Repositories -------------------------------------------------------
# Air-gapped: the enterprise repo needs a subscription AND internet, so it only
# produces 401s that make every apt run noisy and slow. Disable it and serve
# packages from the staged bundle instead.
if [[ -f /etc/apt/sources.list.d/pve-enterprise.list ]] \
   && ! grep -q '^#' /etc/apt/sources.list.d/pve-enterprise.list; then
  sed -i 's/^deb/# deb/' /etc/apt/sources.list.d/pve-enterprise.list
  say "disabled pve-enterprise repo"
fi
if [[ -f /etc/apt/sources.list.d/ceph.list ]] \
   && ! grep -q '^#' /etc/apt/sources.list.d/ceph.list; then
  sed -i 's/^deb/# deb/' /etc/apt/sources.list.d/ceph.list
  say "disabled ceph enterprise repo"
fi

# Local file-backed apt repo from the offline bundle.
if [[ -d "$OFFLINE_BUNDLE_PATH" ]]; then
  ( cd "$OFFLINE_BUNDLE_PATH" \
    && dpkg-scanpackages -m . 2>/dev/null | gzip -9c > Packages.gz )
  echo "deb [trusted=yes] file://${OFFLINE_BUNDLE_PATH} ./" \
    > /etc/apt/sources.list.d/ctm-offline.list
  say "local apt repo indexed from $OFFLINE_BUNDLE_PATH"
else
  say "WARNING: no offline bundle at $OFFLINE_BUNDLE_PATH; apt will have no source"
fi

# Drop any repo line that points at the internet -- on an air-gapped OT network
# these only cause 30s timeouts on every apt invocation.
for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do
  [[ -f "$f" ]] || continue
  [[ "$f" == */ctm-offline.list ]] && continue
  if grep -qE '^deb .*https?://' "$f"; then
    sed -i -E 's|^(deb .*https?://.*)$|# \1  # disabled: air-gapped|' "$f"
    say "commented internet repo lines in $(basename "$f")"
  fi
done

apt-get update -o Acquire::Retries=0 >/dev/null 2>&1 || say "apt update reported errors (expected if bundle is partial)"

# --- 2. Subscription nag ---------------------------------------------------
# Patch the JS that raises the "no valid subscription" dialog. Re-applied after
# every pve-manager upgrade, so this is safe to run repeatedly.
NAG=/usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js
if [[ -f "$NAG" ]] && grep -q 'No valid subscription' "$NAG"; then
  cp -n "$NAG" "${NAG}.orig" 2>/dev/null || true
  sed -i "s/data.status.toLowerCase() !== 'active'/false/g" "$NAG" || true
  systemctl restart pveproxy 2>/dev/null || true
  say "suppressed subscription dialog"
fi

# --- 3. Time ---------------------------------------------------------------
# The kiosk runbook records a whole class of failures caused by wrong clocks.
# Corosync will not form a stable ring across skewed nodes either.
if [[ -n "${TIMEZONE:-}" ]]; then
  timedatectl set-timezone "$TIMEZONE"
  say "timezone: $TIMEZONE"
fi

if [[ -n "${NTP_SERVERS:-}" ]]; then
  mkdir -p /etc/chrony/conf.d
  {
    echo "# managed by ctm-provision -- local time source (air-gapped site)"
    for s in $NTP_SERVERS; do echo "server $s iburst"; done
  } > /etc/chrony/conf.d/ctm.conf
  systemctl restart chrony 2>/dev/null || systemctl restart chronyd 2>/dev/null || true
  say "NTP sources: $NTP_SERVERS"
fi

# --- 4. Baseline packages --------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
for p in chrony corosync-qdevice ifupdown2 lldpd; do
  if ! dpkg -s "$p" >/dev/null 2>&1; then
    if apt-get install -y --no-install-recommends "$p" >/dev/null 2>&1; then
      say "installed $p"
    else
      say "WARNING: could not install $p -- stage it in the offline bundle"
    fi
  fi
done

# --- 5. SSH hardening ------------------------------------------------------
# These runs are unattended; password auth on an OT host is a standing risk.
sshd_drop=/etc/ssh/sshd_config.d/10-ctm.conf
mkdir -p "$(dirname "$sshd_drop")"
cat > "$sshd_drop" <<'SSHD'
# managed by ctm-provision
PasswordAuthentication no
PermitRootLogin prohibit-password
SSHD
if sshd -t 2>/dev/null; then
  systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true
  say "sshd: key-only auth enforced"
else
  rm -f "$sshd_drop"
  say "WARNING: sshd config test failed; reverted hardening"
fi

say "post-install complete on $(hostname -s)"
