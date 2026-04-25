// mock-data.ts
// Swap this file (and/or point to a real API) to replace mock content.
// Schema shapes in src/lib/schema.ts mirror the Python backend dataclasses.

import type {
  Scenario,
  GameState,
  PendingDecision,
  DecisionOption,
  AAR,
} from './schema'

// ── Decision option library ────────────────────────────────────────────────

export const NEAR_PEER_OPTIONS: DecisionOption[] = [
  {
    key: 'hold',
    label: 'HOLD FORWARD',
    sub_label: 'Maintain current positions',
    consequence_hint: 'Preserves terrain, accepts attrition',
  },
  {
    key: 'reorient_fires',
    label: 'REORIENT FIRES',
    sub_label: 'Mass tube fires at canalization point',
    consequence_hint: 'Disrupts red tempo if axis is confirmed',
  },
  {
    key: 'commit_reserve',
    label: 'COMMIT RESERVE',
    sub_label: 'Release LATSOF recce plt from screening',
    consequence_hint: 'Gains intelligence, exposes reserve',
  },
  {
    key: 'withdraw',
    label: 'WITHDRAW LOCALLY',
    sub_label: 'Accept 2 km withdrawal to river line',
    consequence_hint: 'Preserves combat power, cedes terrain',
  },
]

export const GREY_HORIZON_DECISIONS: Record<number, PendingDecision> = {
  1: {
    turn: 1,
    context:
      'Opening phase. Red cyber unit begins DDoS against Latvian C2 networks. ISR detects armor movement from Pskov staging area toward A6 axis. Blue force is at full combat power. Choose opening posture.',
    options: NEAR_PEER_OPTIONS,
  },
  2: {
    turn: 2,
    context:
      'Red EW (Krasukha-4) begins jamming blue comms. MQ-9B has pattern-of-life on border crossing. Red motor rifle lead elements have crossed into Latgale. Blue arty is pre-positioned. Choose next action.',
    options: NEAR_PEER_OPTIONS,
  },
  3: {
    turn: 3,
    context:
      'Red main effort confirmed on A6 Daugavpils–Rēzekne axis. Blue screen platoon in contact near Krāslava. Red tank Bn has separated from BTR column — possible flanking. Decide how to employ fires.',
    options: NEAR_PEER_OPTIONS,
  },
  4: {
    turn: 4,
    context:
      'Red artillery (2S19) conducting counter-battery. Blue PzH 2000 battery still effective. Max penetration 14 km. NASAMS AD battery reports Ka-52 contact north of Daugavpils. Combat power holding at ~78%. Choose.',
    options: NEAR_PEER_OPTIONS,
  },
  5: {
    turn: 5,
    context:
      'Krāslava bridge under threat. If red seizes it, A12 spur to BLR border opens as a second axis. Blue has one coy uncommitted. Red cyber disrupted LATSOF comms for 2h. What is your main effort?',
    options: NEAR_PEER_OPTIONS,
  },
  6: {
    turn: 6,
    context:
      'Blue combat power at ~64%. Red penetration at 18 km — 7 km short of Daugavpils. Dvina river line available as fallback. NATO Article 4 consultations begun; Article 5 trigger not yet reached. Posture?',
    options: NEAR_PEER_OPTIONS,
  },
  7: {
    turn: 7,
    context:
      'T+42h. Red 76th VDV reserve has deployed — now on 4h notice. Blue AD coverage holding but NASAMS battery Winchester on 3 salvos. Daugavpils civilian C2 intact. This is likely the decisive turn.',
    options: NEAR_PEER_OPTIONS,
  },
  8: {
    turn: 8,
    context:
      'Blue fires at Krāslava canalization point inflicted 22% on red lead Bn last turn. Red is slowing. Penetration static at 20 km. Red logistics appear stretched. Do you press the advantage or consolidate?',
    options: NEAR_PEER_OPTIONS,
  },
  9: {
    turn: 9,
    context:
      'T+54h. Red operational pause likely — fuel and ammo running thin at forward elements. Blue has window to counterattack or maintain defensive economy-of-force. Article 5 trigger under NATO review.',
    options: NEAR_PEER_OPTIONS,
  },
  10: {
    turn: 10,
    context:
      'Final turn. T+60h. Blue holds Daugavpils. Penetration at 22 km. Blue CP at 62%. Red CP at 38%. This decision determines final combat power ratio and doctrine compliance score for the AAR.',
    options: NEAR_PEER_OPTIONS,
  },
}

