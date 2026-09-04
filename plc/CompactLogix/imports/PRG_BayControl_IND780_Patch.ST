(* ============================================================================
   PRG_BayControl / BayControl  -  IND780 Cfg_Mode 1 integration
   KJV Solutions LLC  /  Continuum Terminal Manager
   ----------------------------------------------------------------------------
   These are INSERTS into the existing BayControl routine, not a replacement.
   The STATE 2 and STATE 3 exit chains are single IF/ELSIF chains by design -
   the existing comments explain why at length, and that structure is not
   changed here. Every insert below either adds one ELSIF at a stated
   position in an existing chain, or adds a block outside the chains.

   Where Cfg_BayScaleMode[i] = 0 not one line of this executes and bay
   behaviour is bit-for-bit what it is today.
   ============================================================================ *)


(* ###########################################################################
   INSERT 1 - near the top of the per-bay loop, beside the existing
   ScaleNetWt resolution (around line 287).
   ########################################################################### *)

(* Resolve the card serving this bay once per scan. BayCard = -1 means the
   bay has no terminal and every Cfg_Mode 1 block below is skipped. *)
IF Cfg_BayScaleSrc[i] >= 1 AND Cfg_BayScaleSrc[i] <= 6 THEN
    BayCard[i] := Cfg_BayScaleSrc[i] - 1;
ELSE
    BayCard[i] := -1;
END_IF;

TermBatch := (BayCard[i] >= 0) AND (Cfg_BayScaleMode[i] = 1);

(* In terminal-batch mode the net on the ticket is the terminal's net, not a
   PLC subtraction. Bay_Scale_Map has already put it in Scale_Net. *)
IF TermBatch AND IND780s[BayCard[i]].Tare_Confirmed THEN
    ScaleNetWt := Bays[i].Scale_Net;
END_IF;


(* ###########################################################################
   INSERT 2 - STATE 1 (READY), replacing the tare-lock block at line 319.

   Cfg_Mode 0 keeps the existing behaviour exactly. Cfg_Mode 1 asks the
   TERMINAL to take the tare - the terminal decides stability, inside the
   sealed device, and the number it captures is the one on the ticket. The
   PLC does not author a custody tare.
   ########################################################################### *)

IF NOT TermBatch THEN

    (* ---- existing behaviour, unchanged ---- *)
    IF Bays[i].Cmd_LockTare AND Bays[i].Scale_Stable THEN
        Bays[i].Tare_Locked := 1;
        Bays[i].Tare_Value  := Bays[i].Scale_Gross;
        Bays[i].Cmd_LockTare := 0;
    END_IF;

ELSE

    (* ---- terminal-batch tare ---- *)
    IF Bays[i].Cmd_LockTare
       AND IND780s[BayCard[i]].Seq_State = 0
       AND NOT IND780s[BayCard[i]].Tare_Confirmed THEN
        (* Step 1 out. The sequencer holds the bit for a clean edge, drops
           it, points the readback at tare, and confirms. *)
        IND780s[BayCard[i]].Req_Tare := 1;
    END_IF;

    IF IND780s[BayCard[i]].Tare_Confirmed THEN
        (* Bay_Scale_Map has already copied Tare_PV into Tare_Value and set
           Tare_Locked. Consume the request. *)
        Bays[i].Cmd_LockTare := 0;
    END_IF;

END_IF;


(* ###########################################################################
   INSERT 3 - STATE 2 (ARMED), at the TOP of the state body, before the
   pump-delay timer (line 364).

   The target is loaded and CONFIRMED BY READBACK before the pump is ever
   permitted. A pump started against an unconfirmed target has no cutoff.
   ########################################################################### *)

IF TermBatch THEN

    (* Step 2 out: push the target. Weight_Out is in the terminal's units. *)
    IF NOT IND780s[BayCard[i]].Target_Confirmed
       AND IND780s[BayCard[i]].Seq_State = 0
       AND IND780s[BayCard[i]].Seq_ErrCode = 0 THEN

        IND780s[BayCard[i]].Target_SP  := Bays[i].Cfg_TargetNet;
        IND780s[BayCard[i]].Weight_Out :=
            REAL_TO_INT(Bays[i].Cfg_TargetNet
                        / IND780s[BayCard[i]].Cfg_Increment);
        IND780s[BayCard[i]].Req_LoadTarget := 1;
    END_IF;

    (* Step 3 out: run the target logic. HELD, not pulsed - clearing this bit
       is the stop, and one-shotting it aborts on the next scan. *)
    IF IND780s[BayCard[i]].Target_Confirmed THEN
        IND780s[BayCard[i]].Req_StartTarget := 1;
    END_IF;

END_IF;


(* ###########################################################################
   INSERT 4 - STATE 2 exit chain, as a NEW ELSIF inserted immediately after
   the existing "ELSIF Bays[i].Scale_Fault THEN" branch (position 2), so it
   sits above the pump and no-flow exits and below the overfill probe.
   ########################################################################### *)

ELSIF TermBatch AND IND780s[BayCard[i]].Seq_ErrCode <> 0 THEN
    (* 2b - the terminal does not hold the target we believe it holds, or a
       readback timed out. Do not arm: there would be no cutoff. *)
    Bays[i].Pump_Permissive := 0;
    Bays[i].Valve_Open := 0;
    Bays[i].Alm_ScaleFault := 1;
    Bays[i].Lockout := 1;
    Bays[i].Lockout_Reason := 6;
    Bays[i].PrevState := 2;
    Bays[i].State := 6;
    StateTimerCnt[i] := 0;


(* ###########################################################################
   INSERT 5 - STATE 2, immediately BEFORE the existing gate that advances to
   STATE 3 (the "ELSIF NOT LowFlowNow" branch, position 7). Add
   Target_Confirmed to that branch's condition rather than adding a branch:

       ELSIF NOT LowFlowNow AND Sts_LowFlowBypassed[i] = 0
             AND (NOT TermBatch OR IND780s[BayCard[i]].Target_Confirmed) THEN

   Nothing else in that branch changes.
   ########################################################################### *)


(* ###########################################################################
   INSERT 6 - STATE 3 exit chain, REPLACING the final branch (position 10,
   normal completion). It stays last in the chain so it cannot mask a fault
   raised in the same scan.
   ########################################################################### *)

ELSIF (NOT TermBatch AND ScaleNetWt >= Bays[i].Cfg_TargetNet)
   OR (TermBatch AND IND780s[BayCard[i]].Batch_Done) THEN
    (* 10 - normal completion.
       Cfg_Mode 0: the PLC's own comparison, as before.
       Cfg_Mode 1: the TERMINAL's derived completion - feed seen then
       dropped, in tolerance, settled. The PLC does not second-guess the
       cutoff; that is the whole point of giving the terminal custody. *)
    Bays[i].PrevState := 3;
    Bays[i].State := 4;
    StateTimerCnt[i] := 0;
    Bays[i].Tmr_Stable := 0;


(* ###########################################################################
   INSERT 7 - CONTROLLED STOP.

   Place at the END of the per-bay loop, AFTER the CASE ... END_CASE, so it
   runs whichever exit the chain took this scan.

   Req_StartTarget is a held level. Clearing it aborts the terminal target
   logic - that IS the stop command; there is no separate one. Any departure
   from STATE 3, for any reason, drops it.
   ########################################################################### *)

IF TermBatch THEN

    IF Bays[i].State <> 2 AND Bays[i].State <> 3 THEN
        IND780s[BayCard[i]].Req_StartTarget := 0;
    END_IF;

    (* An E-Stop or lockout drops it immediately, without waiting for the
       state to change. *)
    IF Bays[i].Cmd_EStop OR Bays[i].EStop_Active OR Bays[i].Lockout THEN
        IND780s[BayCard[i]].Req_StartTarget := 0;
    END_IF;

END_IF;


(* ###########################################################################
   INSERT 8 - STATE 4 (COMPLETING), inside the existing stability block that
   captures results (line 681), replacing the three custody assignments.

   Cfg_Mode 1: the ticket carries the TERMINAL's numbers. Res_GrossWt is not
   recomputed and Res_NetWt is not a PLC subtraction - a net the PLC
   calculated is not a legal-for-trade net.
   ########################################################################### *)

IF TermBatch THEN
    Bays[i].Res_GrossWt := Bays[i].Scale_Net + IND780s[BayCard[i]].Tare_PV;
    Bays[i].Res_TareWt  := IND780s[BayCard[i]].Tare_PV;
    Bays[i].Res_NetWt   := Bays[i].Scale_Net;
ELSE
    Bays[i].Res_GrossWt := Bays[i].Scale_Gross;
    Bays[i].Res_TareWt  := Bays[i].Tare_Value;
    Bays[i].Res_NetWt   := ScaleNetWt;
END_IF;
Bays[i].Res_TotalGal := Bays[i].Flow_Total;


(* ###########################################################################
   INSERT 9 - STATE 0 (IDLE) and STATE 5 (COMPLETE) reset paths, beside the
   existing "Bays[i].Tare_Locked := 0".

   Clears the terminal so the next truck starts from a known place. Req_Clear
   is also what releases a Seq_State 5 timeout.
   ########################################################################### *)

IF TermBatch THEN
    IND780s[BayCard[i]].Req_StartTarget  := 0;
    IND780s[BayCard[i]].Req_Clear        := 1;
    IND780s[BayCard[i]].Tare_Confirmed   := 0;
    IND780s[BayCard[i]].Target_Confirmed := 0;
    IND780s[BayCard[i]].Batch_Done       := 0;
    IND780s[BayCard[i]].Batch_Fault      := 0;
    IND780s[BayCard[i]].Fed_Once         := 0;
ELSE
    (* Req_Clear must not stay latched, or the terminal never sees an edge. *)
    IF BayCard[i] >= 0 THEN
        IND780s[BayCard[i]].Req_Clear := 0;
    END_IF;
END_IF;
