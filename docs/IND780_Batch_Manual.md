# IND780 Terminal Batching — Engineering & Commissioning Manual

**Project:** CTM_CPX (CompactLogix 5069-L330ER, v37)
**Scope:** Six METTLER TOLEDO IND780 EtherNet/IP weigh terminals, one per bay
**Rev:** 1.0

---

## 1. What this adds

Each bay can now run its load-out one of two ways, selected per bay in PLC
configuration. Nothing about bay 1 changes because bay 2 is switched over.

| `Cfg_BayScaleMode[b]` | Name | Who runs the cutoff |
|---|---|---|
| **0** | Monitor | PLC. Weight arrives from CTM / the simulator or from the terminal as a plain reading; `PRG_BayControl` compares net against target and cuts off. **This is today's behaviour, unchanged.** |
| **1** | Terminal batch | The IND780. The PLC writes the tare, target and start commands and acts on the terminal's completion. |

Under mode 1 the ownership split is:

- **PLC** — safety, permissives, the bay state machine, the controlled stop.
- **IND780** — custody transfer. It captures its own tare, runs its own
  coarse/fine cutoff with its own preact, and reports in-tolerance.
- **CTM** — the books, and still the permissive. The PLC will not start a
  load CTM has not authorized.

---

## 2. The load-out sequence — what goes out, what comes back

This is the contract. Every step names the PLC tag written, the terminal
command bit behind it, and the input the PLC waits for before moving on.

| # | Phase | PLC writes (out to IND780) | PLC waits for (in from IND780) | Fails to |
|---|---|---|---|---|
| 0 | Bay idle | `Req_Clear` pulse | `NetMode` clear, `Seq_State` = 0 | — |
| 1 | **Tare** | `Req_Tare` (0→1, held 2 scans) | `UpdateInProgress` clear, then `Motion` clear **and** `NetMode` set | `Seq_ErrCode` 1 |
| 1b | Confirm tare | `Req_SelTare` (readback selector = 3) | `Weight_Raw` → `Tare_PV`; `Tare_Confirmed` set | `Seq_ErrCode` 1 |
| 2 | **Load target** | `Weight_Out` = target ÷ increment, then `Req_LoadTarget` (0→1) | `UpdateInProgress` clear | `Seq_ErrCode` 1 |
| 2b | Confirm target | `Req_SelTarget` (readback selector = 4) | `Weight_Raw` × increment within `Cfg_TolWindow` of `Target_SP` → `Target_Confirmed` | `Seq_ErrCode` 2 |
| 3 | **Start** | `Req_StartTarget` = 1 — **held for the whole load** | `FastFeed` then `Feed` — sets `Fed_Once` | STATE 2 no-flow timeout |
| 4 | Loading | selector returned to gross (`Req_SelGross`) | `Weight_PV` live; `Tolerance_Ok`, `Motion` monitored | scale-fault exits |
| 5 | **Cutoff** | *(nothing — the terminal cuts off on its own preact)* | `FastFeed` clears, then `Feed` clears | — |
| 6 | **Done** | *(nothing)* | `Fed_Once` **and** `Feed` clear **and** `FastFeed` clear **and** `Motion` clear, held 2 s → `Batch_Done` | `Batch_Fault` if `Tolerance_Ok` is clear |
| 7 | **Stop** | `Req_StartTarget` = 0 | `Feed` / `FastFeed` clear | — |
| 8 | Capture | *(nothing)* | `Tare_PV`, `Scale_Net` → `Res_TareWt`, `Res_NetWt`, `Res_GrossWt` | — |
| 9 | Reset | `Req_Clear` pulse | `Seq_State` → 0, `NetMode` clear | — |

### The three things that are not obvious

**There is no "batch done" bit.** The terminal does not have one. Step 6
derives it and latches it. `Fed_Once` is load-bearing: without it, the
completion test is satisfied *at rest before the load starts*, because with
nothing moving, feed is off and tolerance is met.

**Start is a held level, not a pulse.** `Req_StartTarget` maps to the
terminal's `AbortStartTarget` bit. Set = run, clear = abort. One-shotting it
aborts the batch on the next scan. **Clearing it is the stop command** —
there is no separate stop.

**There is no command acknowledge.** `CmdAck` exists only in Floating Point
mode. This project is Integer/Divisions. Every value written is confirmed by
reading it back (steps 1b, 2b), which is the stronger check anyway: an
acknowledge says the terminal heard you, a readback says it holds the right
number.

---

## 3. Controlled stop

`Req_StartTarget` drops on every one of these, and dropping it aborts the
terminal target logic immediately:

- Bay leaves STATE 2 or STATE 3 for any reason
- `Cmd_EStop`, `EStop_Active`, or `Lockout`
- CTM permissive withdrawn (`Cfg_CTMPermissiveMode` 1 → controlled stop with
  a ticket; 2 → fault, no ticket)
- Overfill probe, scale fault, pump fault, no-flow, ground loss, DOT gross
  limit, source tank low

The pump and valve outputs are dropped by the existing STATE 3 exit chain on
the same scan. The terminal abort is additional to that, not instead of it.

