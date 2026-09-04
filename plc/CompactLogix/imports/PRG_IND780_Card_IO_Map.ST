(* ============================================================================
   Card_IO_Map  -  PRG_IND780        Type: Structured Text
   KJV Solutions LLC  /  Continuum Terminal Manager
   ----------------------------------------------------------------------------
   PURPOSE
   Copies each IND780 EtherNet/IP module's tags into and out of IND780s[],
   so that every other routine can work on the cards by index.

   WHY THIS ROUTINE EXISTS AT ALL
   Studio 5000 module-defined tags (IND780_3:I.Slot1.Feed) cannot be indexed.
   There is no way to write IND780_[c]:I.Slot1.Feed. The only way to run one
   body of logic across six terminals is to unroll the copy here and index
   everywhere else. That is why this routine is repetitive and every other
   routine is not.

   MODULE NAMING - REQUIRED
   Modules must be named IND780_1 .. IND780_6, each added at revision 2.005
   with data format Integer/Divisions, one message slot, byte order Word Swap.
   The card number is the BAY it serves. On the existing project this means
   renaming IND780_Float (bay 3's terminal) to IND780_3.

   A card whose module has not been added yet is left disabled by
   Cfg_Enabled = 0; the block for it is present and inert.

   ORDERING: this routine must run FIRST in PRG_IND780, before Batch_Sequencer
   and Bay_Scale_Map, and PRG_IND780 must run before PRG_BayControl. It does.
   ============================================================================ *)


(* ---------------------------------------------------------------------------
   1. Connection health, per card.

   GSV EntryStatus is the only trustworthy answer to "is this terminal
   actually there". The status bits inside the input image cannot answer it:
   on a dropped Class 1 connection the input image stops updating, and a
   frozen DataOk = 1 reads exactly like a healthy terminal. That failure is
   what F-02 exists to prevent.

   EntryStatus bits 12-15 = 4#0100 (16#4000) means Running/connected.
   --------------------------------------------------------------------------- *)

GSV(MODULE, IND780_1, EntryStatus, CardEntryStatus[0]);
GSV(MODULE, IND780_2, EntryStatus, CardEntryStatus[1]);
GSV(MODULE, IND780_3, EntryStatus, CardEntryStatus[2]);
GSV(MODULE, IND780_4, EntryStatus, CardEntryStatus[3]);
GSV(MODULE, IND780_5, EntryStatus, CardEntryStatus[4]);
GSV(MODULE, IND780_6, EntryStatus, CardEntryStatus[5]);

FOR CardIdx := 0 TO 5 DO
    IND780s[CardIdx].CardID  := CardIdx + 1;
    IND780s[CardIdx].Comm_OK := ((CardEntryStatus[CardIdx] AND 16#F000) = 16#4000);
END_FOR;


(* ---------------------------------------------------------------------------
   2. INPUTS - module -> array.

   Six identical blocks. Change one, change all six.
   --------------------------------------------------------------------------- *)

(* ---- Card 1 ---- *)
IND780s[0].DataOk             := IND780_1:I.Slot1.DataOk;
IND780s[0].UpdateInProgress   := IND780_1:I.Slot1.UpdateInProgress;
IND780s[0].Motion             := IND780_1:I.Slot1.Motion;
IND780s[0].NetMode            := IND780_1:I.Slot1.NetMode;
IND780s[0].Feed               := IND780_1:I.Slot1.Feed;
IND780s[0].FastFeed           := IND780_1:I.Slot1.FastFeed;
IND780s[0].Tolerance_Ok       := IND780_1:I.Slot1.Tolerance_Ok;
IND780s[0].UnderLowTolerance  := IND780_1:I.Slot1.UnderLowTolerance;
IND780s[0].OverHighTolerance  := IND780_1:I.Slot1.OverHighTolerance;
IND780s[0].Comparator1        := IND780_1:I.Slot1.Comparator1;
IND780s[0].Comparator2        := IND780_1:I.Slot1.Comparator2;
IND780s[0].Comparator3        := IND780_1:I.Slot1.Comparator3;
IND780s[0].EnterKey           := IND780_1:I.Slot1.EnterKey;
IND780s[0].Input1             := IND780_1:I.Slot1.Slot5_InputBit1;
IND780s[0].Input2             := IND780_1:I.Slot1.Slot5_InputBit2;
IND780s[0].Input3             := IND780_1:I.Slot1.Slot5_InputBit3;
IND780s[0].Status_Raw         := IND780_1:I.Slot1.Status;
IND780s[0].Weight_Raw         := IND780_1:I.Slot1.Weight;

(* ---- Card 2 ---- *)
IND780s[1].DataOk             := IND780_2:I.Slot1.DataOk;
IND780s[1].UpdateInProgress   := IND780_2:I.Slot1.UpdateInProgress;
IND780s[1].Motion             := IND780_2:I.Slot1.Motion;
IND780s[1].NetMode            := IND780_2:I.Slot1.NetMode;
IND780s[1].Feed               := IND780_2:I.Slot1.Feed;
IND780s[1].FastFeed           := IND780_2:I.Slot1.FastFeed;
IND780s[1].Tolerance_Ok       := IND780_2:I.Slot1.Tolerance_Ok;
IND780s[1].UnderLowTolerance  := IND780_2:I.Slot1.UnderLowTolerance;
IND780s[1].OverHighTolerance  := IND780_2:I.Slot1.OverHighTolerance;
IND780s[1].Comparator1        := IND780_2:I.Slot1.Comparator1;
IND780s[1].Comparator2        := IND780_2:I.Slot1.Comparator2;
IND780s[1].Comparator3        := IND780_2:I.Slot1.Comparator3;
IND780s[1].EnterKey           := IND780_2:I.Slot1.EnterKey;
IND780s[1].Input1             := IND780_2:I.Slot1.Slot5_InputBit1;
IND780s[1].Input2             := IND780_2:I.Slot1.Slot5_InputBit2;
IND780s[1].Input3             := IND780_2:I.Slot1.Slot5_InputBit3;
IND780s[1].Status_Raw         := IND780_2:I.Slot1.Status;
IND780s[1].Weight_Raw         := IND780_2:I.Slot1.Weight;

(* ---- Card 3 ---- *)
IND780s[2].DataOk             := IND780_3:I.Slot1.DataOk;
IND780s[2].UpdateInProgress   := IND780_3:I.Slot1.UpdateInProgress;
IND780s[2].Motion             := IND780_3:I.Slot1.Motion;
IND780s[2].NetMode            := IND780_3:I.Slot1.NetMode;
IND780s[2].Feed               := IND780_3:I.Slot1.Feed;
IND780s[2].FastFeed           := IND780_3:I.Slot1.FastFeed;
IND780s[2].Tolerance_Ok       := IND780_3:I.Slot1.Tolerance_Ok;
IND780s[2].UnderLowTolerance  := IND780_3:I.Slot1.UnderLowTolerance;
IND780s[2].OverHighTolerance  := IND780_3:I.Slot1.OverHighTolerance;
IND780s[2].Comparator1        := IND780_3:I.Slot1.Comparator1;
IND780s[2].Comparator2        := IND780_3:I.Slot1.Comparator2;
IND780s[2].Comparator3        := IND780_3:I.Slot1.Comparator3;
IND780s[2].EnterKey           := IND780_3:I.Slot1.EnterKey;
IND780s[2].Input1             := IND780_3:I.Slot1.Slot5_InputBit1;
IND780s[2].Input2             := IND780_3:I.Slot1.Slot5_InputBit2;
IND780s[2].Input3             := IND780_3:I.Slot1.Slot5_InputBit3;
IND780s[2].Status_Raw         := IND780_3:I.Slot1.Status;
IND780s[2].Weight_Raw         := IND780_3:I.Slot1.Weight;

(* ---- Card 4 ---- *)
IND780s[3].DataOk             := IND780_4:I.Slot1.DataOk;
IND780s[3].UpdateInProgress   := IND780_4:I.Slot1.UpdateInProgress;
IND780s[3].Motion             := IND780_4:I.Slot1.Motion;
IND780s[3].NetMode            := IND780_4:I.Slot1.NetMode;
IND780s[3].Feed               := IND780_4:I.Slot1.Feed;
IND780s[3].FastFeed           := IND780_4:I.Slot1.FastFeed;
IND780s[3].Tolerance_Ok       := IND780_4:I.Slot1.Tolerance_Ok;
IND780s[3].UnderLowTolerance  := IND780_4:I.Slot1.UnderLowTolerance;
IND780s[3].OverHighTolerance  := IND780_4:I.Slot1.OverHighTolerance;
IND780s[3].Comparator1        := IND780_4:I.Slot1.Comparator1;
IND780s[3].Comparator2        := IND780_4:I.Slot1.Comparator2;
IND780s[3].Comparator3        := IND780_4:I.Slot1.Comparator3;
IND780s[3].EnterKey           := IND780_4:I.Slot1.EnterKey;
IND780s[3].Input1             := IND780_4:I.Slot1.Slot5_InputBit1;
IND780s[3].Input2             := IND780_4:I.Slot1.Slot5_InputBit2;
IND780s[3].Input3             := IND780_4:I.Slot1.Slot5_InputBit3;
IND780s[3].Status_Raw         := IND780_4:I.Slot1.Status;
IND780s[3].Weight_Raw         := IND780_4:I.Slot1.Weight;

(* ---- Card 5 ---- *)
IND780s[4].DataOk             := IND780_5:I.Slot1.DataOk;
IND780s[4].UpdateInProgress   := IND780_5:I.Slot1.UpdateInProgress;
IND780s[4].Motion             := IND780_5:I.Slot1.Motion;
IND780s[4].NetMode            := IND780_5:I.Slot1.NetMode;
IND780s[4].Feed               := IND780_5:I.Slot1.Feed;
IND780s[4].FastFeed           := IND780_5:I.Slot1.FastFeed;
IND780s[4].Tolerance_Ok       := IND780_5:I.Slot1.Tolerance_Ok;
IND780s[4].UnderLowTolerance  := IND780_5:I.Slot1.UnderLowTolerance;
IND780s[4].OverHighTolerance  := IND780_5:I.Slot1.OverHighTolerance;
IND780s[4].Comparator1        := IND780_5:I.Slot1.Comparator1;
IND780s[4].Comparator2        := IND780_5:I.Slot1.Comparator2;
IND780s[4].Comparator3        := IND780_5:I.Slot1.Comparator3;
IND780s[4].EnterKey           := IND780_5:I.Slot1.EnterKey;
IND780s[4].Input1             := IND780_5:I.Slot1.Slot5_InputBit1;
IND780s[4].Input2             := IND780_5:I.Slot1.Slot5_InputBit2;
IND780s[4].Input3             := IND780_5:I.Slot1.Slot5_InputBit3;
IND780s[4].Status_Raw         := IND780_5:I.Slot1.Status;
IND780s[4].Weight_Raw         := IND780_5:I.Slot1.Weight;

(* ---- Card 6 ---- *)
IND780s[5].DataOk             := IND780_6:I.Slot1.DataOk;
IND780s[5].UpdateInProgress   := IND780_6:I.Slot1.UpdateInProgress;
IND780s[5].Motion             := IND780_6:I.Slot1.Motion;
IND780s[5].NetMode            := IND780_6:I.Slot1.NetMode;
IND780s[5].Feed               := IND780_6:I.Slot1.Feed;
IND780s[5].FastFeed           := IND780_6:I.Slot1.FastFeed;
IND780s[5].Tolerance_Ok       := IND780_6:I.Slot1.Tolerance_Ok;
IND780s[5].UnderLowTolerance  := IND780_6:I.Slot1.UnderLowTolerance;
IND780s[5].OverHighTolerance  := IND780_6:I.Slot1.OverHighTolerance;
IND780s[5].Comparator1        := IND780_6:I.Slot1.Comparator1;
IND780s[5].Comparator2        := IND780_6:I.Slot1.Comparator2;
IND780s[5].Comparator3        := IND780_6:I.Slot1.Comparator3;
IND780s[5].EnterKey           := IND780_6:I.Slot1.EnterKey;
IND780s[5].Input1             := IND780_6:I.Slot1.Slot5_InputBit1;
IND780s[5].Input2             := IND780_6:I.Slot1.Slot5_InputBit2;
IND780s[5].Input3             := IND780_6:I.Slot1.Slot5_InputBit3;
IND780s[5].Status_Raw         := IND780_6:I.Slot1.Status;
IND780s[5].Weight_Raw         := IND780_6:I.Slot1.Weight;


(* ---------------------------------------------------------------------------
   3. Scale the raw weight, per card.

   Weight_Raw is divisions (or display units) - a 16-bit signed integer,
   +/-32767. Cfg_Increment converts it to lbs and is NOT read from the
   terminal; it must match the terminal calibration or every ticket is wrong
   by a constant factor. Commissioning verifies it against a known test
   weight before the bay is released.

   Weight_PV is written ONLY when the reading is coherent. On a bad scan it
   holds its last value and Quality marks it, rather than being zeroed -
   zeroing reads as an empty truck (F-04).
   --------------------------------------------------------------------------- *)

FOR CardIdx := 0 TO 5 DO

    IF IND780s[CardIdx].Cfg_Enabled
       AND IND780s[CardIdx].Comm_OK
       AND IND780s[CardIdx].DataOk
       AND NOT IND780s[CardIdx].UpdateInProgress THEN

        IND780s[CardIdx].Weight_PV  := IND780s[CardIdx].Weight_Raw
                                       * IND780s[CardIdx].Cfg_Increment;
        IND780s[CardIdx].Quality    := 0;
        IND780s[CardIdx].LastUpdate := WallClockSeconds;

    ELSIF IND780s[CardIdx].Cfg_Enabled THEN

        (* Reading not usable this scan. Weight_PV deliberately not written. *)
        IND780s[CardIdx].Quality := 2;

    ELSE

        (* Card out of service by configuration. Not a fault. *)
        IND780s[CardIdx].Quality := 1;

    END_IF;

END_FOR;


(* ---------------------------------------------------------------------------
   4. OUTPUTS - array -> module.

   The named BOOL members are driven, NOT the raw Command INT. Driving both
   puts two writers on the same word: the BOOLs and the INT would fight and
   the losing one changes scan to scan. Nothing in this project writes
   IND780_n:O.Slot1.Command.

   Select1/2/3 are bits 0-2 of the command word read as a 3-bit binary
   readback selector:  0=gross  1=net  2=displayed  3=tare  4=target.
   --------------------------------------------------------------------------- *)

FOR CardIdx := 0 TO 5 DO
    (* Decode the requested readback into the three select bits once, so the
       six output blocks below stay identical. *)
    SelBit1[CardIdx] := IND780s[CardIdx].Req_SelNet OR IND780s[CardIdx].Req_SelTare;
    SelBit2[CardIdx] := IND780s[CardIdx].Req_SelTare;
    SelBit3[CardIdx] := IND780s[CardIdx].Req_SelTarget;
END_FOR;

(* ---- Card 1 ---- *)
IND780_1:O.Slot1.Tare              := IND780s[0].Req_Tare;
IND780_1:O.Slot1.Clear             := IND780s[0].Req_Clear;
IND780_1:O.Slot1.Zero              := IND780s[0].Req_Zero;
IND780_1:O.Slot1.Print             := IND780s[0].Req_Print;
IND780_1:O.Slot1.LoadTare          := IND780s[0].Req_LoadTare;
IND780_1:O.Slot1.LoadTarget        := IND780s[0].Req_LoadTarget;
IND780_1:O.Slot1.AbortStartTarget  := IND780s[0].Req_StartTarget;
IND780_1:O.Slot1.Select1           := SelBit1[0];
IND780_1:O.Slot1.Select2           := SelBit2[0];
IND780_1:O.Slot1.Select3           := SelBit3[0];
IND780_1:O.Slot1.Weight            := IND780s[0].Weight_Out;

(* ---- Card 2 ---- *)
IND780_2:O.Slot1.Tare              := IND780s[1].Req_Tare;
IND780_2:O.Slot1.Clear             := IND780s[1].Req_Clear;
IND780_2:O.Slot1.Zero              := IND780s[1].Req_Zero;
IND780_2:O.Slot1.Print             := IND780s[1].Req_Print;
IND780_2:O.Slot1.LoadTare          := IND780s[1].Req_LoadTare;
IND780_2:O.Slot1.LoadTarget        := IND780s[1].Req_LoadTarget;
IND780_2:O.Slot1.AbortStartTarget  := IND780s[1].Req_StartTarget;
IND780_2:O.Slot1.Select1           := SelBit1[1];
IND780_2:O.Slot1.Select2           := SelBit2[1];
IND780_2:O.Slot1.Select3           := SelBit3[1];
IND780_2:O.Slot1.Weight            := IND780s[1].Weight_Out;

(* ---- Card 3 ---- *)
IND780_3:O.Slot1.Tare              := IND780s[2].Req_Tare;
IND780_3:O.Slot1.Clear             := IND780s[2].Req_Clear;
IND780_3:O.Slot1.Zero              := IND780s[2].Req_Zero;
IND780_3:O.Slot1.Print             := IND780s[2].Req_Print;
IND780_3:O.Slot1.LoadTare          := IND780s[2].Req_LoadTare;
IND780_3:O.Slot1.LoadTarget        := IND780s[2].Req_LoadTarget;
IND780_3:O.Slot1.AbortStartTarget  := IND780s[2].Req_StartTarget;
IND780_3:O.Slot1.Select1           := SelBit1[2];
IND780_3:O.Slot1.Select2           := SelBit2[2];
IND780_3:O.Slot1.Select3           := SelBit3[2];
IND780_3:O.Slot1.Weight            := IND780s[2].Weight_Out;

(* ---- Card 4 ---- *)
IND780_4:O.Slot1.Tare              := IND780s[3].Req_Tare;
IND780_4:O.Slot1.Clear             := IND780s[3].Req_Clear;
IND780_4:O.Slot1.Zero              := IND780s[3].Req_Zero;
IND780_4:O.Slot1.Print             := IND780s[3].Req_Print;
IND780_4:O.Slot1.LoadTare          := IND780s[3].Req_LoadTare;
IND780_4:O.Slot1.LoadTarget        := IND780s[3].Req_LoadTarget;
IND780_4:O.Slot1.AbortStartTarget  := IND780s[3].Req_StartTarget;
IND780_4:O.Slot1.Select1           := SelBit1[3];
IND780_4:O.Slot1.Select2           := SelBit2[3];
IND780_4:O.Slot1.Select3           := SelBit3[3];
IND780_4:O.Slot1.Weight            := IND780s[3].Weight_Out;

(* ---- Card 5 ---- *)
IND780_5:O.Slot1.Tare              := IND780s[4].Req_Tare;
IND780_5:O.Slot1.Clear             := IND780s[4].Req_Clear;
IND780_5:O.Slot1.Zero              := IND780s[4].Req_Zero;
IND780_5:O.Slot1.Print             := IND780s[4].Req_Print;
IND780_5:O.Slot1.LoadTare          := IND780s[4].Req_LoadTare;
IND780_5:O.Slot1.LoadTarget        := IND780s[4].Req_LoadTarget;
IND780_5:O.Slot1.AbortStartTarget  := IND780s[4].Req_StartTarget;
IND780_5:O.Slot1.Select1           := SelBit1[4];
IND780_5:O.Slot1.Select2           := SelBit2[4];
IND780_5:O.Slot1.Select3           := SelBit3[4];
IND780_5:O.Slot1.Weight            := IND780s[4].Weight_Out;

(* ---- Card 6 ---- *)
IND780_6:O.Slot1.Tare              := IND780s[5].Req_Tare;
IND780_6:O.Slot1.Clear             := IND780s[5].Req_Clear;
IND780_6:O.Slot1.Zero              := IND780s[5].Req_Zero;
IND780_6:O.Slot1.Print             := IND780s[5].Req_Print;
IND780_6:O.Slot1.LoadTare          := IND780s[5].Req_LoadTare;
IND780_6:O.Slot1.LoadTarget        := IND780s[5].Req_LoadTarget;
IND780_6:O.Slot1.AbortStartTarget  := IND780s[5].Req_StartTarget;
IND780_6:O.Slot1.Select1           := SelBit1[5];
IND780_6:O.Slot1.Select2           := SelBit2[5];
IND780_6:O.Slot1.Select3           := SelBit3[5];
IND780_6:O.Slot1.Weight            := IND780s[5].Weight_Out;
