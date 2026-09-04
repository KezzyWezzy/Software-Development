# IND780 — Batch Interface Contract (Tare / Target / Start / Done)

Reference for the CTM ↔ CompactLogix ↔ IND780 integration.

**Ownership model this document serves:** the PLC owns safety and permissives,
the IND780 owns custody transfer (tare, net, printed weight), CTM owns the books
and is responsible for communicating with and configuring both.

**Source documents.** METTLER TOLEDO *IND780 Terminal PLC Interface Manual*
(64057518) and *IND780 Terminal Shared Data Reference* (64059110). The tables
below were reconstructed from indexed content of those manuals, not read out of
the PDFs directly. **Verify every bit against the controlling revision of
64057518 for the fieldbus option actually installed before wiring or
commissioning.** Rows marked UNCONFIRMED were not established at all — do not
build to them.

---

## 1. Which interface

Two independent paths reach the terminal. They are not interchangeable.

| Path | Mechanism | Use for |
|---|---|---|
| **Cyclic PLC interface** | Message slots in Integer, Divisions, or Floating Point format | Real-time batch control — tare, target, start, feed status |
| **Shared Data** | Named variable read/write (explicit messaging or SD server) | Configuration, table records, diagnostics, non-cyclic commands |

Batch control belongs on the cyclic interface. Shared Data is the configuration
channel.

---

## 2. Integer / Divisions mode — Discrete Write (PLC → IND780)

One 16-bit data word plus one 16-bit command word per message slot.

### WORD 0 — data value

16-bit **signed** integer. Weight in displayed units (Integer mode) or in
calibrated scale divisions (Divisions mode). Range **±32,767**.

This is the "amount to load." It is loaded into the target register by Bit 15.

### Command word bits

| Bit | Function | Edge / level |
|---|---|---|
| 0–2 | Selects data returned in Discrete Read WORD 0: `0`=gross, `1`=net, `2`=displayed, `3`=tare, `4`=**target**, `5`=rate, `6`/`7`=reserved | value |
| 3 | Load WORD 0 into the **tare register** | 0→1 |
| 4 | CLEAR | 0→1 |
| 5 | **TARE** — terminal captures current weight as tare | 0→1 |
| 6 | PRINT | 0→1 |
| 7 | ZERO | 0→1 |
| 8 | **Start / abort target logic.** `1` = run, `0` = abort all target logic | **level** |
| 9–11 | Display mode control | value |
| 15 | Load WORD 0 into the **target register** and transfer into target logic | 0→1 |

Bit 8 is documented as: the PLC must start the target logic before it can abort
the target logic.

---

## 3. Integer / Divisions mode — Discrete Read status word (IND780 → PLC)

| Bit | Meaning |
|---|---|
| 0 | **Feed** (slow / fine feed active) |
| 1 | **Fast Feed** (coarse feed active) |
| 2 | **Tolerance OK** — in tolerance, material transfer and over/under mode |
| 3 | Under negative tolerance |
| 4 | Over positive tolerance |
| 5 | Comparator 3 active |
| 6 | Comparator 2 active |
| 7 | Comparator 1 active |
| 8 | ENTER key |
| 9–11 | Input 1 / Input 2 / Input 3 status |

Motion (scale unstable) is reported at **bit 12** in the Floating Point status
word. Its position in the Integer-mode status word was **not confirmed** —
verify against 64057518.

---

## 4. Floating Point mode

Four 16-bit input words and three 16-bit output words per message slot.

**Output (PLC → terminal):** `Command`, `FPLoadData1`, `FPLoadData2` — the
latter two forming one 32-bit single-precision value.

**Input (terminal → PLC):**

| Word | Content |
|---|---|
| 0 | `CMD_Response` — high byte carries data-type indication and command acknowledge bits; low byte reserved |
| 1–2 | `FPdata1` / `FPdata2` — 32-bit single-precision value of the requested scale data |
| 3 | `Status` — scale and I/O status bits; bit 12 = motion (unstable) |

The floating-point value may represent gross, tare, net, target, fine gross,
fine tare, fine net, or filter setting.

**UNCONFIRMED:** the Floating Point command code table (the hex/decimal command
values for load-target, start-target, abort-target). Not established. Pull it
from the command table in 64057518 before designing to FP mode.