// ── Pre-fab scenarios ──────────────────────────────────────────────────────

export const SCENARIO_GREY_HORIZON: Scenario = {
  id: 'scn-grey-horizon',
  name: 'OPERATION GREY HORIZON',
  classification: 'UNCLASSIFIED // FOUO',
  threat_tier: 'near_peer',
  summary:
    'Russian Western Military District forces conduct a limited ground operation along the Latgale axis to seize the Daugavpils–Rēzekne road network, screened by sustained cyber and EW disruption against Latvian C2. Blue is a forward-deployed NATO enhanced Forward Presence battlegroup with Latvian National Armed Forces in support. Mission framed as a 72-hour delay-and-shape engagement pending NATO Article 4 escalation.',
  timeline_hours: 72,
  turns_total: 10,
  location: {
    name: 'Latgale Corridor',
    region: 'Southeastern Latvia',
    country: 'Latvia',
    bbox: [26.1, 55.84, 27.95, 56.55],
    key_routes: ['A6 / E22 Daugavpils–Rēzekne', 'A12 spur to RUS border'],
    terrain_notes:
      'Dvina river crossings (3), boreal forest belt north of Krāslava, urban canalization at Daugavpils',
    pop_centers: ['Daugavpils (~80k)', 'Rēzekne', 'Krāslava', 'Preiļi'],
  },
  blue_force: {
    side: 'blue',
    name: 'eFP Battlegroup Latvia + LATSOF',
    combat_power: 100,
    units: [
      { designation: 'eFP BG HQ', type: 'HQ', equipment: 'C2', location: 'Ādaži', notes: 'CAN lead' },
      { designation: '1× Mech Inf Bn', type: 'Infantry', equipment: 'Warrior IFV', location: 'fwd Rēzekne', notes: 'UK / GBR' },
      { designation: '1× Tank Sqn', type: 'Armour', equipment: 'Leopard 2A5', location: 'Krāslava', notes: 'POL' },
      { designation: '1× SP Arty Bty', type: 'Fires', equipment: 'PzH 2000', location: 'Lielvārde', notes: 'DEU' },
      { designation: '2× LATSOF Recce Plt', type: 'Recce', equipment: 'Light vehicle', location: 'corridor screen', notes: '' },
      { designation: '1× NASAMS Bty', type: 'Air Defence', equipment: 'NASAMS', location: 'Lielvārde', notes: 'NOR' },
      { designation: '1× MQ-9B', type: 'ISR', equipment: 'MQ-9B', location: 'RUS border pattern', notes: 'UK' },
    ],
  },
  red_force: {
    side: 'red',
    name: '1st Guards Tank Army (fwd elements)',
    combat_power: 85,
    units: [
      { designation: '2× Motor Rifle Bn', type: 'Infantry', equipment: 'T-90M / BTR-82A', location: 'Pskov staging', notes: '4th Gds Tank Div (-)' },
      { designation: '1× Tank Bn', type: 'Armour', equipment: 'T-90M2', location: 'Pskov staging', notes: '' },
      { designation: '1× SP Arty Bn', type: 'Fires', equipment: '2S19 Msta', location: 'border area', notes: '' },
      { designation: '1× Recon Coy', type: 'Recce', equipment: 'BRM-3K / Orlan-30 UAV', location: 'fwd screen', notes: '' },
      { designation: 'EW Det', type: 'EW', equipment: 'Krasukha-4', location: 'Pskov', notes: '' },
      { designation: '76th VDV Div', type: 'Reserve', equipment: 'BMD-4', location: 'Pskov', notes: '12h notice' },
    ],
  },
  victory_conditions: {
    blue: [
      'Hold Daugavpils through T+72h',
      'Limit RUS penetration to ≤ 25 km',
      'Preserve ≥ 70% combat power',
      'Maintain civilian C2 over Latgale',
    ],
    red: [
      'Seize A6 corridor to Rēzekne',
      'Inflict ≥ 30% blue combat losses',
      'Disrupt NATO C2 for ≥ 24h cumulative',
      'Establish fait accompli before Art. 5 trigger',
    ],
  },
  available_modifiers: [
    { key: 'cyber_opening', label: 'Cyber disruption opening', description: 'Red begins with sustained DDoS against Latvian C2', value: true, default_value: true },
    { key: 'red_reserves', label: 'Red reserves committed', description: '76th VDV on 4h instead of 12h notice', value: false, default_value: false },
    { key: 'weather_degraded', label: 'Weather: degraded visibility', description: 'Air assets limited; range reduced 30%', value: true, default_value: true },
    { key: 'nato_media_pressure', label: 'NATO media/IO pressure', description: 'Blue decision timeline compressed by political OpTempo', value: false, default_value: false },
    { key: 'civilian_axis', label: 'Civilian infrastructure axis', description: 'Adds humanitarian decision points each turn', value: false, default_value: false },
  ],
  active_modifier_keys: ['cyber_opening', 'weather_degraded'],
  budget: { label: 'NATO Support Package', total: 420, remaining: 420, unit: '$M' },
  seed_events: [
    { date: '2026-04-22', description: 'DDoS campaign against Latvian government portals attributed to APT28', source: 'GDELT', source_id: '1192384772' },
    { date: '2026-04-19', description: 'Increased Russian armor sightings near Pskov; ZAPAD-style readiness exercise', source: 'ACLED', source_id: 'LVA-RUS-0419-04' },
    { date: '2026-04-15', description: 'Belarusian airspace incursion; Latvia files NATO Article 4 consultations', source: 'GDELT', source_id: '1191875221' },
    { date: '2026-04-09', description: 'Cyber probing of Latvian energy SCADA; CERT.LV public advisory', source: 'GDELT', source_id: '1190442016' },
  ],
  doctrine_citations: [
    {
      text: "Multi-domain operations require integrated synchronization of cyber, electromagnetic spectrum, and physical effects to converge against an adversary's decision-making cycle.",
      source: 'JP 3-0 · Operations · §IV-12',
      relevance: 'grounds blue posture against integrated cyber/EW threat axis',
    },
    {
      text: "Defending forces canalize the attacker into restrictive terrain to mass fires at decisive points while preserving combat power for the counter-attack.",
      source: 'FM 3-90 · Tactics · §3.4',
      relevance: 'justifies blue economy-of-force in Latgale corridor',
    },
    {
      text: 'Reflexive control through cyber and information operations seeks to shape adversary decisions before kinetic engagement.',
      source: 'Joint DoD Russian New-Generation Warfare Study · §2.7',
      relevance: 'explains red opening cyber salvo as doctrinal',
    },
  ],
  generated_at: '2026-04-25T17:41:00Z',
  generated_in_seconds: 28.4,
  run_id: '7f3a2c',
}

