# CTM ↔ PLC Contract — IND780 Terminal Batching

**For the CTM-side engineer/agent.** This describes what changes on the PLC
side and what CTM must do differently. It does not ask for CTM code here —
it states the contract.

**Read `continuum-terminal-product` first.** The data ownership matrix in that
skill is amended by this document in four rows. Everything else stands.

---

## 1. What changed, in one paragraph

Each bay can now be configured so that the **IND780 weigh terminal runs the
load cutoff itself** instead of the PLC doing it. Where that is on, the
terminal captures its own tare and cuts off on its own target, and the
numbers on the ticket are the terminal's numbers, not values the PLC
computed. CTM still owns the books and still owns the permissive. The PLC
still owns safety and the bay state machine. What CTM loses is the ability to
author a tare or a net — and that is deliberate: a net the PLC calculated is
not a legal-for-trade net.

---

## 2. The mode switch

Per bay, in PLC configuration:

| `Cfg_BayScaleMode[b]` | Behaviour |
|---|---|
| **0** | **Unchanged.** Exactly today's behaviour. CTM/simulator-written weights, PLC-computed net, PLC cutoff. |
| **1** | Terminal batch. PLC commands the IND780; terminal cuts off; terminal's numbers reach the ticket. |

Also per bay: `Cfg_BayScaleSrc[b]` = 0 (no terminal) or 1–6 (which card).

**A bay in mode 0 is untouched by any of this.** If CTM does nothing, nothing
changes. Migration is per bay, at whatever pace commissioning allows.

---

## 3. Amendments to the data ownership matrix

Four rows change **when `Cfg_BayScaleMode[b] = 1`**. In mode 0 the existing
matrix is correct as written.

| Tag | Was | Now (mode 1) |
|---|---|---|
| `Tare_Value` | PLC, captured from `Scale_Gross` at lock | **IND780** — the terminal's own captured tare, via `IND780s[c].Tare_PV` |
| `Tare_Locked` | PLC, on `Cmd_LockTare` with `Scale_Stable` | **IND780** — set when the terminal confirms a tare |
| `Scale_Net` | PLC, `Scale_Gross − Tare_Value` | **IND780** — the terminal's net, read directly |
| `Res_GrossWt` / `Res_TareWt` / `Res_NetWt` | PLC at the 4→5 transition | **IND780**, latched by the PLC at 4→5 |

`Res_TotalGal` is unchanged — it is the flow totalizer, a different
instrument. It is **not** a second custody number. Treat it as the
reconciliation cross-check against the terminal's weight, which is exactly
what it is good for.

`Scale_Gross` in mode 1 is reconstructed by the PLC as terminal net +
terminal tare, so the DOT gross interlock still has a real gross to work
against. It is a derived display value, not the custody gross.

---

## 4. What CTM must NOT do in mode 1

1. **Do not write `Scale_Gross`, `Scale_Tare_Live`, `Tare_Value` or
   `Scale_Net` for a bay in mode 1.** The PLC writes them from the terminal
   every scan. A CTM write is a second writer on the same tag and the values
   will fight scan to scan. This is the existing anti-pattern #3, and mode 1
   moves four more tags into it.

2. **Do not recompute the net for the BOL.** Take `Res_NetWt` as the PLC
   presents it. If it disagrees with `Res_GrossWt − Res_TareWt` by more than
   rounding, that is an anomaly to raise, not an error to correct.

3. **Do not correct a tare silently.** The tare came from a sealed device. A
   correction goes through the existing manual-correction path
   (`POST /plc/reconciliation/transactions/{id}/manual-correct`, superuser
   only) so the original is preserved in `transaction_events`.

---

## 5. What CTM should do

### 5.1 The permissive is unchanged

CTM still drives the permissive through `CommIF`, and
`Cfg_CTMPermissiveMode` still governs what withdrawing it does mid-load:

- `0` — checked at start only
- `1` — controlled stop; the bay completes and a ticket is written for what
  was delivered
- `2` — fault; no ticket, operator reset required

