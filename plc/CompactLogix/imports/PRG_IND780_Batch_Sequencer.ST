(* ============================================================================
   Batch_Sequencer  -  PRG_IND780        Type: Structured Text
   KJV Solutions LLC  /  Continuum Terminal Manager
   ----------------------------------------------------------------------------
   PURPOSE
   Runs the PLC-driven load-out sequence against each IND780 that is
   configured for it (IND780s[c].Cfg_Mode = 1). Indexed - one body, six cards.

   OWNERSHIP
     PLC   owns safety, permissives and the bay state machine.
     IND780 owns custody transfer - it captures its own tare and runs its own
            cutoff. The PLC commands it and reads the result; the PLC never
            computes a custody number.
     CTM   owns the books and still owns the permissive. Nothing here starts a
            load that CTM has not authorized - PRG_BayControl gates that.

   THE COMPLETION PROBLEM
   The terminal has no "batch done" bit. Completion is DERIVED here and
   latched, from: feed seen at least once, then feed and fast feed both clear,
   then in tolerance, no motion, and a stability hold. Sampling those five
   conditions on one scan without Fed_Once produces a false complete before
   the batch has started, because at rest feed is off and tolerance is met.

   COMMAND CONFIRMATION
   Integer/Divisions mode has no command-acknowledge bit - CmdAck exists only
   in Floating Point mode. Every value written to the terminal is therefore
   confirmed by READING IT BACK, not by an acknowledge. A readback proves the
   terminal holds the right number; an acknowledge only proves it heard us.
   On a value that drives a truck load, hold out for the number.
   ============================================================================ *)