export const SCENARIO_JADE_GATE: Scenario = {
  id: 'scn-jade-gate',
  name: 'OPERATION JADE GATE',
  classification: 'UNCLASSIFIED',
  threat_tier: 'peer',
  summary:
    'PLA Eastern Theater Command initiates a maritime blockade of Taiwan with simultaneous air and missile strikes on key infrastructure. Blue is a USN carrier strike group with USMC MEF assets and joint coalition support. Mission is to break the blockade within 96h before economic and political costs become irreversible.',
  timeline_hours: 96,
  turns_total: 10,
  location: {
    name: 'Taiwan Strait / Western Pacific',
    region: 'East Asia',
    country: 'Taiwan',
    bbox: [119.0, 21.5, 123.5, 26.5],
    key_routes: ['Taiwan Strait centerline', 'Bashi Channel', 'Miyako Strait'],
    terrain_notes: 'Open ocean with island chokepoints; A2/AD bubble extending 1,000 nm',
    pop_centers: ['Taipei', 'Kaohsiung', 'Taichung', 'Keelung'],
  },
  blue_force: {
    side: 'blue',
    name: 'CSG-11 + USMC MEF + JASDF',
    combat_power: 100,
    units: [
      { designation: 'CVN-72 Lincoln', type: 'Carrier', equipment: 'F/A-18E/F, EA-18G, E-2D', location: 'Philippine Sea', notes: 'CSG-11 lead' },
      { designation: '2× DDG Flt III', type: 'Surface', equipment: 'SM-6, Tomahawk', location: 'screen', notes: '' },
      { designation: '2× SSN', type: 'Subsurface', equipment: 'Mk-48, TLAM', location: 'fwd patrol', notes: '' },
      { designation: '1× MEU', type: 'Amphibious', equipment: 'F-35B, MV-22', location: 'Okinawa', notes: 'USMC' },
      { designation: 'JASDF 301 Sq', type: 'Air', equipment: 'F-35A', location: 'Kadena', notes: 'coalition' },
    ],
  },
  red_force: {
    side: 'red',
    name: 'PLA Eastern Theater Command',
    combat_power: 90,
    units: [
      { designation: '3× DDG Type-055', type: 'Surface', equipment: 'YJ-18, HHQ-9B', location: 'strait', notes: '' },
      { designation: '4× SSK Type-039', type: 'Subsurface', equipment: 'Yu-6', location: 'Bashi Channel', notes: '' },
      { designation: '2× H-6K Rgt', type: 'Air', equipment: 'YJ-12 ASCM', location: 'Fujian', notes: '' },
      { designation: 'DF-21D Bde', type: 'Ballistic Missile', equipment: 'DF-21D ASBM', location: 'Fujian', notes: '' },
    ],
  },
  victory_conditions: {
    blue: [
      'Break blockade within 96h',
      'Maintain CVN survivability',
      'Preserve Taiwan port access',
      'Prevent PLA amphibious lodgment',
    ],
    red: [
      'Sustain blockade ≥ 96h',
      'Force blue CVN withdrawal',
      'Destroy ≥ 40% blue surface combatants',
      'Establish air superiority over strait',
    ],
  },
  available_modifiers: [
    { key: 'a2ad_full', label: 'Full A2/AD activation', description: 'PLA radar + SAM network at full readiness', value: true, default_value: true },
    { key: 'cyber_grid', label: 'Taiwan grid attack', description: 'PLA cyber hits Taiwan power grid at T+0', value: false, default_value: false },
    { key: 'third_party', label: 'Third-party escalation', description: 'DPRK conducts demonstration missile test T+24h', value: false, default_value: false },
    { key: 'coalition_support', label: 'Coalition fires support', description: 'UK, AUS, JPN actively contribute long-range fires', value: true, default_value: true },
    { key: 'space_degraded', label: 'Space assets degraded', description: 'GPS/comms disrupted; blue relies on INS + datalink', value: false, default_value: false },
  ],
  active_modifier_keys: ['a2ad_full', 'coalition_support'],
  budget: { label: 'Joint Fires Package', total: 880, remaining: 880, unit: '$M' },
  seed_events: [],
  doctrine_citations: [
    {
      text: "Anti-access/area-denial environments require distributed maritime operations and long-range precision fires to create dilemmas inside the adversary's engagement zone.",
      source: 'NDS 2022 · §III Maritime',
      relevance: 'grounds blue standoff fires approach',
    },
  ],
  generated_at: '2026-04-25T17:41:00Z',
  generated_in_seconds: 31.7,
  run_id: '8b4e1f',
}

