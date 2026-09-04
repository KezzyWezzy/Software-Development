(* ============================================================================
   Bay_Scale_Map  -  PRG_IND780        Type: Structured Text        REVISED
   KJV Solutions LLC  /  Continuum Terminal Manager
   ----------------------------------------------------------------------------
   Carries terminal weight into the Bays[] scale members that PRG_BayControl
   consumes, for all six cards, and reports which terminal serves each bay.

   SITE CONFIGURATION
     Cfg_BayScaleSrc[b]   0 = no terminal on this bay (simulator / manual)
                          1-6 = IND780s[] card index + 1 serving this bay
     Cfg_BayScaleMode[b]  0 = PLC reads weight and runs its own cutoff
                          1 = terminal runs the cutoff; PLC commands it
                              (mirrored into IND780s[c].Cfg_Mode below)

   WHAT CHANGED FROM THE PREVIOUS REVISION - READ THIS
   The old routine computed:

       FP_Ok := DataOk AND ((DataOk AND DataOk) OR (NOT DataOk AND NOT DataOk));

   The parenthesised term is a tautology: it is TRUE for every value of
   DataOk. FP_Ok therefore reduced to plain DataOk and the data-integrity
   gate the comment describes was not being applied. The same substitution
   appears in the Floating_Point ladder routine, where XIC(DataIntegrity)
   XIC(DataIntegrity2) had become XIC(DataOk) XIC(DataOk).

   Cause: the example code was written for a Floating Point module. The
   module in this project is Integer/Divisions (data type
   ME:IND780Enet_INTDIV_1Slots), which has no DataIntegrity, DataIntegrity2,
   CmndAck1 or CmndAck2 members. On import those references resolved to the
   nearest surviving member name and the checks silently collapsed.

   Integer/Divisions has one integrity mechanism: UpdateInProgress. It is
   used here, on every card, and there is no second bit to agree with it.
   ============================================================================ *)


FOR ScaleIdx := 0 TO 5 DO

    (* Push the per-bay mode down to the card that serves it, so the
       sequencer has it and the PanelView can show it against the card. *)
    IF Cfg_BayScaleSrc[ScaleIdx] >= 1 AND Cfg_BayScaleSrc[ScaleIdx] <= 6 THEN
        SrcCard := Cfg_BayScaleSrc[ScaleIdx] - 1;
        IND780s[SrcCard].Cfg_Mode := Cfg_BayScaleMode[ScaleIdx];
    ELSE
        SrcCard := -1;
    END_IF;


    IF SrcCard >= 0 THEN

        (* -------- source health, one rule for all six cards --------
           F-02: a lost terminal is never presented as a live reading.
           Comm_OK comes from GSV EntryStatus in Card_IO_Map and is the only
           bit that distinguishes "terminal absent" from "terminal reading a
           stable zero". *)

        SrcOk     := IND780s[SrcCard].Cfg_Enabled
                     AND IND780s[SrcCard].Comm_OK
                     AND IND780s[SrcCard].DataOk
                     AND NOT IND780s[SrcCard].UpdateInProgress
                     AND IND780s[SrcCard].Quality = 0;

        SrcWt     := IND780s[SrcCard].Weight_PV;
        SrcMotion := IND780s[SrcCard].Motion;
        SrcNet    := IND780s[SrcCard].NetMode;


        IF SrcOk THEN

            (* NET mode handling depends on who owns the tare.

               Cfg_Mode 0 - the PLC computes net from gross and its own
               locked tare, so the value on the wire must BE gross. A
               terminal in NET mode is a fault, exactly as before.

               Cfg_Mode 1 - the terminal took the tare and is displaying
               net by design. That is the expected state after Req_Tare, not
               a fault. Scale_Gross is reconstructed from the terminal's own
               net plus the terminal's own tare so that downstream logic and
               the DOT gross interlock still see a real gross number. *)

            IF Cfg_BayScaleMode[ScaleIdx] = 0 THEN

                IF SrcNet THEN
                    Bays[ScaleIdx].Scale_Fault    := 1;
                    Bays[ScaleIdx].Alm_ScaleFault := 1;
                    Bays[ScaleIdx].Scale_Stable   := 0;
                ELSE
                    Bays[ScaleIdx].Scale_Gross    := SrcWt;
                    Bays[ScaleIdx].Scale_Fault    := 0;
                    Bays[ScaleIdx].Alm_ScaleFault := 0;
                    Bays[ScaleIdx].Scale_Stable   := NOT SrcMotion;
                END_IF;

            ELSE

                IF SrcNet AND IND780s[SrcCard].Tare_Confirmed THEN
                    Bays[ScaleIdx].Scale_Net     := SrcWt;
                    Bays[ScaleIdx].Tare_Value    := IND780s[SrcCard].Tare_PV;
                    Bays[ScaleIdx].Scale_Gross   := SrcWt
                                                    + IND780s[SrcCard].Tare_PV;
                    Bays[ScaleIdx].Tare_Locked   := 1;
                ELSE
                    (* Before the tare, or after a clear: the terminal is in
                       gross and there is no tare yet. *)
                    Bays[ScaleIdx].Scale_Gross   := SrcWt;
                    Bays[ScaleIdx].Scale_Net     := 0.0;
                END_IF;

                Bays[ScaleIdx].Scale_Fault    := 0;
                Bays[ScaleIdx].Alm_ScaleFault := 0;
                Bays[ScaleIdx].Scale_Stable   := NOT SrcMotion;

            END_IF;

            Bays[ScaleIdx].Scale_Motion := SrcMotion;

        ELSE

            (* -------- terminal lost or data invalid --------
               Scale_Gross deliberately NOT written: it holds its last value
               and Scale_Fault marks it stale. Zeroing here reads as an empty
               truck (F-04). *)

            Bays[ScaleIdx].Scale_Fault    := 1;
            Bays[ScaleIdx].Alm_ScaleFault := 1;
            Bays[ScaleIdx].Scale_Stable   := 0;
            Bays[ScaleIdx].Scale_Motion   := 0;

        END_IF;


        (* A sequencer error is a scale fault as far as the bay is concerned:
           the PLC and the terminal disagree about what the terminal holds,
           and nothing downstream may load against that. *)
        IF Cfg_BayScaleMode[ScaleIdx] = 1
           AND IND780s[SrcCard].Seq_ErrCode <> 0 THEN
            Bays[ScaleIdx].Scale_Fault    := 1;
            Bays[ScaleIdx].Alm_ScaleFault := 1;
        END_IF;

    END_IF;

END_FOR;