**Data validity:** use both Data Integrity bits in Floating Point mode, or the
UpdateInProgress bit in Integer mode. Do not latch a custody weight without
them.

---

## 5. Shared Data — the batch registers

### 5.1 Naming

Shared Data variables are `<class><instance><attribute>` — e.g. `wc0101` is
class `wc`, instance `01` (scale A), attribute `01`. Scale B is instance `02`.

### 5.2 Classes relevant to a batch — CONFIRMED

| Class | Contents |
|---|---|
| `sp` | **Full Target Process Data** — the batch/target class |
| `wt` | Dynamic Scale Weight |
| `ws` | Scale Process Data |
| `wc` | Scale Commands |
| `ct` | Scale Tare Setup |

`sp` is the class the batch lives in. That is the confirmed part.

### 5.3 Commands — CONFIRMED

| Variable | Dir | Meaning |
|---|---|---|
| `wc0101` | write | Scale command, scale A. **`1` = tare.** |
| `wx0101` | read | Command status, scale A. `1` = in progress, `0` = complete. Supports a registered callback to get completion status. |

The `wc` → `wx` handshake is the pattern for every command on this path: write
the command, watch the status variable fall back to 0, read the result. Do not
fire and forget.

### 5.4 What is NOT confirmed — do not build to guesses

The **attribute-level map inside `sp`** was not recovered. Specifically unknown:

- which attribute holds the **target value** (amount to load)
- which attribute holds **fine feed / spill / preact / tolerance**
- which attribute **starts** the target and which **aborts** it
- which attribute carries **target status** (feeding, in tolerance, complete)

Search indexing does not carry that table and this environment cannot reach
mt.com. `sp0101 = target` is a plausible guess and it is still a guess — a
wrong attribute number writes a spill value into a target register on a live
loading rack. Get the real table before writing a single line of it.

### 5.5 Fastest way to close the gap

Three routes, best first:

1. **Read it off your own terminal.** The IND780 serves a Shared Data
   Monitoring page from its own web interface —
   `http://<terminal-ip>/IND780/excalweb.dll?webpage=shareddata.htm`. It
   enumerates the live variables with their current values. This beats the
   manual: it shows what *your* terminal, with *your* installed application
   software, actually exposes.
2. **Shared Data Reference 64059110**, the `sp` class section. Get the revision
   matching your firmware — R01 and R12 are both in circulation and the class
   tables changed between them.
3. **The terminal's own setup menu** under the target/material transfer
   configuration — the field order there generally mirrors the attribute order.

### 5.6 Base target ≠ batching

One distinction that matters for scoping. The `sp` class is **single-target
material transfer** — one material, coarse/fine, cut off, check tolerance. That
is a *fill*, not a *batch*.

Multi-phase batching — sequencing, recipes, multiple ingredients, phase state —
is **IND780batch** running the Batch-780 application software, built on an
ISA-S88 structure, with its own shared data surface. If the scope is "the
terminal runs the batch," confirm which product is actually in the panel. A
base IND780 will not do it, and no amount of shared-data writing will make it.

---

## 6. Batch sequence

```
1.  Write WORD 0 = target amount        (divisions or units — see §7)
2.  Pulse Bit 15  (0→1)                 target loaded into target logic
3.  Pulse Bit 5   (0→1)                 terminal captures its own tare
    └─ confirm tare via Bits 0–2 = 3, read WORD 0
4.  Set  Bit 8 = 1                      start target logic  (level, hold it)
5.  Watch Bit 1 (fast feed) → Bit 0 (feed) → both clear
6.  Confirm Bit 2 (tolerance OK), confirm no motion
7.  Latch custody weights
8.  Clear Bit 8 = 0                     release target logic
```

---

## 7. Four things that bite

### 7.1 There is no "batch done" bit

Nothing in the status word says *complete*. Done has to be derived, in PLC
logic, as:

> Feed (bit 0) **falling edge**, having previously been set
> AND Fast Feed (bit 1) clear
> AND Tolerance OK (bit 2) set
> AND no motion
> AND stability timer elapsed

That derived bit is what drives the State 4→5 transition and the custody
capture. Build it as an explicit latch, not as a coincidence of conditions
sampled on one scan.

### 7.2 ±32,767 breaks pound-denominated targets in Integer mode

A 45,000 lb net target **will not fit** in a 16-bit signed integer. Three ways
out:

- **Divisions mode** — 45,000 lb at a 20 lb division = 2,250. Fits comfortably.
  Requires CTM to convert target and to know the division size, and requires
  that division size to be treated as configuration, not a constant.
- **Floating Point mode** — real engineering units, no scaling. Costs the
  multiplexed command sequencing.
- Cap targets below 32,767 — not viable for truck loading.

CTM currently holds `Cfg_TargetNet` in pounds. Whichever path is chosen, the
unit conversion and its rounding behavior belong in exactly one place, and the
BOL must record which unit basis was used.

### 7.3 Bit 8 is a level, not a pulse

One-shotting bit 8 aborts the batch on the next scan. It is held for the
duration of the transfer and cleared to stop. Clearing it is also the stop
command — there is no separate stop bit.

### 7.4 Bit 3 and Bit 5 are not interchangeable — this is the custody boundary

- **Bit 5** — the terminal captures the tare itself, at its own stability
  judgment, inside the sealed device.
- **Bit 3** — the PLC pushes a number into the tare register from WORD 0.

Under the ownership model, **use Bit 5.** Bit 3 puts the origin of the tare
outside the custody device, and a tare the PLC authored is not a tare the
terminal witnessed. Reserve Bit 3 for stored-tare / preset-tare workflows that
are explicitly documented as such on the ticket.

---

## 9. AOP migration — Floating Point example code onto an INTDIV module

Applies when porting IND780 example code written for **Floating Point** mode
onto a module whose definition is **Integer/Divisions**.

### 9.1 Identify the module definition first

The Studio 5000 tag *name* is not evidence of the mode. Read the data type:

```
IND780_Float:I   ->  ME:IND780Enet_INTDIV_1Slots:I:0     <- INTDIV, not FP
IND780_Float:O   ->  ME:IND780Enet_INTDIV_1Slots:O:0
```

`INTDIV` = Integer/Divisions. `_1Slots` = one message slot. A tag named
`IND780_Float` carrying an `INTDIV` type is an Integer/Divisions module with a
misleading name — rename the tag or expect the next engineer to lose an
afternoon.

Structural tell: INTDIV carries **one** `Weight` INT and one `Command` /
`Status` INT per direction. Floating Point carries **two** data words plus a
`CMD_Response`.

### 9.2 Members that do not exist in INTDIV

| FP member | INTDIV equivalent |
|---|---|
| `:O.Slot1FPLoadData1` | none — collapses into `:O.Slot1.Weight` (single INT) |
| `:O.Slot1FPLoadData2` | none — same |
| `:I.Slot1FPdata1` / `FPdata2` | none — collapses into `:I.Slot1.Weight` |
| `:I.Slot1CmndAck1` / `CmndAck2` | **none** — see §9.5 |
| Both Data Integrity bits | `:I.Slot1.UpdateInProgress` + `:I.Slot1.DataOk` |

### 9.3 Output — command bits became named BOOLs

`IND780_Float:O.Slot1.*`

| Command word bit | Member |
|---|---|
| 0–2 readback select | `Select1` / `Select2` / `Select3` |
| 3 load tare | `LoadTare` |
| 4 clear | `Clear` |
| 5 tare | `Tare` |
| 6 print | `Print` |
| 7 zero | `Zero` |
| 8 start / abort target | `AbortStartTarget` |
| 9–11 display mode | `DisplayMode1` / `2` / `3` |
| 15 load target | `LoadTarget` |
| WORD 0 data | `Weight` (INT) |

Also present: `Output1` / `Output2` / `Output3`, and the raw `Command` INT.

### 9.4 Input — status bits became named BOOLs

`IND780_Float:I.Slot1.*`

| Status word bit | Member |
|---|---|
| 0 feed | `Feed` |
| 1 fast feed | `FastFeed` |
| 2 tolerance OK | `Tolerance_Ok` |
| 3 under negative tolerance | `UnderLowTolerance` |
| 4 over positive tolerance | `OverHighTolerance` |
| 5 / 6 / 7 comparators | `Comparator3` / `Comparator2` / `Comparator1` |
| 8 ENTER key | `EnterKey` |
| 9–11 inputs | `Slot5_InputBit1` / `2` / `3` |
| motion | `Motion` |
| — | `NetMode`, `DataOk`, `UpdateInProgress` |

Plus the raw `Status` INT.