export const SCENARIO_HARMATTAN: Scenario = {
  id: 'scn-harmattan',
  name: 'OPERATION HARMATTAN ECHO',
  classification: 'UNCLASSIFIED',
  threat_tier: 'hybrid',
  summary:
    'VEO coalition seizes regional capital Gao and establishes a contested zone in central Mali following MINUSMA withdrawal. Blue is a joint AFRICOM/French special operations task force with Malian Armed Forces partner units. Mission is population-centric COIN to restore government control within 48h before international recognition of VEO administration.',
  timeline_hours: 48,
  turns_total: 8,
  location: {
    name: 'Gao Province',
    region: 'Central Mali',
    country: 'Mali',
    bbox: [-1.5, 15.5, 1.0, 17.2],
    key_routes: ['N16 Gao–Kidal highway', 'Niger River corridor'],
    terrain_notes: 'Semi-arid Sahel; limited paved roads; IED threat on MSRs',
    pop_centers: ['Gao (~90k)', 'Ansongo', 'Bourem'],
  },
  blue_force: {
    side: 'blue',
    name: 'JSOTF-Africa + French SOF + FAMa',
    combat_power: 100,
    units: [
      { designation: 'ODA-team cluster', type: 'SF', equipment: 'light infantry, AC-130U', location: 'FOB Tessalit', notes: 'AFRICOM' },
      { designation: 'CPA-10 Det', type: 'SF', equipment: 'light vehicle, Mirage 2000D reach-back', location: 'Gao perimeter', notes: 'French SOF' },
      { designation: '1× FAMa Coy', type: 'Partner Force', equipment: 'light infantry', location: 'Gao', notes: 'variable readiness' },
      { designation: 'MQ-9 ISR cell', type: 'ISR', equipment: 'MQ-9', location: 'Niamey reach-back', notes: '' },
    ],
  },
  red_force: {
    side: 'red',
    name: 'GSIM-JNIM Coalition VEO',
    combat_power: 70,
    units: [
      { designation: 'GSIM urban cell', type: 'Irregular', equipment: 'SVBIED, RPG-7', location: 'Gao city', notes: '' },
      { designation: 'JNIM mobile element', type: 'Irregular', equipment: 'technicals, MANPADS', location: 'N16 axis', notes: '' },
      { designation: 'IO/influence cell', type: 'Information', equipment: 'social media, FM radio', location: 'distributed', notes: 'narrative warfare' },
    ],
  },
  victory_conditions: {
    blue: [
      'Restore Gao government control by T+48h',
      'Limit civilian casualties ≤ 15',
      'Neutralize VEO command node',
      'Maintain FAMa partner force cohesion',
    ],
    red: [
      'Hold Gao for ≥ 48h',
      'Inflict ≥ 5 blue SF casualties',
      'Trigger international media condemnation',
      'Fracture FAMa–coalition relationship',
    ],
  },
  available_modifiers: [
    { key: 'io_active', label: 'VEO IO campaign active', description: 'Real-time propaganda degrades population support', value: true, default_value: true },
    { key: 'fama_fragile', label: 'FAMa cohesion fragile', description: 'Partner force requires management each turn', value: true, default_value: true },
    { key: 'hostages', label: 'Civilian hostages present', description: 'Adds ROE constraints on direct action', value: false, default_value: false },
    { key: 'acled_feed', label: 'Live ACLED event feed', description: 'Seed events update from real ACLED API each turn', value: false, default_value: false },
  ],
  active_modifier_keys: ['io_active', 'fama_fragile'],
  budget: { label: 'JSOTF-AF Support Package', total: 85, remaining: 85, unit: '$M' },
  seed_events: [],
  doctrine_citations: [
    {
      text: 'COIN operations require the host nation government to provide security, good governance, and development simultaneously to deny the insurgent legitimacy.',
      source: 'FM 3-24 · Counterinsurgency · §1.4',
      relevance: 'grounds whole-of-government approach in Gao',
    },
  ],
  generated_at: '2026-04-25T17:41:00Z',
  generated_in_seconds: 19.2,
  run_id: '2c9d3a',
}