FOR CardIdx := 0 TO 5 DO

  (* Cards not configured for PLC-driven batching are skipped entirely. In
     Cfg_Mode 0 this routine writes nothing - no request bit, no Weight_Out -
     so a bay left on the old scheme is untouched by any of this. *)

  IF IND780s[CardIdx].Cfg_Enabled AND IND780s[CardIdx].Cfg_Mode = 1 THEN

    (* -----------------------------------------------------------------------
       A. Terminal lost mid-sequence.

       Checked before the state machine so that no state can advance on data
       from a terminal that is not there. Batch_Fault latches; only Seq 0
       entry clears it.
       ----------------------------------------------------------------------- *)

    IF NOT IND780s[CardIdx].Comm_OK OR NOT IND780s[CardIdx].DataOk THEN
      IF IND780s[CardIdx].Batch_Running OR IND780s[CardIdx].Seq_State <> 0 THEN
        IND780s[CardIdx].Batch_Fault  := 1;
        IND780s[CardIdx].Seq_ErrCode  := 3;
      END_IF;
      IND780s[CardIdx].Batch_Running   := 0;
      IND780s[CardIdx].Tare_Confirmed  := 0;
      IND780s[CardIdx].Target_Confirmed := 0;
      IND780s[CardIdx].Req_StartTarget := 0;
      IND780s[CardIdx].Seq_State       := 0;
      IND780s[CardIdx].Stable_Timer    := 0;

    ELSE

      (* ---------------------------------------------------------------------
         B. Readback scaling.

         Whatever the select bits are currently asking for comes back in the
         same Weight_Raw word. Readback_PV is that value in lbs.
         --------------------------------------------------------------------- *)

      IND780s[CardIdx].Readback_PV := IND780s[CardIdx].Weight_Raw
                                      * IND780s[CardIdx].Cfg_Increment;


      (* ---------------------------------------------------------------------
         C. Command / confirm sequencer.

         Seq_State  0 IDLE          nothing outstanding
                    1 WRITE         request bit held, value in Weight_Out
                    2 WAIT_COHERENT wait out UpdateInProgress
                    3 READBACK      selector set, compare Readback_PV
                    4 CONFIRMED     one scan, then back to IDLE
                    5 TIMEOUT       no match inside Cfg_AckTimeout scans
         --------------------------------------------------------------------- *)

      CASE IND780s[CardIdx].Seq_State OF

        0:  (* IDLE - the request bits are raised by PRG_BayControl. *)
            IND780s[CardIdx].Seq_Timer := 0;
            IF IND780s[CardIdx].Req_Tare
               OR IND780s[CardIdx].Req_LoadTarget THEN
              IND780s[CardIdx].Seq_State := 1;
              IND780s[CardIdx].Seq_ErrCode := 0;
            END_IF;

        1:  (* WRITE - the request bit is already on the wire via Card_IO_Map.
               Hold it one full scan so the terminal sees a clean 0->1 edge. *)
            IND780s[CardIdx].Seq_Timer := IND780s[CardIdx].Seq_Timer + 1;
            IF IND780s[CardIdx].Seq_Timer >= 2 THEN

              (* Point the readback at what we just wrote. *)
              IF IND780s[CardIdx].Req_LoadTarget THEN
                IND780s[CardIdx].Req_SelTarget := 1;
                IND780s[CardIdx].Req_SelTare   := 0;
              ELSE
                IND780s[CardIdx].Req_SelTare   := 1;
                IND780s[CardIdx].Req_SelTarget := 0;
              END_IF;

              (* Drop the command bit. It is edge-triggered at the terminal;
                 leaving it set blocks the next command of the same kind. *)
              IND780s[CardIdx].Req_Tare       := 0;
              IND780s[CardIdx].Req_LoadTarget := 0;

              IND780s[CardIdx].Seq_Timer := 0;
              IND780s[CardIdx].Seq_State := 2;
            END_IF;

        2:  (* WAIT_COHERENT *)
            IND780s[CardIdx].Seq_Timer := IND780s[CardIdx].Seq_Timer + 1;
            IF NOT IND780s[CardIdx].UpdateInProgress THEN
              IND780s[CardIdx].Seq_State := 3;
            ELSIF IND780s[CardIdx].Seq_Timer > IND780s[CardIdx].Cfg_AckTimeout THEN
              IND780s[CardIdx].Seq_ErrCode := 1;
              IND780s[CardIdx].Seq_State   := 5;
            END_IF;

        3:  (* READBACK - compare against what we intended. *)
            IND780s[CardIdx].Seq_Timer := IND780s[CardIdx].Seq_Timer + 1;

            IF IND780s[CardIdx].Req_SelTarget THEN
              SeqExpected[CardIdx] := IND780s[CardIdx].Target_SP;
            ELSE
              SeqExpected[CardIdx] := IND780s[CardIdx].Weight_PV;
            END_IF;

            SeqDelta[CardIdx] := ABS(IND780s[CardIdx].Readback_PV
                                     - SeqExpected[CardIdx]);

            IF IND780s[CardIdx].Req_SelTarget THEN

              (* Target: the terminal must hold the number we sent. *)
              IF SeqDelta[CardIdx] <= IND780s[CardIdx].Cfg_TolWindow THEN
                IND780s[CardIdx].Target_Confirmed := 1;
                IND780s[CardIdx].Seq_State := 4;
              ELSIF IND780s[CardIdx].Seq_Timer > IND780s[CardIdx].Cfg_AckTimeout THEN
                IND780s[CardIdx].Seq_ErrCode := 2;
                IND780s[CardIdx].Seq_State   := 5;
              END_IF;

            ELSE

              (* Tare: whatever the terminal captured IS the custody tare.
                 There is nothing to compare it against - the terminal chose
                 it. What is required is that it is a real, settled number:
                 not in motion, and the terminal now in NET mode because a
                 tare has been taken. Tare_PV is what goes on the ticket. *)
              IF NOT IND780s[CardIdx].Motion
                 AND IND780s[CardIdx].NetMode THEN
                IND780s[CardIdx].Tare_PV        := IND780s[CardIdx].Readback_PV;
                IND780s[CardIdx].Tare_Confirmed := 1;
                IND780s[CardIdx].Seq_State      := 4;
              ELSIF IND780s[CardIdx].Seq_Timer > IND780s[CardIdx].Cfg_AckTimeout THEN
                IND780s[CardIdx].Seq_ErrCode := 1;
                IND780s[CardIdx].Seq_State   := 5;
              END_IF;

            END_IF;

        4:  (* CONFIRMED - return the selector to gross and go idle. *)
            IND780s[CardIdx].Req_SelTarget := 0;
            IND780s[CardIdx].Req_SelTare   := 0;
            IND780s[CardIdx].Req_SelNet    := 0;
            IND780s[CardIdx].Req_SelGross  := 1;
            IND780s[CardIdx].Seq_Timer     := 0;
            IND780s[CardIdx].Seq_State     := 0;

        5:  (* TIMEOUT - held. PRG_BayControl faults the bay on Seq_ErrCode.
               Cleared by the bay reset path calling Req_Clear. *)
            IND780s[CardIdx].Req_SelTarget := 0;
            IND780s[CardIdx].Req_SelTare   := 0;
            IND780s[CardIdx].Req_SelGross  := 1;
            IF IND780s[CardIdx].Req_Clear THEN
              IND780s[CardIdx].Seq_ErrCode := 0;
              IND780s[CardIdx].Seq_State   := 0;
            END_IF;

      END_CASE;


      (* ---------------------------------------------------------------------
         D. Batch running / completion detection.

         Req_StartTarget is a HELD LEVEL, not a pulse. PRG_BayControl sets it
         to run and clears it to stop. Clearing it is the controlled stop -
         there is no separate stop command at the terminal.
         --------------------------------------------------------------------- *)

      IF IND780s[CardIdx].Req_StartTarget THEN

        IND780s[CardIdx].Batch_Running := 1;

        (* Feed seen at least once. Without this latch the completion test
           below is satisfied at rest, before any product has moved. *)
        IF IND780s[CardIdx].Feed OR IND780s[CardIdx].FastFeed THEN
          IND780s[CardIdx].Fed_Once := 1;
        END_IF;

        (* Stability hold once feeding has stopped. *)
        IF IND780s[CardIdx].Fed_Once
           AND NOT IND780s[CardIdx].Feed
           AND NOT IND780s[CardIdx].FastFeed
           AND NOT IND780s[CardIdx].Motion THEN
          IND780s[CardIdx].Stable_Timer := IND780s[CardIdx].Stable_Timer + 1;
        ELSE
          IND780s[CardIdx].Stable_Timer := 0;
        END_IF;

        (* Derived completion. Latches - it is read by the bay state machine
           one scan later and must not be a single-scan pulse. *)
        IF IND780s[CardIdx].Stable_Timer >= (2 * CONST_SCANS_PER_SEC) THEN
          IND780s[CardIdx].Batch_Done  := 1;
          IND780s[CardIdx].Batch_InTol := IND780s[CardIdx].Tolerance_Ok;
          IF NOT IND780s[CardIdx].Tolerance_Ok THEN
            (* Feed stopped and settled outside the tolerance band. The load
               is over, but it is not a good load - the bay must not treat
               this as a clean completion. *)
            IND780s[CardIdx].Batch_Fault := 1;
            IND780s[CardIdx].Seq_ErrCode := 5;
          END_IF;
        END_IF;

      ELSE

        (* Start not held: the terminal target logic is aborted, by
           definition. Clear the running/derived state so the next batch
           starts from a known place. Batch_Fault is NOT cleared here - it is
           cleared by the bay reset path, so a fault survives the stop that
           it caused. *)
        IND780s[CardIdx].Batch_Running := 0;
        IND780s[CardIdx].Batch_Done    := 0;
        IND780s[CardIdx].Fed_Once      := 0;
        IND780s[CardIdx].Stable_Timer  := 0;

      END_IF;

      IND780s[CardIdx].Feed_Prev := IND780s[CardIdx].Feed;


      (* ---------------------------------------------------------------------
         E. Status rollup for the PanelView.
         --------------------------------------------------------------------- *)

      IF IND780s[CardIdx].Batch_Fault OR IND780s[CardIdx].Seq_ErrCode = 3 THEN
        IND780s[CardIdx].Status := 3;
      ELSIF IND780s[CardIdx].Seq_ErrCode <> 0 THEN
        IND780s[CardIdx].Status := 2;
      ELSIF IND780s[CardIdx].Motion OR IND780s[CardIdx].Quality <> 0 THEN
        IND780s[CardIdx].Status := 1;
      ELSE
        IND780s[CardIdx].Status := 0;
      END_IF;

    END_IF;

  END_IF;

END_FOR;
