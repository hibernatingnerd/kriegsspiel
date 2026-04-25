// mock-audit.ts
// Pre-built audit log entries for the Grey Horizon demo scenario.
// Each turn covers a 6-hour battle window; entries show what the sim generated.
// In production this data streams from the adjudicator backend.

export type AuditCategory =
  | 'INTEL'
  | 'MOVEMENT'
  | 'FIRES'
  | 'CYBER'
  | 'EW'
  | 'C2'
  | 'ASSESSMENT'
  | 'SYSTEM'

export interface AuditEntry {
  time: string        // "T+HH:MM" absolute from scenario start
  category: AuditCategory
  text: string
}

export const GREY_HORIZON_AUDIT: Record<number, AuditEntry[]> = {
  // Turn 1 — T+00:00 to T+05:59 — opening cyber phase, ISR detection
  1: [
    { time: 'T+00:08', category: 'CYBER',      text: 'APT28 DDoS initiated against Latvian government portals; Ādaži C2 node degraded 30%' },
    { time: 'T+00:17', category: 'INTEL',      text: 'MQ-9B pattern-of-life: armor column 40+ vehicles, Pskov → A6 axis, ETA border ~6h' },
    { time: 'T+00:44', category: 'EW',         text: 'Krasukha-4 begins jamming 243.0–244.5 MHz; blue comms shifted to SATCOM fallback' },
    { time: 'T+02:12', category: 'MOVEMENT',   text: 'Red recon element (BRM-3K ×4) observed at border crossing point, halted — recce pause' },
    { time: 'T+03:55', category: 'C2',         text: 'eFP BG HQ acknowledges INTEL; LATSOF screen platoons ordered to observation posts' },
    { time: 'T+05:22', category: 'ASSESSMENT', text: 'SITREP T+05h — red main effort assessed A6 axis; cyber phase ongoing; border not yet crossed' },
  ],

  // Turn 2 — T+06:00 to T+11:59 — border crossing, first contact
  2: [
    { time: 'T+06:15', category: 'MOVEMENT',   text: 'Red lead BTR Bn crosses Latvian border at Zilupe crossing point; penetration 3.1km' },
    { time: 'T+07:30', category: 'INTEL',      text: 'MQ-9B confirms T-90M2 Bn departing Pskov staging; estimated 4h to border at current rate' },
    { time: 'T+08:05', category: 'FIRES',      text: 'Blue PzH 2000 battery (×6) moves to firing position, sector Rēzekne-southwest; SA complete' },
    { time: 'T+09:44', category: 'CYBER',      text: 'Second DDoS wave targets power grid SCADA; partial success — Rēzekne substation offline 2h' },
    { time: 'T+10:22', category: 'MOVEMENT',   text: 'Red motor rifle coy probing road junction 3.5km inside border; blue screen plt in contact' },
    { time: 'T+11:41', category: 'ASSESSMENT', text: 'SITREP T+11h — penetration 5.2km; red axis confirmed A6; tank Bn ~2h behind infantry lead' },
  ],

  // Turn 3 — T+12:00 to T+17:59 — A6 axis confirmed, flanking attempt
  3: [
    { time: 'T+12:18', category: 'FIRES',      text: 'Blue PzH 2000 fires 40-round area suppression on Zilupe crossing; BDA: 2× BTR mobility kill' },
    { time: 'T+13:05', category: 'EW',         text: 'Orlan-30 UAV detected over Krāslava at 800m AGL; blue SHORAD engaged; UAV withdrew northeast' },
    { time: 'T+14:33', category: 'MOVEMENT',   text: 'Red tank Bn (T-90M2 ×28) crosses border; second axis probed via forest track north of A6' },
    { time: 'T+15:44', category: 'C2',         text: 'LATSOF recce confirms tank Bn on forest track — terrain channeling likely; flanking in progress' },
    { time: 'T+16:20', category: 'INTEL',      text: 'MQ-9B: red arty (2S19 ×6) deploying to firing position 8km inside border; counter-battery threat' },
    { time: 'T+17:55', category: 'ASSESSMENT', text: 'SITREP T+17h — penetration 8.1km; forest flanking attempt identified; red arty now active' },
  ],

  // Turn 4 — T+18:00 to T+23:59 — canalization, blue fires effective
  4: [
    { time: 'T+18:22', category: 'FIRES',      text: 'Blue mass fires at Krāslava canalization point; 3× fire missions; red BTR Bn 18% attrition in 40 min' },
    { time: 'T+19:15', category: 'FIRES',      text: 'Red 2S19 Bty opens counter-battery; 2× blue PzH 2000 positions suppressed — battery mobile' },
    { time: 'T+20:40', category: 'MOVEMENT',   text: 'Red tank Bn forest track blocked — boreal terrain denial; column rerouted back to A6 main axis' },
    { time: 'T+21:55', category: 'EW',         text: 'Red Krasukha-4 shifts jamming to blue fires coordination nets; degraded 15 min; manual backup' },
    { time: 'T+22:30', category: 'INTEL',      text: 'MQ-9B: red logistics convoy halted at Zilupe staging; sustainment stretch becoming visible' },
    { time: 'T+23:47', category: 'ASSESSMENT', text: 'SITREP T+23h — penetration 11.4km; red advance slowing; blue fires effective; CP BLUE 86% RED 68%' },
  ],

  // Turn 5 — T+24:00 to T+29:59 — Krāslava bridge threat, VDV notice
  5: [
    { time: 'T+24:15', category: 'CYBER',      text: 'GRU APT28 disrupts LATSOF comms net 2h; recce platoon on enforced radio silence — comms loss' },
    { time: 'T+25:33', category: 'MOVEMENT',   text: 'Red motor rifle coy separates from column toward Krāslava bridge — potential seizure attempt' },
    { time: 'T+26:44', category: 'C2',         text: 'eFP BG HQ: Article 4 consultations confirmed; NAC convened Brussels; reinforcement TBD' },
    { time: 'T+27:10', category: 'MOVEMENT',   text: 'UK Mech Inf coy establishes blocking position Krāslava bridge east approach; bridge intact' },
    { time: 'T+28:30', category: 'INTEL',      text: 'MQ-9B: 76th VDV Div loading at Pskov rail yard; BTG ×2; deployment timeline unknown — 12h notice' },
    { time: 'T+29:55', category: 'ASSESSMENT', text: 'SITREP T+29h — penetration 14.2km; Krāslava bridge defended; LATSOF comms recovering; VDV threat emerging' },
  ],

  // Turn 6 — T+30:00 to T+35:59 — blue CP declining, AD supply critical
  6: [
    { time: 'T+30:12', category: 'INTEL',      text: 'LATSOF (comms restored): red tank Bn regrouping at Dagda; next push likely A6 axis south of town' },
    { time: 'T+31:28', category: 'MOVEMENT',   text: 'Red motor rifle Bn presses A6 past Dagda; overcoming local delay; penetration increasing' },
    { time: 'T+32:15', category: 'FIRES',      text: 'NASAMS Bty tracks Ka-52 ×2 at 45km; weapons free; 1 Ka-52 downed, 1 breaks off — blue AD effective' },
    { time: 'T+33:44', category: 'C2',         text: 'Blue NASAMS Bty: 3 salvos remaining; resupply 8h out from Lielvārde depot — AD supply critical' },
    { time: 'T+34:20', category: 'EW',         text: 'Red EW intensifies on blue fires coordination nets; 20-min degradation; manual backup activated' },
    { time: 'T+35:52', category: 'ASSESSMENT', text: 'SITREP T+35h — penetration 16.8km; Daugavpils 8.2km ahead; blue AD supply critical; CP BLUE 74% RED 56%' },
  ],

  // Turn 7 — T+36:00 to T+41:59 — Dvina line, Article 5
  7: [
    { time: 'T+36:18', category: 'MOVEMENT',   text: 'Blue local withdrawal 2km to Dvina river line complete; new defensive positions established' },
    { time: 'T+37:40', category: 'INTEL',      text: '76th VDV Div: BTG ×2 fully loaded at Pskov; now on 4h notice to depart — escalation risk elevated' },
    { time: 'T+38:55', category: 'FIRES',      text: 'Blue PzH 2000 fire mission road junction south of Krāslava; BDA: 4× vehicles destroyed, 1× gun silenced' },
    { time: 'T+39:22', category: 'MOVEMENT',   text: 'Red exploitation halted at Dvina — river obstacle + blue AD posture; red pauses to consolidate' },
    { time: 'T+40:15', category: 'C2',         text: 'NATO HQ SHAPE: Article 5 consultations initiated; multinational reinforcement timeline TBD ≥48h' },
    { time: 'T+41:50', category: 'ASSESSMENT', text: 'SITREP T+41h — penetration 20.1km; Dvina line holding; VDV 4h notice; CP BLUE 70% RED 46%' },
  ],

  // Turn 8 — T+42:00 to T+47:59 — red operational pause
  8: [
    { time: 'T+42:05', category: 'INTEL',      text: 'Red log convoy halted 15km behind FLOT; fuel shortage confirmed via HUMINT; ~6h to resupply' },
    { time: 'T+43:30', category: 'MOVEMENT',   text: 'Red forward elements static on A6; defensive posturing observed; no new axis probed' },
    { time: 'T+44:15', category: 'FIRES',      text: 'Blue counter-battery mission: 2S19 firing position acquired by LATSOF; 2× guns destroyed' },
    { time: 'T+45:00', category: 'C2',         text: 'UK Mech Inf Bn reports 60% ammo state; resupply convoy departed Ādaži ETA 4h; holding in place' },
    { time: 'T+46:44', category: 'EW',         text: 'Red EW activity reduced 60% vs turn 1; assessed fuel rationing affecting all Red electronic systems' },
    { time: 'T+47:58', category: 'ASSESSMENT', text: 'SITREP T+47h — penetration static 22.4km; red operational pause likely; CP BLUE 67% RED 40%' },
  ],

  // Turn 9 — T+48:00 to T+53:59 — holding, NATO reinforcement window
  9: [
    { time: 'T+48:12', category: 'C2',         text: 'SHAPE confirms multinational reinforcement package arriving T+96h; blue ordered hold in place' },
    { time: 'T+49:25', category: 'INTEL',      text: '76th VDV: logistics constraint confirmed; commitment before T+72h assessed unlikely — VDV threat receding' },
    { time: 'T+50:44', category: 'MOVEMENT',   text: 'Red minor probing at Dvina south flank; repelled by blue screening element; no penetration gain' },
    { time: 'T+51:30', category: 'FIRES',      text: 'Blue conservation order in effect: fires authorized only on confirmed main-effort targets' },
    { time: 'T+52:15', category: 'EW',         text: 'NATO CCDCOE Tallinn team deploys patch to Krasukha-4 jamming gap; blue comms restored to 85%' },
    { time: 'T+53:50', category: 'ASSESSMENT', text: 'SITREP T+53h — penetration static 22.4km; red stalled; VDV uncommitted; CP BLUE 64% RED 36%' },
  ],

  // Turn 10 — T+54:00 to T+59:59 — final turn, scenario close-out
  10: [
    { time: 'T+54:22', category: 'INTEL',      text: '76th VDV: logistics constraint binding; no commitment this scenario window — reserve no longer a factor' },
    { time: 'T+55:15', category: 'C2',         text: 'NAC formally triggers Article 5; multinational reinforcement columns moving — ETA 48h' },
    { time: 'T+56:33', category: 'MOVEMENT',   text: 'Red flag of truce signal observed from Dagda — unverified; blue holds position; no acknowledgement' },
    { time: 'T+57:44', category: 'FIRES',      text: 'Final fire mission: blue PzH 2000 suppresses red arty at Zilupe; 2× guns silenced; battery Winchester' },
    { time: 'T+58:50', category: 'ASSESSMENT', text: 'SITREP T+58h — Daugavpils held; penetration 22.4km; CP BLUE 62% RED 32%; ENDEX approaching' },
    { time: 'T+59:55', category: 'SYSTEM',     text: 'Scenario engine: turn 10 complete — generating after-action review…' },
  ],
}