export const ALL_SCENARIOS: Scenario[] = [
  SCENARIO_GREY_HORIZON,
  SCENARIO_JADE_GATE,
  SCENARIO_HARMATTAN,
]

// ── Completed game state (for demo debrief) ────────────────────────────────

const COMPLETED_AAR: AAR = {
  outcome: {
    label: 'blue_win',
    summary:
      'Blue achieved 3 of 4 victory conditions. Daugavpils held through T+72h; corridor preserved through deliberate canalization in turns 3–5; combat power retention 68% (failed threshold by 2%). Red achieved tactical surprise in opening cyber phase but failed to convert tempo into ground gains after blue\'s turn-4 fires reorientation.',
    blue_cp_final: 68,
    red_cp_final: 32,
    max_penetration_km: 22.4,
    turns_played: 7,
    blue_conditions_met: 3,
    red_conditions_met: 1,
    conditions_total: 4,
  },
  key_turns: [2, 4, 6],
  lessons: [
    { category: 'strategic', text: 'Cyber-led reflexive-control phases are now standard red-cell openings; blue C2 hardening must be assumed day-one rather than reactive.' },
    { category: 'operational', text: 'NASAMS placement at Lielvārde left a 30 km gap over Daugavpils airspace through T+12h; coverage planning needs explicit overlap audit.' },
    { category: 'tactical', text: 'Restrictive-terrain canalization remains the defender\'s highest-leverage move; Krāslava forest belt forced red into a 2 km axis with predictable fires solutions.' },
    { category: 'doctrinal', text: 'Turn-6 withdrawal showed value of FM 3-90 §4.2 trade-space thinking; planners should pre-identify withdrawal lines, not improvise under contact.' },
    { category: 'cognitive', text: 'Blue committed to ISR pattern at T+2 with high confidence; later turns showed appropriate willingness to update — no anchoring observed.' },
  ],
  recommendations: [
    { text: 'Run repeat scenario with red opening cyber duration set to 8h instead of 4h to test blue C2 resilience under sustained disruption.' },
    { text: 'Brief eFP planners on FM 3-90 §4.2 trade-space framework; turn-6 decision was correct but appeared improvised.' },
    { text: 'Pre-stage AD coverage overlap audit as a planning checkpoint at every BG-level rehearsal.' },
    { text: 'Add civilian infrastructure overlay to mission-rehearsal scenarios; current run did not stress humanitarian decision points.' },
    { text: 'Generate companion scenario with red 76th VDV reserve committed at T+24h to test blue counter-attack timing.' },
  ],
  doctrine_citations: [
    { text: 'Defenders concentrate fires at the decisive point — typically where terrain canalizes the attacker into a predictable axis.', source: 'FM 3-0 · §5.3', relevance: 'turn-4 fires reorientation aligns with doctrine' },
    { text: 'Trading ground for posture is a legitimate defensive option when terrain offers superior subsequent positions.', source: 'FM 3-90 · §4.2', relevance: 'justifies turn-6 withdrawal decision' },
    { text: 'ISR allocation should follow the commander\'s priority intelligence requirements, not asset availability.', source: 'JP 2-01 · §III-7', relevance: 'turn-2 ISR commitment was doctrinally sound' },
  ],
  generated_in_seconds: 11.2,
}