**These 16 named BOOLs are the whole word.** Count them — every bit of `Status`
is exposed and named. Nothing is hidden in the raw INT, so a member absent from
this list is absent from the connection. This is the check to run before
concluding a v1 member "must be in there somewhere": if the named BOOLs account
for all 16 bits, they do not.

**Do not drive both the raw INT and the named BOOLs on the same word.** That is
two writers on one tag.

### 9.5 `CmndAck1` / `CmndAck2` have no replacement bit

The v1 Floating Point module exposes **two** acknowledge bits, `CmndAck1` and
`CmndAck2`, in the `CMD_Response` high byte. Treat them as a **2-bit field**,
not two independent flags — the pair is read together.

Command acknowledge is a Floating Point mechanism. FP multiplexes: one command
word, and the returned 32-bit value depends on what was asked for, so the
terminal must echo which command it is answering. Integer/Divisions does not
multiplex — the selector is the three `Select` bits and the value returns in one
`Weight` INT. There is nothing to acknowledge, and neither bit exists on the
connection.

**UNCONFIRMED:** the encoding of the `CmndAck1`/`CmndAck2` pair (which of the
four values means accepted, in-progress, rejected), and whether this pair is the
same thing as the two Data Integrity bits MT tells you to use in Floating Point
mode, or a separate field in the same byte. Not established. If the port stays
on FP, read the `CMD_Response` breakdown in 64057518 before relying on either.

Port it by intent, not by name:

- **Used as a data gate** ("don't read until coherent") → `UpdateInProgress`
  (with `DataOk`). Closest available swap. Two bits become one; if the v1 logic
  branched on the *value* of the pair rather than merely on it being set, that
  distinction is gone.
- **Used as a handshake** ("command landed, advance the sequence") → no bit does
  this. Rebuild it as a readback compare (§9.6). The information does not exist
  on this connection.

Substituting `UpdateInProgress` for a handshake use of `CmndAck1`/`2` compiles
clean and advances the sequence on data that was never confirmed. That is the
failure mode to watch for in this port.

### 9.6 Load-target sequence with readback confirmation

```
1. MOV  target            -> IND780_Float:O.Slot1.Weight
2. Pulse                     IND780_Float:O.Slot1.LoadTarget      (0->1)
3. Set  Select1/2/3 = 4                                  (select target readback)
4. Wait NOT IND780_Float:I.Slot1.UpdateInProgress
        AND IND780_Float:I.Slot1.DataOk
5. CMP  IND780_Float:I.Slot1.Weight = target
        match    -> target accepted; proceed to AbortStartTarget = 1
        mismatch -> fault on timeout; do NOT start
```

Step 5 replaces the ack, and is the stronger check: an acknowledge says the
terminal heard the command, a readback says it holds the right number. On a
target that drives a truck load, verify the value.

Same shape for tare — pulse `Tare`, set the selector to tare, wait for clean
data, read `Weight` back, and record **that** value as the BOL tare.

### 9.7 The ±32,767 ceiling is live on this module

`Weight` is a single 16-bit signed INT. In **Integer** sub-mode a 45,000 lb
target does not fit. In **Divisions** sub-mode it does (45,000 lb at a 20 lb
division = 2,250).

Two things must be settled and written down:

1. Which sub-mode the terminal is configured for.
2. Whether CTM sends pounds or divisions, and where the conversion and its
   rounding live — one place only.

If the ported example code assumed floating-point engineering units, changing
the **module definition** to Floating Point may be cheaper than rewriting to
INTDIV, and removes the ceiling. That regenerates the module-defined tags
again, so decide before doing the port, not after.

---

## 10. Open items before this is buildable

1. Confirm every bit above against the controlling revision of 64057518 for the
   installed fieldbus option.
2. Recover the Floating Point command code table (§4).
3. Recover the `sp` class attribute map from the terminal's own Shared Data
   Monitoring page or from 64059110 at the matching firmware revision (§5.4).
4. Decide Divisions vs Floating Point (§7.2) — this determines the CTM-side
   conversion and the `Cfg_TargetNet` contract.
5. Confirm the physical topology: EtherNet/IP into the CompactLogix, Modbus TCP
   direct to CTM, or both. Determines whether CTM's custody read is a direct
   read or a PLC mirror, and how the two are timestamped against each other for
   the reconciliation cross-check.
