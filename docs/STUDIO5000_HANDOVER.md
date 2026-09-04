# Studio 5000 + PanelView Handover — IND780 Terminal Batching

**To:** whoever is picking this up at a station with Studio 5000 Logix Designer and FactoryTalk View.
**Project:** CTM_CPX — CompactLogix 5069-L330ER, firmware v37.11
**Source:** `github.com/KezzyWezzy/Software-Development`, branch `claude/ind780-batch-processing-7weoad` (PR #8)

Read this end to end before opening Studio 5000. Section 2 is a production defect that is live right now and is not part of the feature.

---

## 0. What you are being handed, and what state it is in

Source code, unbuilt. **None of it has been compiled, imported, or run.** It was written in a Linux container with no Rockwell software and no network path to the terminals. Every line is a proposal until you verify it at a station.

That means the usual assumptions do not hold:
- Tag names in the ST were written against an L5X export, not against a project open in Studio 5000.
- The ST has never been through the syntax checker.
- The UDT L5X is well-formed XML but has never been imported.
- The PanelView side is a specification only — no `.apa`, no screens, nothing built.

Treat every file as a first draft by someone who could not test it, because that is what it is.

---

## 1. What the change does

Each bay gets a configuration choice for who runs the load cutoff.

| `Cfg_BayScaleMode[b]` | Who cuts off | Notes |
|---|---|---|
| **0** | PLC | Today's behaviour, bit for bit. |
| **1** | The IND780 terminal | PLC writes tare / target / start; terminal runs its own coarse-fine cutoff with its own preact; PLC acts on the completion it derives. |

Ownership under mode 1: **PLC** owns safety, permissives and the bay state machine. **IND780** owns custody transfer — it captures its own tare and the ticket carries its numbers. **CTM** owns the books and still owns the permissive.

A bay in mode 0 is untouched by any of this. Rollback is one config value, no download.

---

## 2. Do this first — existing defect, in production, bay 3

`PRG_IND780` contains METTLER TOLEDO's Floating Point example code. It was imported against a module that is **Integer/Divisions**, not Floating Point.

Check it yourself before believing me — open the module properties on `IND780_Float` and read the data type:

```
IND780_Float:I  ->  ME:IND780Enet_INTDIV_1Slots:I:0
```

`INTDIV`, not FP. That module has no `DataIntegrity`, `DataIntegrity2`, `CmndAck1`, `CmndAck2`, `FPdata1` or `FPdata2` members. The example's references to them collapsed onto `DataOk`. Three live consequences:

**2.1 — The integrity gate is a tautology.** `Bay_Scale_Map` computes:

```
FP_Ok := DataOk AND ((DataOk AND DataOk) OR (NOT DataOk AND NOT DataOk));
```

The parenthesised half is TRUE for every value of `DataOk`. The gate its own comment describes has never been applied.

**2.2 — The command ack is meaningless.** `Floating_Point` rung 3 drives `CMD_Ack.0` and `CMD_Ack.1` from the *same* bit (`UpdateInProgress`). A two-bit code driven from one source can only read 0 or 3, so `Command_Acked` carries no information.

**2.3 — Two instructions are writing over the wrong memory.**
- Rung 2: `CPS(IND780_Float:I.Slot1, FloatingPoint_Data, 1)` — on an INTDIV structure this copies the hidden BOOL carrier bytes into a REAL. `FloatingPoint_Data` is not a weight.
- Rung 4: `COP(Command_Data, IND780_Float:O.Slot1, 2)` — writes two words of REAL over the **command bits**.

**Action:** the `Floating_Point` and `Integer` routines are demonstration code. Take them out of the scan. Leaving rung 4's `COP` in place while the new code drives the same output structure puts two writers on one word. The revised `Bay_Scale_Map` in this handover fixes 2.1.

---

## 3. Module setup

Six modules, named **`IND780_1` … `IND780_6`**, the number being the bay served. The existing `IND780_Float` is bay 3's terminal — **rename it to `IND780_3`**. The old `IND780_Integer` (Major 1, Minor 1) is superseded; delete it once bay 3 is proved.

Each module:

| Setting | Value |
|---|---|
| Revision | **2.005** (Major 2, Minor 5) |
| Data format | **Integer/Divisions** |
| Message slots | **1** |
| Byte order | **Word Swap** |
| Electronic Keying | **Compatible Module** |

### Two things about the revision change

**1.0 → 2.005 is a MAJOR revision change.** Under Compatible Keying the major must match exactly, so an existing 1.x module faults the connection until its definition is updated. Do not reach for Disable Keying — that moves the failure somewhere worse.

**Changing the Module Definition deletes and recreates the module-defined tags.** Every rung referencing them goes to verification errors at once. Do it on a copy, get it verifying clean, then deploy. Do not do this live against the rack.

### Terminal-side configuration

At each IND780: Integer/**Divisions** sub-mode, one message slot, Word Swap, and the target (Material Transfer) configured with its coarse/fine feed, preact and tolerance. The terminal owns the cutoff — if its preact is not set up, mode 1 will overshoot and nothing in the PLC will save it.

---

## 4. Import order

From the branch, `plc/CompactLogix/imports/`:

| Step | File | How |
|---|---|---|
| 1 | `IND780.L5X` | Import as User-Defined Type |
| 2 | `IND780_New_Tags.csv` | Create the tags it lists. **Scope column says where each belongs** — some are controller, some `PRG_IND780`, some `PRG_BayControl` |
| 3 | `PRG_IND780_Card_IO_Map.ST` | New ST routine in `PRG_IND780`, named `Card_IO_Map` |
| 4 | `PRG_IND780_Batch_Sequencer.ST` | New ST routine in `PRG_IND780`, named `Batch_Sequencer` |
| 5 | `PRG_IND780_Bay_Scale_Map.ST` | Replaces the body of the existing `Bay_Scale_Map` |
| 6 | `PRG_BayControl_IND780_Patch.ST` | **Nine numbered inserts** into `BayControl`. Not a replacement — see §5 |

Then in `PRG_IND780/MainRoutine`, the JSRs in this order, before the existing `Bay_Scale_Map` call:

```
JSR(Card_IO_Map,0);
JSR(Batch_Sequencer,0);
JSR(Bay_Scale_Map,0);
```

`PRG_IND780` already runs before `PRG_BayControl` in MainTask. Keep it that way. (A comment in the old `Bay_Scale_Map` claims it is scheduled last — that comment is stale and has been corrected.)

---

## 5. The BayControl inserts — read before you touch that routine

`PRG_BayControl/BayControl` STATE 2 and STATE 3 each have an exit chain written as a **single IF/ELSIF chain**. The existing comments explain at length why: written as separate IF statements, the last match wins, which lets a low-priority exit such as the CTM permissive overwrite a latched overfill or scale fault and hand the bay back as though nothing happened.

**That structure does not change.** The nine inserts either add one ELSIF at a stated position in an existing chain, or add a block outside the chains. Insert 5 in particular is not a new branch — it adds a condition to an existing one. Follow the positions as written.

---

## 6. The three things that make this work

**There is no batch-done bit.** The terminal does not have one. Completion is derived in `Batch_Sequencer` and latched: feed seen at least once (`Fed_Once`), then feed and fast feed both clear, in tolerance, no motion, held two seconds. `Fed_Once` is load-bearing — without it the test is satisfied *at rest before the load starts*, because with nothing moving, feed is off and tolerance is met.

**There is no command acknowledge.** `CmdAck` exists only in Floating Point mode. Every value written to the terminal is confirmed by **reading it back** — the sequencer points the readback selector at what it just wrote and compares. A readback proves the terminal holds the right number; an acknowledge only proves it heard you. The pump is never permitted before `Target_Confirmed`.

**Start is a held level, not a pulse.** `Req_StartTarget` maps to the terminal's `AbortStartTarget` bit: set = run, clear = abort. One-shotting it aborts on the next scan. **Clearing it is the stop command** — there is no separate stop.

---

## 7. The ±32,767 ceiling — settle this before commissioning

`Weight_Raw` and `Weight_Out` are single 16-bit signed INTs. A 45,000 lb target **does not fit** in display units. At a 20 lb division it is 2,250 and fits comfortably.

So: **the terminals must be in Divisions sub-mode**, and `IND780s[c].Cfg_Increment` is the division size in lbs. The conversion `REAL_TO_INT(target / Cfg_Increment)` lives in exactly one place (Insert 3) and must stay that way.

`Cfg_Increment` is **not** read from the terminal. If the terminal is calibrated at 20 lb and `Cfg_Increment` says 10.0, every weight in the system is half the real value and every ticket is wrong by the same factor — **with no alarm anywhere**, because nothing is internally inconsistent. Verify it against a known test weight (check 3 below) before releasing any bay.

---

## 8. Commissioning checks, per card

Do not skip 3.

1. **Connection.** `Comm_OK` = 1 with the terminal up. Pull the Ethernet cable: it must go to 0 and the bay must fault with `Lockout_Reason` 6. A frozen `DataOk` must not read as healthy — this is why `Comm_OK` comes from GSV `EntryStatus` and not from a status bit inside the input image.
2. **Gross tracking.** `Weight_PV` follows the terminal display in gross.
3. **Increment.** Known test weight on the scale; `Weight_PV` must match it. Off by a constant ratio means `Cfg_Increment` is wrong.
4. **Tare.** Command `Req_Tare`. Terminal goes to NET, `Tare_Confirmed` sets, `Tare_PV` matches the terminal's tare display.
5. **Target readback.** Load a target, confirm `Target_Confirmed`. Load a different one; confirm it clears and re-confirms at the new value.
6. **Readback mismatch.** Force `Cfg_TolWindow` to 0.1 with a target that cannot land inside it. Confirm `Seq_ErrCode` 2 and that the bay refuses to arm (STATE 2 → 6, `Lockout_Reason` 6).
7. **Batch.** Run a load. `FastFeed` → `Feed` → both clear → `Batch_Done` two seconds later → STATE 3 → 4.
8. **Controlled stop.** Mid-load, drop the CTM permissive. `Req_StartTarget` clears, feed stops, bay completes (`Cfg_CTMPermissiveMode` 1) or faults (mode 2).
9. **Terminal lost mid-batch.** Pull the cable during a load. `Batch_Fault`, `Seq_ErrCode` 3, pump permissive dropped, **no ticket**.
10. **Out of tolerance.** A load that settles outside tolerance must set `Batch_Fault` and must not complete as a clean load.

---

## 9. PanelView

Everything binds directly to `IND780s[c]` — no mapping layer needed.

**Numeric block, per card**

| Tag | Type | Display |
|---|---|---|
| `IND780s[c].Weight_PV` | REAL | Live weight, lbs |
| `IND780s[c].Tare_PV` | REAL | Custody tare |
| `IND780s[c].Target_SP` | REAL | Target |
| `IND780s[c].Status` | DINT | 0 OK / 1 Warn / 2 Alarm / 3 Fault → colour |
| `IND780s[c].Quality` | DINT | 0 Good / 1 Uncertain / 2 Bad |
| `IND780s[c].Seq_State` | DINT | 0 Idle / 1 Write / 2 Wait / 3 Readback / 4 Confirmed / 5 Timeout |
| `IND780s[c].Seq_ErrCode` | DINT | 0 None / 1 ReadbackTimeout / 2 ReadbackMismatch / 3 TerminalLost / 4 NetMode / 5 OutOfTolerance |

**Lamps** — `Comm_OK`, `DataOk`, `Motion`, `NetMode`, `FastFeed`, `Feed`, `Tolerance_Ok`, `UnderLowTolerance`, `OverHighTolerance`, `Tare_Confirmed`, `Target_Confirmed`, `Batch_Running`, `Batch_Done`, `Batch_Fault`.

**Three display rules that matter**

- **`Comm_OK` = 0 means the weight on screen is not live.** It must be visually unmistakable — grey the number out or overlay it, not a small lamp in a corner. A stale weight shown as a live weight is the failure this whole design is built to prevent.
- **`Comparator1..3` are not batch state.** They are independent thresholds configured at the terminal. Label them for whatever they are actually configured as, or leave them off the screen entirely. Do not show them as part of the load sequence.
- **Show `Cfg_BayScaleMode[b]` per bay.** A mode 0 bay and a mode 1 bay behave differently on stop and on completion. The operator needs to know which one they are looking at.

---

## 10. Two answers needed from Keith before commissioning

1. Confirm module naming `IND780_1`…`IND780_6`, with bay 3's `IND780_Float` renamed to `IND780_3`.
2. Confirm the terminals are in **Divisions** sub-mode and give the calibrated division size per terminal for `Cfg_Increment`.

---

## 11. Two things deliberately left unverified

Both are marked in the code and in `IND780_PLC_Interface_Contract.md`, and neither was guessed at:

- The `sp` Shared Data class attribute map and the Floating Point command code table. Not recoverable from where this was written. Not needed by this design (it is Integer/Divisions and uses the cyclic interface), but noted if anyone later moves to FP.
- The ordering of `Comparator1..3` within status word bits 5–7. Sources conflict. **This is why the code uses the AOP's named BOOL members everywhere and never bit numbers** — the ambiguity cannot reach the logic. Keep it that way.

Verify every bit against the controlling revision of the IND780 PLC Interface Manual (64057518) for the installed fieldbus option before energizing.

---

## 12. Other documents on the branch

| File | What it is |
|---|---|
| `docs/IND780_Batch_Manual.md` | Engineering + commissioning manual. Full out/in step table for a load-out |
| `docs/CTM_IND780_Handover.md` | The CTM-side contract — what the app must stop writing in mode 1 |
| `IND780_PLC_Interface_Contract.md` | The underlying command/status surface, plus the FP→INTDIV AOP migration map (§9) |