export const GAME_STATE_IN_PROGRESS: GameState = {
  scenario_id: 'scn-grey-horizon',
  run_id: '7f3a2c',
  status: 'running',
  current_turn: 4,
  next_checkin_iso: '2026-04-26T05:42:00Z',
  blue_force: { ...SCENARIO_GREY_HORIZON.blue_force, combat_power: 78 },
  red_force: { ...SCENARIO_GREY_HORIZON.red_force, combat_power: 64 },
  max_penetration_km: 14.2,
  turn_log: [
    {
      turn: 1,
      elapsed_hours: 6,
      blue_action_key: 'commit_reserve',
      blue_action_label: 'COMMIT RESERVE',
      blue_note: 'Task MQ-9B to border pattern-of-life',
      red_action_label: 'CYBER STRIKE + ADVANCE',
      narrative: 'Blue ISR committed early confirmed red main effort on A6 axis. Red cyber disrupted blue C2 for 3h but failed to achieve operational surprise. Blue CP: 96, Red CP: 82.',
      blue_cp_after: 96,
      red_cp_after: 82,
      penetration_km_after: 4.0,
      doctrine_refs: ['JP 2-01 §III-7'],
    },
    {
      turn: 2,
      elapsed_hours: 12,
      blue_action_key: 'hold',
      blue_action_label: 'HOLD FORWARD',
      blue_note: '',
      red_action_label: 'ARMORED ADVANCE',
      narrative: 'Blue screen platoon in contact near Krāslava. Red tank Bn attempted flanking via forest belt — terrain canalized them back to A6. Attrition exchange favoring blue. Blue CP: 92, Red CP: 76.',
      blue_cp_after: 92,
      red_cp_after: 76,
      penetration_km_after: 8.1,
      doctrine_refs: ['FM 3-90 §3.4'],
    },
    {
      turn: 3,
      elapsed_hours: 18,
      blue_action_key: 'reorient_fires',
      blue_action_label: 'REORIENT FIRES',
      blue_note: 'PzH 2000 from counter-battery to massed fires at canalization point',
      red_action_label: 'PRESS ON A6',
      narrative: 'Blue tube fires massed at Krāslava canalization point. Red lead motor rifle Bn took 18% losses in 40 minutes. Red advance stalled. Blue CP: 86, Red CP: 68.',
      blue_cp_after: 86,
      red_cp_after: 68,
      penetration_km_after: 11.4,
      doctrine_refs: ['FM 3-0 §5.3'],
    },
  ],
  pending_decision: GREY_HORIZON_DECISIONS[4],
  aar: null,
}