**The exit chain in STATE 2 and STATE 3 must remain a single IF/ELSIF
chain.** The existing comments explain why; the IND780 work adds branches at
stated positions and does not restructure it.

---

## 4. Configuration

### Per bay — `Cfg_BayScaleSrc[10]`, `Cfg_BayScaleMode[10]`

| Tag | Values |
|---|---|
| `Cfg_BayScaleSrc[b]` | 0 = no terminal; 1–6 = which IND780 card serves bay *b* |
| `Cfg_BayScaleMode[b]` | 0 = monitor; 1 = terminal batch |

### Per card — `IND780s[c]`

| Member | Set to |
|---|---|
| `Cfg_Enabled` | 1 when the module exists and is commissioned |
| `Cfg_Increment` | **Division size in lbs.** Must match terminal calibration |
| `Cfg_TolWindow` | Readback compare window, lbs. Default 1.0 |
| `Cfg_AckTimeout` | Scans before a readback is declared failed. Default 100 |

### `Cfg_Increment` is the one that will cost you a truck

It is **not** read from the terminal. If the terminal is calibrated at a
20 lb division and `Cfg_Increment` says 10.0, every weight in the system is
half the real value and every ticket is wrong by the same factor — with no
alarm anywhere, because nothing is inconsistent. Verify it against a known
test weight before releasing the bay. See §7.

### The ±32,767 ceiling

`Weight_Raw` and `Weight_Out` are single 16-bit signed INTs. A 45,000 lb
target does **not** fit in display units. At a 20 lb division it is 2,250 and
fits comfortably. **The terminal must be in Divisions sub-mode**, and
`Cfg_Increment` is the division size. `REAL_TO_INT(target / Cfg_Increment)`
in INSERT 3 is that conversion and it exists in exactly one place.

---

## 5. Module setup in Studio 5000

Six modules, named **`IND780_1` … `IND780_6`**, the number being the bay served.
The existing `IND780_Float` is bay 3's terminal and must be **renamed to
`IND780_3`**.

Each module:

- Revision **2.005** (Major 2, Minor 5)
- Data format **Integer/Divisions**, **one** message slot
- Byte order **Word Swap**
- Electronic Keying: **Compatible Module**

**1.0 → 2.005 is a major revision change.** Under Compatible Keying the major
must match exactly, so an existing 1.x module will fault the connection until
its definition is updated. Do not reach for Disable Keying — that moves the
failure somewhere worse. Changing the Module Definition deletes and recreates
the module-defined tags, so every rung referencing them goes to verification
errors at once. Do it on a copy, get it verifying clean, then deploy.

The old `IND780_Integer` module (Major 1, Minor 1) is superseded and should be
deleted once bay 3 is proved on `IND780_3`.

---

## 6. Defect found in the existing code — fix before commissioning

The Floating Point example code in `PRG_IND780` was imported against a
module that is **Integer/Divisions**, not Floating Point. The FP-only members
(`DataIntegrity`, `DataIntegrity2`, `CmndAck1`, `CmndAck2`, `FPdata1/2`) do
not exist on this connection, and the references collapsed onto `DataOk`.

Three consequences, all live in the running code:

1. **`Bay_Scale_Map`** computed
   `FP_Ok := DataOk AND ((DataOk AND DataOk) OR (NOT DataOk AND NOT DataOk))`.
   The parenthesised term is a tautology. The integrity gate the comment
   describes was never applied. **Fixed** in the revised routine.

2. **`Floating_Point` rung 3** drives `CMD_Ack.0` and `CMD_Ack.1` from the
   *same* bit (`UpdateInProgress`), so the 2-bit ack code can only ever be 0
   or 3 and `Command_Acked` is meaningless.

3. **`Floating_Point` rung 2** does `CPS(IND780_Float:I.Slot1,
   FloatingPoint_Data, 1)` and rung 4 does `COP(Command_Data,
   IND780_Float:O.Slot1, 2)`. On an INTDIV structure these copy the BOOL
   carrier bytes into a REAL, and write two words of REAL over the command
   bits. `FloatingPoint_Data` is not a weight, and the output copy scribbles
   on the command word.

**The `Floating_Point` and `Integer` routines are demonstration code and
should be removed from the scan** once `Card_IO_Map` and `Batch_Sequencer`
are in. Leaving rung 4's `COP` in place while the new code drives the same
output structure is two writers on one word.

---

## 7. Commissioning checks

Per card, in order. Do not skip 3.

1. **Connection.** `IND780s[c].Comm_OK` = 1 with the terminal powered;
   pull the Ethernet cable and confirm it goes to 0 and the bay faults with
   `Lockout_Reason` 6. A frozen `DataOk` must not read as healthy.
2. **Gross tracking.** `Weight_PV` follows the terminal display in gross.
3. **Increment.** Put a **known test weight** on the scale. `Weight_PV` must
   match it. If it is off by a constant ratio, `Cfg_Increment` is wrong.