In mode 1 a withdrawn permissive additionally aborts the terminal's target
logic on the same scan. The delivered amount is still captured.

### 5.2 New anomaly check — terminal vs. PLC disagreement

This is the piece worth building. The PLC now exposes both:

- the terminal's own numbers (`Res_*`, sourced from `IND780s[c]`)
- the flow totalizer's independent measure (`Res_TotalGal`)

Add a sixth check to the anomaly scanner: a completed transaction whose
`Res_NetWt` and `Res_TotalGal` (converted at product density) disagree beyond
a configured tolerance. That is a continuous, free proof that the custody
chain is honest, and it is the first thing an auditor will ask for.

### 5.3 New status to surface

Per bay, read-only, for the dashboard and for anomaly context:

| Tag | Meaning |
|---|---|
| `IND780s[c].Comm_OK` | Terminal reachable. **0 means the weight is not live** |
| `IND780s[c].Quality` | 0 Good / 1 Uncertain / 2 Bad |
| `IND780s[c].Seq_ErrCode` | 0 None / 1 ReadbackTimeout / 2 ReadbackMismatch / 3 TerminalLost / 4 NetMode / 5 OutOfTolerance |
| `IND780s[c].Tare_Confirmed` | The terminal holds the tare the PLC believes it holds |
| `IND780s[c].Target_Confirmed` | The terminal holds the commanded target |
| `IND780s[c].Batch_Done` | Terminal-derived completion |
| `IND780s[c].Batch_Fault` | Batch ended abnormally — aborted, out of tolerance, or terminal lost |

`Seq_ErrCode ≠ 0` raises `Scale_Fault` on the bay and drives
`Lockout_Reason` 6. CTM will see the existing lockout; the error code says
*why* in a way the lockout reason cannot.

### 5.4 Target is still CTM's to set

Unchanged: CTM writes the target through the existing bay command handshake
(`Bay_CmdCode` 7, `Bay_CmdValue` → `Cfg_TargetNet`). The PLC pushes it to the
terminal and **confirms it by reading it back** before the pump is permitted.
If the readback does not match, the bay refuses to arm and CTM sees
`Lockout_Reason` 6 with `Seq_ErrCode` 2.

**Units:** `Cfg_TargetNet` stays in **pounds**. The pounds→divisions
conversion happens in exactly one place in the PLC. Do not send divisions.

---

## 6. Capture-before-reset still holds — and is now stricter

The existing rule stands: read `Res_*` before sending `Cmd_Reset`. In mode 1
there is a second reason. The PLC's reset path also clears the terminal
(`Req_Clear`), which returns it to gross and drops the tare. Once that has
happened the terminal no longer holds the numbers either. There is no second
place to recover them from.

Order is unchanged and non-negotiable:

```
State 5 observed → read Res_GrossWt / Res_TareWt / Res_NetWt / Res_TotalGal
                 → persist to loading_transactions
                 → update bills_of_lading
                 → THEN Cmd_Reset
```

---

## 7. Migration

Per bay, independently:

1. Bay runs mode 0. Nothing changes. This is the current production state.
2. Commission the terminal per §7 of the engineering manual.
3. Set `Cfg_BayScaleSrc[b]` and `Cfg_BayScaleMode[b] = 1`.
4. CTM stops writing that bay's weight tags.
5. Run loads and compare `Res_NetWt` against `Res_TotalGal` before trusting
   tickets from that bay.

Rolling back is setting `Cfg_BayScaleMode[b]` to 0. No code change, no
download.

---

## 8. Status of this work

The PLC code has **not been compiled, imported, or run** — it was written in
a Linux container with no Studio 5000, no FactoryTalk View, and no access to
the terminals. It is source for a Rockwell engineer to import, verify and
test.

A defect was found in the existing `PRG_IND780` while writing this: the
Floating Point example code was imported against an Integer/Divisions module,
and the data-integrity and command-acknowledge checks collapsed into
tautologies. Details in §6 of the engineering manual. **It affects bay 3
today**, in production, and should be treated as the first item rather than
part of this feature.