export const GAME_STATE_COMPLETED: GameState = {
  scenario_id: 'scn-grey-horizon',
  run_id: '7f3a2c',
  status: 'ended',
  current_turn: 7,
  next_checkin_iso: null,
  blue_force: { ...SCENARIO_GREY_HORIZON.blue_force, combat_power: 68 },
  red_force: { ...SCENARIO_GREY_HORIZON.red_force, combat_power: 32 },
  max_penetration_km: 22.4,
  turn_log: [
    ...GAME_STATE_IN_PROGRESS.turn_log,
    {
      turn: 4,
      elapsed_hours: 24,
      blue_action_key: 'reorient_fires',
      blue_action_label: 'REORIENT FIRES',
      blue_note: '',
      red_action_label: 'FLANK ATTEMPT',
      narrative: 'Blue fires reorientation decisive. Red flank attempt through Dvina marshes failed; terrain denied. Max penetration held at 14 km. Blue CP: 78, Red CP: 54.',
      blue_cp_after: 78,
      red_cp_after: 54,
      penetration_km_after: 14.2,
      doctrine_refs: ['FM 3-0 §5.3'],
    },
    {
      turn: 5,
      elapsed_hours: 30,
      blue_action_key: 'hold',
      blue_action_label: 'HOLD FORWARD',
      blue_note: 'Reinforcing Krāslava bridge defense',
      red_action_label: 'BRIDGE SEIZURE ATTEMPT',
      narrative: 'Red attempted Krāslava bridge seizure. Blue coy held. Bridge intact. Red operational tempo declining — logistics strain visible. Blue CP: 74, Red CP: 46.',
      blue_cp_after: 74,
      red_cp_after: 46,
      penetration_km_after: 16.8,
      doctrine_refs: ['FM 3-90 §3.4'],
    },
    {
      turn: 6,
      elapsed_hours: 36,
      blue_action_key: 'withdraw',
      blue_action_label: 'WITHDRAW LOCALLY',
      blue_note: 'Consolidate behind Dvina line; preserve AD coverage',
      red_action_label: 'EXPLOITATION',
      narrative: 'Blue accepted 2 km local withdrawal at Krāslava to consolidate behind the Dvina. Trade preserved AD coverage and sustainment lines. Blue CP: 70, Red CP: 40.',
      blue_cp_after: 70,
      red_cp_after: 40,
      penetration_km_after: 20.1,
      doctrine_refs: ['FM 3-90 §4.2'],
    },
    {
      turn: 7,
      elapsed_hours: 42,
      blue_action_key: 'hold',
      blue_action_label: 'HOLD FORWARD',
      blue_note: 'Daugavpils defense priority',
      red_action_label: 'FINAL PUSH',
      narrative: 'Red final push stalled at Dvina river line. Blue NASAMS neutralized Ka-52 pair. Red 76th VDV reserve did not commit — logistics unsupportable. Game ends. Blue CP: 68, Red CP: 32.',
      blue_cp_after: 68,
      red_cp_after: 32,
      penetration_km_after: 22.4,
      doctrine_refs: ['JP 3-0 §IV-12'],
    },
  ],
  pending_decision: null,
  aar: COMPLETED_AAR,
}
