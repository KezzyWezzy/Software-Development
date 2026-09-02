# Comms chain: continuumsrv01 <-> Claude Code cloud sessions

Runbook for linking the long-running `claude --resume --dangerously-skip-permissions`
session on **continuumsrv01** (LAN-only) to Claude Code sessions running in the
Anthropic cloud (claude.ai/code, iOS app).

## Why the link must start from continuumsrv01

A cloud session runs in an isolated Anthropic-managed container. It has no SSH, no
MQTT client, no LAN route, and outbound HTTPS only through an agent proxy. It cannot
reach a LAN-only host, and nothing written in the cloud session changes that.

Remote Control solves it from the other side: the local CLI makes **outbound HTTPS
requests only and never opens an inbound port**. NAT, no port-forward, and a
LAN-only address are all fine. Traffic is relayed through the Anthropic API over TLS.

## Prerequisites on continuumsrv01

| Requirement | Check |
|---|---|
| Claude Code >= 2.1.225 (cross-machine send) | `claude --version` |
| Signed in to claude.ai (not an API key) | `/login` inside the CLI |
| Pro / Max / Team / Enterprise plan | API keys are not supported |

On Team/Enterprise an Owner must enable the Remote Control toggle in
Claude Code admin settings first.

## Step 1 - expose the session

Attach Remote Control to the already-running conversation. Inside the session:

```
/remote-control continuumsrv01
```

The argument names the session, which is the address other sessions use, so give it
a stable name rather than letting one be auto-generated. A `/rc active` indicator
appears in the footer and the session URL is posted into the conversation.

To start a fresh session with it already on:

```bash
claude --remote-control continuumsrv01 --resume
```

Running `/remote-control` a second time opens a status panel with the URL, a QR code,
and a disconnect option.

> If the conversation is resumed in a second terminal while the first still holds
> Remote Control, it stays **off** in the second and that session becomes unreachable.
> Keep one terminal authoritative.

## Step 2 - stop messages being held

Inbound messages are filtered by the receiving session's permission mode. A session
started with `--dangerously-skip-permissions` is in the *bypassing* class, and the
default for a bypassing receiver is to **hold every message for interactive approval**,
dropping it after `dialogExpiry` (5 minutes by default). An unattended server session
will silently swallow the chain.

Set this in user settings on continuumsrv01 (`~/.claude/settings.json`):

```json
{
  "crossSessionInbound": "accept",
  "dialogExpiry": "never"
}
```

`crossSessionInbound` is also selectable in `/config` under
**Messages from your other sessions**. Note that a `refuse` in project or local
settings overrides a user-settings `accept`.

## Step 3 - open the chain

Discovery is asymmetric. A session connected to Remote Control can enumerate the
account's cloud sessions; a cloud session generally cannot enumerate back. **So
continuumsrv01 speaks first.** From that session, prompt Claude with something like:

```
List my sessions beyond this machine, then tell the cloud session
<session-name> that the continuumsrv01 link is up
```

The message carries a reply address, so the cloud session can answer directly from
then on. The link is bidirectional once the first message lands.

Verify reachability at any time with `/list-agents` (alias `/peers`). Cloud sessions
are labelled `cloud`; other machines are labelled `Remote Control`.

## Fallback - one-way post into a cloud session

No Remote Control needed, only `claude auth login`. Posts one message and exits:

```bash
claude -p "PLC sync finished on continuumsrv01" --cloud <session-id>
```

The message arrives as an ordinary user turn. There is no reply address, so this is
outbound-only from continuumsrv01 - read the answer in the session transcript on the
web or in the app. Useful from cron, hooks, or a build script.

Machine-readable result:

```bash
claude -p "..." --cloud <session-id> --output-format json
# {"ok":true,"session_id":"...","url":"..."}
```

## Troubleshooting

| Symptom | Cause |
|---|---|
| `/list-agents` not recognised | CLI below v2.1.224 - upgrade |
| Cloud sessions absent from the listing | This session is not connected to Remote Control |
| Message sent but never arrived | Receiver held or refused it - check `crossSessionInbound` |
| Repeated HTTP 403, then disconnect | A proxy, VPN, or firewall between continuumsrv01 and Anthropic |
| Disconnect after ~30 min idle | Presence heartbeats failed - run `/remote-control` to reconnect |
| Server mode exits after ~10 min | Extended network outage - rerun `claude remote-control` |

Recover sessions from a stopped server mode, within about four hours, from the same
directory:

```bash
claude remote-control                      # every session it was serving
claude remote-control --session-id <id>    # just one
```

## Limits worth knowing

- Plain text only; no files or conversation history cross the link.
- Messages are rate-limited per sender and identical repeats inside a short window are
  dropped, so a loop between two sessions stops on its own.
- At most 50 accepted messages queue for the receiving Claude.
- A message from another session never counts as your consent: it cannot answer a
  permission prompt, and the receiving session is instructed not to change settings
  or `CLAUDE.md` because a peer asked.
- Set `isolatePeerMachines: true` to require explicit approval before any message
  leaves the machine.