4. **Tare.** Command `Req_Tare`. Terminal goes to NET, `Tare_Confirmed` sets,
   `Tare_PV` matches the terminal's tare display.
5. **Target readback.** Load a target. `Target_Confirmed` sets. Then load a
   deliberately different target and confirm `Target_Confirmed` clears and
   re-confirms at the new value.
6. **Readback mismatch.** Force `Cfg_TolWindow` to 0.1 and a target that
   cannot land inside it; confirm `Seq_ErrCode` 2 and that the bay refuses to
   arm (STATE 2 → 6, `Lockout_Reason` 6).
7. **Batch.** Run a load. Confirm `FastFeed` → `Feed` → both clear →
   `Batch_Done` two seconds later, and that STATE 3 → 4 on `Batch_Done`.
8. **Controlled stop.** Mid-load, drop the CTM permissive. Confirm
   `Req_StartTarget` clears, feed stops, and the bay completes (mode 1) or
   faults (mode 2) per `Cfg_CTMPermissiveMode`.
9. **Terminal lost mid-batch.** Pull the cable during a load. Confirm
   `Batch_Fault`, `Seq_ErrCode` 3, pump permissive dropped, no ticket.
10. **Out of tolerance.** Confirm a load that settles outside tolerance sets
    `Batch_Fault` and does not complete as a clean load.

---

## 8. PanelView tags

All bind directly to `IND780s[c]` — no additional mapping layer.

**Per-card status block**

| Tag | Type | Display |
|---|---|---|
| `IND780s[c].Weight_PV` | REAL | Live weight, lbs |
| `IND780s[c].Tare_PV` | REAL | Custody tare |
| `IND780s[c].Target_SP` | REAL | Target |
| `IND780s[c].Status` | DINT | 0 OK / 1 Warn / 2 Alarm / 3 Fault → colour |
| `IND780s[c].Quality` | DINT | 0 Good / 1 Uncertain / 2 Bad |
| `IND780s[c].Seq_State` | DINT | 0 Idle / 1 Write / 2 Wait / 3 Readback / 4 Confirmed / 5 Timeout |
| `IND780s[c].Seq_ErrCode` | DINT | 0 None / 1 Timeout / 2 Mismatch / 3 TerminalLost / 4 NetMode / 5 OutOfTol |

**Indicator lamps** — `Comm_OK`, `DataOk`, `Motion`, `NetMode`, `FastFeed`,
`Feed`, `Tolerance_Ok`, `UnderLowTolerance`, `OverHighTolerance`,
`Tare_Confirmed`, `Target_Confirmed`, `Batch_Running`, `Batch_Done`,
`Batch_Fault`.

**Comparators.** `Comparator1..3` are independent terminal thresholds. They
are **not** batch logic and must not be shown as batch state. Label them for
what they are configured as at the terminal, or leave them off the screen.

**Mode banner.** Show `Cfg_BayScaleMode[b]` per bay so the operator knows
which scheme is running that bay. A bay in mode 0 behaves differently on
stop and on completion, and the screen should not hide that.

---

## 9. Files

| File | Goes to |
|---|---|
| `plc/CompactLogix/imports/IND780.L5X` | Import as a User-Defined Type |
| `plc/CompactLogix/imports/PRG_IND780_Card_IO_Map.ST` | New ST routine in `PRG_IND780` |
| `plc/CompactLogix/imports/PRG_IND780_Batch_Sequencer.ST` | New ST routine in `PRG_IND780` |
| `plc/CompactLogix/imports/PRG_IND780_Bay_Scale_Map.ST` | Replaces the existing routine body |
| `plc/CompactLogix/imports/PRG_BayControl_IND780_Patch.ST` | Nine numbered inserts into `BayControl` |
| `plc/CompactLogix/imports/IND780_New_Tags.csv` | New controller and program tags |
| `docs/CTM_IND780_Handover.md` | The CTM-side contract |

`PRG_IND780/MainRoutine` gains two JSRs, in this order, before the existing
`Bay_Scale_Map` JSR:

```
JSR(Card_IO_Map,0);
JSR(Batch_Sequencer,0);
JSR(Bay_Scale_Map,0);
```

`PRG_IND780` already runs before `PRG_BayControl` in MainTask. Keep it that
way — the header comment in the old `Bay_Scale_Map` claiming otherwise is
stale and has been corrected.

---

## 10. Verification status

**This code has not been compiled, imported, or run.** No Studio 5000 or
FactoryTalk View tooling exists in the environment it was written in — it is
a Linux container with no Rockwell software and no access to the terminals.
Everything here is source to be imported, verified and tested by someone at a
station with Studio 5000 and the hardware.

Two items in the interface contract remain unconfirmed against the MT
manuals and are flagged where they appear:

- the `CmndAck1` / `CmndAck2` encoding in Floating Point mode (not used by
  this design, which is Integer/Divisions)
- the ordering of `Comparator1..3` within status word bits 5–7 — which is why
  the code uses the AOP's named BOOL members and never bit numbers

Verify every bit against the controlling revision of the IND780 PLC Interface
Manual (64057518) for the installed fieldbus option before energizing.
