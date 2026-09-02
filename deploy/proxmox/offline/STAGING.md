# Air-gap staging

The Line 2 and Nash Proxmox hosts have no route to the internet, so every
package has to arrive on media. Build the bundle once on a machine that *does*
have internet, running the **same Proxmox VE version** as the target hosts —
package versions must match or `apt` will pull unmet dependencies it cannot
reach.

## 1. Build the bundle

On an internet-connected PVE host of the same version:

```bash
mkdir -p /tmp/ctm-offline && cd /tmp/ctm-offline
apt-get update
apt-get install -y --download-only --reinstall \
    chrony corosync-qdevice corosync-qnetd ifupdown2 lldpd nfs-common
cp /var/cache/apt/archives/*.deb .
dpkg-scanpackages -m . | gzip -9c > Packages.gz
```

Add anything else the site will need before you leave — a container template
(`pveam download local debian-12-standard_*`, then copy from
`/var/lib/vz/template/cache/`), and the CTM container images if the server
guest is built on site.

## 2. Verify the bundle resolves *before* travelling

An incomplete bundle is only discovered at the terminal, which is the expensive
place to discover it. On a throwaway VM with no network:

```bash
echo "deb [trusted=yes] file:///tmp/ctm-offline ./" > /etc/apt/sources.list.d/test.list
mv /etc/apt/sources.list /etc/apt/sources.list.bak
apt-get update && apt-get install -s corosync-qdevice ifupdown2 chrony
```

`-s` simulates. If it reports no unmet dependencies, the bundle is complete.

## 3. Stage it on each host

Copy to `OFFLINE_BUNDLE_PATH` (default `/opt/ctm-offline`) on **both** Proxmox
nodes and on the QDevice host:

```bash
rsync -a --rsh="ssh -i ~/.ssh/id_ed25519_ctm" \
      /tmp/ctm-offline/ root@<host>:/opt/ctm-offline/
```

`00-preflight.sh` fails the host if the bundle is missing or empty, so you find
out before any stage tries to install something.

## 4. The QDevice host

`51-qdevice-setup.sh` needs `corosync-qnetd` running on the NAS. That package
is Debian-flavoured, so:

- **Debian/Ubuntu-based NAS** — stage the bundle there too and run the
  `qdevice` stage directly.
- **TrueNAS / Synology / QNAP** — the appliance OS will not take a Debian
  package. Run qnetd in a small Debian container or VM on the NAS instead, give
  it a static IP on the cluster's corosync network, and point
  `*_QDEVICE_ADDR` at that container rather than the NAS itself.

Whichever it is, the cluster nodes must be able to SSH to it as `root` with a
key — `pvecm qdevice setup` drives it over SSH.

## What the QDevice buys you

A two-node cluster has `expected_votes: 2`. Lose one node and the survivor
holds 1 of 2 — not a majority — so it goes non-quorate, `/etc/pve` drops to
read-only, and HA cannot start anything. That is the failure mode the QDevice
exists to remove: a third arbitrating vote means the survivor holds 2 of 3 and
can legitimately take over.

It is not a Proxmox node, stores no guest data, and never runs workloads. It
votes. Losing the QDevice itself while both nodes are up is harmless — you are
back to a plain two-node cluster until it returns.
