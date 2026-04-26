// mock-data.ts
// Scenario data sourced from starter_kits_v2.json + wargame_unit_library_v3.json.
// Unit names resolved from the unit library (asset_id → full name + category).
// Replace with /scenarios API responses from the backend.

import type {
  Scenario,
  GameState,
  PendingDecision,
  DecisionOption,
  Force,
  Unit,
  AAR,
} from './schema'

// ── Generic land decision option set (reused across land scenarios) ───────

export const LAND_OPTIONS: DecisionOption[] = [
  {
    key: 'hold',
    label: 'HOLD FORWARD',
    sub_label: 'Maintain current positions',
    consequence_hint: 'Preserves terrain, accepts attrition',
  },
  {
    key: 'reorient_fires',
    label: 'REORIENT FIRES',
    sub_label: 'Mass fires at canalization point',
    consequence_hint: 'Disrupts RED tempo on confirmed axis',
  },
  {
    key: 'commit_reserve',
    label: 'COMMIT RESERVE',
    sub_label: 'Release special forces from screening',
    consequence_hint: 'Gains intelligence, exposes reserve',
  },
  {
    key: 'withdraw',
    label: 'WITHDRAW LOCALLY',
    sub_label: 'Fall back to prepared defensive line',
    consequence_hint: 'Preserves combat power, cedes terrain',
  },
]

export const AMPHIBIOUS_OPTIONS: DecisionOption[] = [
  {
    key: 'hold',
    label: 'HOLD PATROL ZONE',
    sub_label: 'Maintain surface/subsurface screen',
    consequence_hint: 'Denies crossing, risk of asset attrition',
  },
  {
    key: 'strike',
    label: 'STRIKE FLEET',
    sub_label: 'Commit SSN + air to lead RED vessels',
    consequence_hint: 'High damage potential, exposes SSN',
  },
  {
    key: 'commit_reserve',
    label: 'DEPLOY MARINES',
    sub_label: 'Land Marine Bn on contested beach node',
    consequence_hint: 'Secures lodgment, splits blue combat power',
  },
  {
    key: 'withdraw',
    label: 'CONSOLIDATE ISLAND',
    sub_label: 'Pull back to island defense perimeter',
    consequence_hint: 'Preserves assets, risks RED beach lodgment',
  },
]

export const URBAN_OPTIONS: DecisionOption[] = [
  {
    key: 'hold',
    label: 'HOLD PERIMETER',
    sub_label: 'Maintain current cordon around city nodes',
    consequence_hint: 'Stable but IED and drone pressure mounts',
  },
  {
    key: 'commit_reserve',
    label: 'COMMIT SOF',
    sub_label: 'Task ODA toward Government District',
    consequence_hint: 'Win-condition delivery — high value, high risk',
  },
  {
    key: 'reorient_fires',
    label: 'APACHE STRIKE',
    sub_label: 'AH-64 battalion targets drone swarm concentration',
    consequence_hint: 'Neutralises air threat, reveals Apache to MANPADS',
  },
  {
    key: 'withdraw',
    label: 'CONSOLIDATE BASE',
    sub_label: 'Withdraw to Coalition Forward Base perimeter',
    consequence_hint: 'Preserves force, cedes city nodes and income',
  },
]

// ── Per-turn decision library (Iron Corridor - land scenario) ─────────────

export const GREY_HORIZON_DECISIONS: Record<number, PendingDecision> = {
  1: {
    turn: 1,
    context: 'Turn 1. RED cyber team opens with EW and C2 disruption. RED armor column departing Forward Staging Area — 3× BTG T-90M on primary axis. BLUE cyber and SOF are at full readiness. Choose opening posture.',
    options: LAND_OPTIONS,
  },
  2: {
    turn: 2,
    context: 'RED BTGs crossed entry node. Lead BTG in contact with BLUE screen near Northern Depot. Iskander-M Brigade deploying to fires position. BLUE HIMARS is pre-positioned. Contested nodes under pressure.',
    options: LAND_OPTIONS,
  },
  3: {
    turn: 3,
    context: 'RED main effort confirmed on primary axis toward Junction Town. Spetsnaz company detected probing River Crossing flanking route. BLUE Patriot engaged inbound Iskander — intercept success 80%. Decide fires posture.',
    options: LAND_OPTIONS,
  },
  4: {
    turn: 4,
    context: 'RED BTG #2 pressing toward Junction Town from Northern Depot. BLUE armored BCT holding Southern Depot. F-35A Strike Wing available for fires tasking. BLUE CP 78%. Choose next priority.',
    options: LAND_OPTIONS,
  },
  5: {
    turn: 5,
    context: 'River Crossing under threat. If RED seizes it, second axis opens to Junction Town. BLUE SOF ODA teams uncommitted. RED Cyber Team disrupting BLUE C2 — 15% degradation. What is your main effort?',
    options: LAND_OPTIONS,
  },
  6: {
    turn: 6,
    context: 'BLUE CP at ~64%. RED has taken Northern Depot. Junction Town 2 nodes away. Economic Exhaustion threshold at $2.1B — BLUE has $3.8B remaining. New defensive line available at river. Choose posture.',
    options: LAND_OPTIONS,
  },
  7: {
    turn: 7,
    context: 'T+42h. BLUE income advantage growing — held Southern Depot and Coastal Port. RED supply chain declining to 62%. RED BTG #3 committed from staging. HIMARS has deep strike solution on RED arty. Decide.',
    options: LAND_OPTIONS,
  },
  8: {
    turn: 8,
    context: 'RED operational tempo declining — logistics stretched. Northern Depot supply lines thin. BLUE has combat power advantage if attrition continues. River Crossing still contested. Opportunity to press.',
    options: LAND_OPTIONS,
  },
  9: {
    turn: 9,
    context: 'T+54h. RED BTG #1 at 35% strength. Iskander reload cycle at risk. Coalition reinforcement arriving T+96h. BLUE must hold Junction Town until then. Final defensive consolidation or counterattack window.',
    options: LAND_OPTIONS,
  },
  10: {
    turn: 10,
    context: 'Final turn. BLUE holds Junction Town and 2 of 4 contested nodes. RED at 38% CP. Economic attrition favors BLUE. This decision determines final conditions score and AAR doctrine compliance rating.',
    options: LAND_OPTIONS,
  },
}

// ── Unit builder helper ───────────────────────────────────────────────────

function u(
  assetId: string,
  name: string,
  type: string,
  equipment: string,
  location: string,
  qty: number,
  readiness: number,
): Unit {
  return {
    designation: qty > 1 ? `${qty}× ${name}` : name,
    type,
    equipment: `${assetId} — ${equipment}`,
    location,
    notes: `readiness ${readiness}%`,
  }
}

// ── SCN-001: Iron Corridor ────────────────────────────────────────────────

const IRON_BLUE_UNITS: Unit[] = [
  u('ARM-001', 'Armored Brigade Combat Team', 'Armor',              'US Armored Brigade Combat Team', 'Main Base',              1, 90),
  u('LI-005',  'Marine Rifle Battalion',       'Light Infantry',    'US Marine Rifle Battalion',       'Main Base',              1, 95),
  u('ART-001', 'HIMARS Battery',               'Artillery',         'HIMARS Battery',                  'Main Base',              1, 100),
  u('AD-002',  'Patriot PAC-3 Battery',        'Air Defense',       'Patriot PAC-3 MSE Battery',       'Main Base',              1, 88),
  u('AIR-001', 'F-35A Strike Wing',            'Air',               'F-35A Strike Wing',               'Main Base',              1, 85),
  u('SPE-001', 'Special Forces ODA',           'Special Ops',       'US Special Forces ODA',           'Main Base',              2, 100),
  u('SPE-002', 'Cyber Operations Team',        'Special Ops',       'NSA Cyber Operations Team',       'Main Base',              1, 100),
]

const IRON_RED_UNITS: Unit[] = [
  u('ARM-002', 'Armored Battle Group (T-90M)', 'Armor',             'Russian BTG (T-90M)',              'Forward Staging Area',   3, 85),
  u('ART-003', 'Iskander-M Brigade',           'Artillery',         'Russian Iskander-M Brigade',       'Forward Staging Area',   1, 90),
  u('AD-003',  'S-400 Triumf Regiment',        'Air Defense',       'S-400 Triumf Regiment',            'Forward Staging Area',   1, 88),
  u('AIR-003', 'Su-35S Fighter Regiment',      'Air',               'Su-35S Fighter Regiment',          'Forward Staging Area',   1, 80),
  u('SPE-003', 'Spetsnaz Company',             'Special Ops',       'Russian Spetsnaz Company',         'Forward Staging Area',   2, 100),
  u('SPE-004', 'Unit 61398 Cyber Team',        'Special Ops',       'PLA Unit 61398 Cyber Team',        'Forward Staging Area',   1, 100),
]

const IRON_BLUE: Force = { side: 'blue', name: 'Coalition Defense Force', combat_power: 100, units: IRON_BLUE_UNITS }
const IRON_RED:  Force = { side: 'red',  name: 'Mechanized Assault Force (RED_RU)', combat_power: 85, units: IRON_RED_UNITS }

export const SCENARIO_IRON_CORRIDOR: Scenario = {
  id:                  'SCN-001',
  name:                'IRON CORRIDOR',
  classification:      'UNCLASSIFIED',
  threat_tier:         'near_peer',
  scenario_type:       'LAND',
  strategic_objective: 'RESOURCE_CONTROL',
  summary:             'RED mechanized force pushes through a land corridor toward BLUE-held territory. BLUE holds defensive positions and attrits the advance. Cyber and EW active from turn 1. No significant naval component — landlocked operational area.',
  timeline_hours:      168,
  turns_total:         10,
  location: {
    name:          'Iron Corridor',
    region:        'Rural / Mixed — open plains, forest corridors, river crossings, light urban',
    country:       'Generic',
    bbox:          null,
    key_routes:    ['Northern Depot', 'Southern Depot', 'River Crossing', 'Junction Town'],
    terrain_notes: 'Objective: Junction Town. Landlocked — no significant naval component.',
    pop_centers:   ['Junction Town'],
  },
  nodes: {
    blue_land_entry:  'Main Base',
    blue_sea_entry:   'Coastal Logistics Port',
    red_land_entry:   'Forward Staging Area',
    red_sea_entry:    'Secondary Logistics Harbor',
    contested_nodes:  ['Northern Depot', 'Southern Depot', 'River Crossing', 'Junction Town'],
    objective_node:   'Junction Town',
  },
  blue_force:    IRON_BLUE,
  red_force:     IRON_RED,
  blue_resources: { dollars_millions: 6000, income_per_turn_millions: 280, supply_chain: 82, stability: 78, intel: 25 },
  red_resources:  { dollars_millions: 4500, income_per_turn_millions: 220, supply_chain: 75, stability: 70, intel: 30 },
  victory_conditions: {
    blue: [
      'Hold Junction Town and ≥ 2 of 4 contested nodes through turn 28',
      'Avoid Economic Exhaustion (budget > $0)',
      'Avoid Supply Chain Collapse',
      'Avoid Command Decapitation',
    ],
    red: [
      'Trigger any BLUE loss condition',
      'ANNIHILATION — destroy all BLUE combat assets (secondary path)',
    ],
  },
  available_modifiers: [
    { key: 'cyber_opening',  label: 'Cyber disruption opening',  description: 'RED Cyber Team opens with sustained C2 disruption from turn 1', value: true,  default_value: true  },
    { key: 'red_reserves',   label: 'RED reserves committed',    description: 'Additional BTG on 4h notice at Forward Staging Area',           value: false, default_value: false },
    { key: 'weather_mud',    label: 'Spring mud / mobility loss', description: 'Armor speed -30%, forest tracks impassable',                   value: false, default_value: false },
    { key: 'nato_reinforce', label: 'NATO reinforcement window', description: 'Coalition reinforcement arrives at turn 20 instead of 28',       value: false, default_value: false },
    { key: 'supply_pressure','label': 'Supply chain pressure',   description: 'Both factions start with supply_chain -10 — attrition accelerated', value: false, default_value: false },
  ],
  active_modifier_keys: ['cyber_opening'],
  budget:             { label: 'Coalition Defense Package', total: 6000, remaining: 6000, unit: '$M' },
  seed_events:        [],
  doctrine_citations: [
    {
      text:      'Defending forces canalize the attacker into restrictive terrain to mass fires at decisive points while preserving combat power for the counter-attack.',
      source:    'FM 3-90 · Tactics · §3.4',
      relevance: 'BLUE economy-of-force posture against BTG mass',
    },
    {
      text:      'Multi-domain operations require integrated synchronization of cyber, electromagnetic spectrum, and physical effects to converge against an adversary\'s decision-making cycle.',
      source:    'JP 3-0 · Operations · §IV-12',
      relevance: 'RED EW + cyber opening phase doctrine basis',
    },
    {
      text:      'Resource control at key terrain features forces the attacker into predictable axes and degrades operational logistics.',
      source:    'FM 3-0 · Operations · §3.1',
      relevance: 'Node-based victory condition design rationale',
    },
  ],
  generated_at:         '2026-04-25T17:41:00Z',
  generated_in_seconds: 24.1,
  run_id:               'IC-001',
}

// ── SCN-002: Blue Water ───────────────────────────────────────────────────

const WATER_BLUE_UNITS: Unit[] = [
  u('MBT-001', 'Arleigh Burke DDG',        'Maritime Combat', 'Arleigh Burke DDG',          'Allied Naval Station',  2, 95),
  u('MBT-002', 'Virginia-class SSN',       'Maritime Combat', 'Virginia-class SSN',          'Allied Naval Station',  1, 92),
  u('AIR-001', 'F-35A Strike Wing',        'Air',             'F-35A Strike Wing',            'Island Defense Base',   1, 88),
  u('AD-001',  'THAAD Battery',            'Air Defense',     'THAAD Battery',               'Island Defense Base',   1, 90),
  u('LI-005',  'Marine Rifle Battalion',   'Light Infantry',  'US Marine Rifle Battalion',    'Island Defense Base',   1, 95),
  u('SPE-002', 'Cyber Operations Team',    'Special Ops',     'NSA Cyber Operations Team',    'Island Defense Base',   1, 100),
]

const WATER_RED_UNITS: Unit[] = [
  u('MCG-004', 'Type 071 LPD',             'Maritime Cargo',  'PLA Type 071 LPD',            'Assault Fleet Harbor',  2, 90),
  u('TRN-005', 'Type 072 LST',             'Transport',       'PLA Type 072 LST',            'Assault Fleet Harbor',  2, 88),
  u('MBT-003', 'Type 055 Destroyer',       'Maritime Combat', 'PLA Type 055 Destroyer',      'Assault Fleet Harbor',  1, 92),
  u('AIR-002', 'J-20 Stealth Squadron',    'Air',             'J-20 Stealth Squadron',        'Mainland Staging Base', 1, 85),
  u('ARM-003', 'Combined Arms Brigade',    'Armor',           'PLA Combined Arms Brigade',    'Mainland Staging Base', 1, 88),
  u('SPE-004', 'Unit 61398 Cyber Team',    'Special Ops',     'PLA Unit 61398 Cyber Team',   'Mainland Staging Base', 1, 100),
  u('ART-004', 'PHL-03 MLRS Regiment',     'Artillery',       'PLA PHL-03 MLRS Regiment',    'Mainland Staging Base', 1, 85),
]

const WATER_BLUE: Force = { side: 'blue', name: 'Naval Defense Force (BLUE)',      combat_power: 100, units: WATER_BLUE_UNITS }
const WATER_RED:  Force = { side: 'red',  name: 'Amphibious Assault Force (RED_CN)', combat_power: 90, units: WATER_RED_UNITS }

export const SCENARIO_BLUE_WATER: Scenario = {
  id:                  'SCN-002',
  name:                'BLUE WATER',
  classification:      'UNCLASSIFIED',
  threat_tier:         'peer',
  scenario_type:       'AMPHIBIOUS',
  strategic_objective: 'ANNIHILATION',
  summary:             'RED amphibious assault force attempts to cross a contested strait and establish a lodgment. BLUE naval and air forces contest the crossing. Land nodes are secondary — the strait and the beachhead are the fight.',
  timeline_hours:      168,
  turns_total:         10,
  location: {
    name:          'Blue Water Strait',
    region:        'Coastal / Littoral — strait crossing, beach nodes, port facilities, island terrain',
    country:       'Generic',
    bbox:          null,
    key_routes:    ['Northern Beach', 'Southern Beach', 'Main Port', 'Strait Chokepoint'],
    terrain_notes: 'Objective: destroy RED amphibious fleet or deny all beach nodes through turn 28.',
    pop_centers:   ['Main Port'],
  },
  nodes: {
    blue_land_entry:  'Island Defense Base',
    blue_sea_entry:   'Allied Naval Station',
    red_land_entry:   'Mainland Staging Base',
    red_sea_entry:    'Assault Fleet Harbor',
    contested_nodes:  ['Northern Beach', 'Southern Beach', 'Main Port', 'Strait Chokepoint'],
    objective_node:   'Main Port',
  },
  blue_force:    WATER_BLUE,
  red_force:     WATER_RED,
  blue_resources: { dollars_millions: 9000, income_per_turn_millions: 380, supply_chain: 80, stability: 72, intel: 35 },
  red_resources:  { dollars_millions: 7500, income_per_turn_millions: 340, supply_chain: 78, stability: 82, intel: 40 },
  victory_conditions: {
    blue: [
      'Destroy RED amphibious fleet before lodgment established',
      'Deny all beach nodes through turn 28',
      'Avoid Economic Exhaustion, Supply Chain Collapse, Political Will Failure',
      'Prevent RED lodgment: ≥ 2 RED assets ashore for 5 consecutive turns',
    ],
    red: [
      'Trigger any BLUE loss condition',
      'RESOURCE_CONTROL — hold Main Port for 10 consecutive turns (secondary path)',
    ],
  },
  available_modifiers: [
    { key: 'a2ad_full',       label: 'Full A2/AD activation',     description: 'PLA radar + SAM network at full readiness from turn 1',           value: true,  default_value: true  },
    { key: 'ssn_risk',        label: 'SSN detection risk',        description: 'RED sub-hunting assets elevated — SSN exposure increases 20%',     value: false, default_value: false },
    { key: 'weather_sea',     label: 'Heavy sea state',           description: 'Amphibious crossing speed -40%; landing turns extended by 2',       value: false, default_value: false },
    { key: 'coalition_fires', label: 'Coalition fires support',   description: 'Allied long-range fires available from turn 5',                    value: true,  default_value: true  },
    { key: 'cyber_grid',      label: 'Island grid cyber attack',  description: 'RED Cyber hits island power grid at T+0; BLUE C2 -20% turns 1–3',  value: false, default_value: false },
  ],
  active_modifier_keys: ['a2ad_full', 'coalition_fires'],
  budget:             { label: 'Naval Defense Package', total: 9000, remaining: 9000, unit: '$M' },
  seed_events:        [],
  doctrine_citations: [
    {
      text:      'Anti-access/area-denial environments require distributed maritime operations and long-range precision fires to create dilemmas inside the adversary\'s engagement zone.',
      source:    'NDS 2022 · §III Maritime',
      relevance: 'BLUE standoff fires approach against A2/AD',
    },
    {
      text:      'The submarine force provides the most survivable long-range strike option and the primary tool for sea denial in contested straits.',
      source:    'NAVPLAN 2020 · §4.2 Undersea Warfare',
      relevance: 'SSN employment as decisive early asset',
    },
  ],
  generated_at:         '2026-04-25T17:41:00Z',
  generated_in_seconds: 31.7,
  run_id:               'BW-002',
}

// ── SCN-003: Broken City ──────────────────────────────────────────────────

const CITY_BLUE_UNITS: Unit[] = [
  u('MBT-001', 'Arleigh Burke DDG',        'Maritime Combat', 'Arleigh Burke DDG',           'Allied Fleet Anchorage',  1, 90),
  u('AIR-004', 'Apache Battalion',         'Air',             'AH-64E Apache Battalion',     'Coalition Forward Base',  1, 92),
  u('LI-001',  'Ranger Battalion',         'Light Infantry',  'US Ranger Battalion',          'Coalition Forward Base',  1, 95),
  u('AD-002',  'Patriot PAC-3 Battery',    'Air Defense',     'Patriot PAC-3 MSE Battery',   'Coalition Forward Base',  1, 85),
  u('SPE-001', 'Special Forces ODA',       'Special Ops',     'US Special Forces ODA',        'Coalition Forward Base',  2, 100),
  u('SPE-002', 'Cyber Operations Team',    'Special Ops',     'NSA Cyber Operations Team',   'Coalition Forward Base',  1, 100),
  u('IRR-001', 'Urban Resistance Cell',    'Irregular',       'Urban Resistance Cell',        'Coalition Forward Base',  2, 100),
]

const CITY_RED_UNITS: Unit[] = [
  u('MBT-005', 'Fast Attack Craft Swarm',  'Maritime Combat', 'IRGC Fast Attack Craft Swarm','Coastal Patrol Base',     2, 100),
  u('AIR-005', 'Shahed-136 Drone Swarm',   'Air',             'Shahed-136 Drone Swarm',       'Insurgent Safe Zone',     3, 100),
  u('LI-002',  'Quds Force Brigade',       'Light Infantry',  'Iranian Quds Force Brigade',   'Insurgent Safe Zone',     2, 90),
  u('ART-005', 'Fateh-110 Missile Battery','Artillery',       'Iranian Fateh-110 Battery',    'Insurgent Safe Zone',     2, 95),
  u('IRR-002', 'IED Network',              'Irregular',       'Insurgent IED Network',         'Insurgent Safe Zone',     3, 100),
  u('IRR-003', 'Proxy Militia Brigade',    'Irregular',       'Proxy Militia Brigade',         'Insurgent Safe Zone',     2, 90),
  u('SPE-005', 'MOIS HUMINT Cell',         'Special Ops',     'Iranian MOIS HUMINT Cell',      'Insurgent Safe Zone',     1, 100),
]

const CITY_BLUE: Force = { side: 'blue', name: 'Coalition Intervention Force (BLUE)', combat_power: 100, units: CITY_BLUE_UNITS }
const CITY_RED:  Force = { side: 'red',  name: 'Irregular Defense Force (RED_IRR)',    combat_power: 70,  units: CITY_RED_UNITS }

export const SCENARIO_BROKEN_CITY: Scenario = {
  id:                  'SCN-003',
  name:                'BROKEN CITY',
  classification:      'UNCLASSIFIED',
  threat_tier:         'asymmetric',
  scenario_type:       'URBAN',
  strategic_objective: 'DECAPITATION',
  summary:             'RED irregular and proxy forces seize port infrastructure and urban nodes in a contested coastal region. BLUE coalition forces respond to restore order and control. Urban combat, IED networks, drone swarms, and fast attack craft define the fight.',
  timeline_hours:      168,
  turns_total:         10,
  location: {
    name:          'Broken City',
    region:        'Urban / Coastal — port cities, chokepoints, urban nodes, infrastructure',
    country:       'Generic',
    bbox:          null,
    key_routes:    ['Central Port', 'Oil Terminal', 'Government District', 'Industrial Zone'],
    terrain_notes: 'Objective: Government District — Command Decapitation. SOF hold node for 3 consecutive turns.',
    pop_centers:   ['Central Port', 'Government District'],
  },
  nodes: {
    blue_land_entry:  'Coalition Forward Base',
    blue_sea_entry:   'Allied Fleet Anchorage',
    red_land_entry:   'Insurgent Safe Zone',
    red_sea_entry:    'Coastal Patrol Base',
    contested_nodes:  ['Central Port', 'Oil Terminal', 'Government District', 'Industrial Zone'],
    objective_node:   'Government District',
  },
  blue_force:    CITY_BLUE,
  red_force:     CITY_RED,
  blue_resources: { dollars_millions: 7000, income_per_turn_millions: 310, supply_chain: 76, stability: 65, intel: 30 },
  red_resources:  { dollars_millions: 3500, income_per_turn_millions: 180, supply_chain: 68, stability: 74, intel: 45 },
  victory_conditions: {
    blue: [
      'SOF asset holds Government District for 3 consecutive turns — Command Decapitation',
      'Avoid Economic Exhaustion, Supply Chain Collapse, Political Will Failure',
      'Avoid Proxy Exhaustion — all BLUE irregular assets destroyed',
      'Avoid Survival Failure — Coalition Forward Base falls',
    ],
    red: [
      'Trigger any BLUE loss condition',
      'RESOURCE_CONTROL — hold Oil Terminal + Central Port for 10 consecutive turns (secondary)',
    ],
  },
  available_modifiers: [
    { key: 'io_active',      label: 'RED IO campaign active',    description: 'Real-time propaganda degrades BLUE stability -5 per turn',         value: true,  default_value: true  },
    { key: 'partner_fragile',label: 'Partner force fragile',     description: 'Urban Resistance Cells require morale check each turn',              value: true,  default_value: true  },
    { key: 'hostages',       label: 'Civilian hostages present', description: 'ROE constraints on SOF and fires — direct action restricted',        value: false, default_value: false },
    { key: 'drone_saturation',label:'Drone saturation turn 1',   description: 'All 3 Drone Swarms active T+0 — BLUE AD immediately stressed',       value: false, default_value: false },
    { key: 'intel_advantage','label': 'HUMINT advantage (RED)',  description: 'RED HUMINT Cell reveals BLUE asset positions from turn 1',           value: false, default_value: false },
  ],
  active_modifier_keys: ['io_active', 'partner_fragile'],
  budget:             { label: 'Coalition Intervention Package', total: 7000, remaining: 7000, unit: '$M' },
  seed_events:        [],
  doctrine_citations: [
    {
      text:      'COIN operations require the host nation government to provide security, good governance, and development simultaneously to deny the insurgent legitimacy.',
      source:    'FM 3-24 · Counterinsurgency · §1.4',
      relevance: 'BLUE whole-of-government approach to Government District',
    },
    {
      text:      'Special operations forces provide the joint force commander a unique capability to conduct direct action against high-value targets in denied environments.',
      source:    'JP 3-05 · Special Operations · §II-8',
      relevance: 'SOF win-condition delivery path to Government District',
    },
  ],
  generated_at:         '2026-04-25T17:41:00Z',
  generated_in_seconds: 19.2,
  run_id:               'BC-003',
}

export const ALL_SCENARIOS: Scenario[] = [
  SCENARIO_IRON_CORRIDOR,
  SCENARIO_BLUE_WATER,
  SCENARIO_BROKEN_CITY,
]

// ── Completed AAR (Iron Corridor demo) ────────────────────────────────────

const IC_AAR: AAR = {
  outcome: {
    label:               'blue_win',
    summary:             'BLUE achieved 3 of 4 victory conditions. Junction Town held through turn 28; Northern Depot recaptured at turn 19 via HIMARS deep strike on RED logistics. Combat power retention 71% — above threshold. RED never achieved Economic Exhaustion trigger.',
    blue_cp_final:       71,
    red_cp_final:        29,
    max_penetration_km:  0,
    turns_played:        24,
    blue_conditions_met: 3,
    red_conditions_met:  1,
    conditions_total:    4,
  },
  key_turns:   [3, 7, 14, 19],
  lessons: [
    { category: 'strategic',   text: 'Income advantage from node control compounded after turn 12 — RED economic attrition was decisive before BTG attrition.' },
    { category: 'operational', text: 'HIMARS deep strike on Iskander reload cycle (turn 7) neutralised RED long-range fires for 6 turns — critical enabler.' },
    { category: 'tactical',    text: 'Holding Southern Depot with armored BCT anchored the defensive line and denied RED a southern flanking axis.' },
    { category: 'doctrinal',   text: 'Cyber team disruption of RED C2 at turn 3 delayed RED commitment of BTG #3 — information advantage front-loaded outcome.' },
    { category: 'cognitive',   text: 'BLUE maintained decisive-point discipline through turn 18 despite Northern Depot loss — no reactive overextension observed.' },
  ],
  recommendations: [
    { text: 'Re-run with RED reserves modifier active — three BTGs plus reserve tests BLUE armored BCT at decisive point.' },
    { text: 'Add supply chain pressure modifier to stress BLUE logistics after turn 15.' },
    { text: 'Test spring mud modifier — limits BTG armor speed and validates fires-centric approach without maneuver option.' },
    { text: 'Generate companion scenario with RED Iskander suppressed from turn 1 to isolate cyber effects on BLUE posture.' },
  ],
  doctrine_citations: [
    { text: 'Defending forces canalize the attacker into restrictive terrain to mass fires at decisive points while preserving combat power for the counter-attack.', source: 'FM 3-90 §3.4', relevance: 'turns 3–7 fires positioning' },
    { text: 'Resource control at key terrain features forces the attacker into predictable axes and degrades operational logistics.', source: 'FM 3-0 §3.1', relevance: 'Southern Depot hold decision' },
  ],
  generated_in_seconds: 11.2,
}

export const GAME_STATE_IN_PROGRESS: GameState = {
  scenario_id:        'SCN-001',
  run_id:             'IC-001',
  status:             'running',
  current_turn:       4,
  next_checkin_iso:   '2026-04-26T05:42:00Z',
  blue_force:         { ...IRON_BLUE, combat_power: 78 },
  red_force:          { ...IRON_RED,  combat_power: 64 },
  max_penetration_km: 14.2,
  turn_log: [
    {
      turn: 1, elapsed_hours: 6,
      blue_action_key: 'commit_reserve', blue_action_label: 'COMMIT RESERVE',
      blue_note: 'SOF ODA tasked to River Crossing recon',
      red_action_label: 'CYBER + ADVANCE',
      narrative: 'BLUE SOF confirmed RED main effort on primary axis. RED Cyber Team disrupted BLUE C2 for 3h but failed to achieve operational surprise. Northern Depot probe repelled.',
      blue_cp_after: 96, red_cp_after: 82, penetration_km_after: 4.0,
      doctrine_refs: ['JP 2-01 §III-7'],
    },
    {
      turn: 2, elapsed_hours: 12,
      blue_action_key: 'hold', blue_action_label: 'HOLD FORWARD',
      blue_note: '',
      red_action_label: 'ARMORED ADVANCE',
      narrative: 'BLUE armored BCT held Northern Depot approach. RED BTG #1 terrain-channeled at forest corridor. Attrition exchange favoring BLUE. HIMARS fired 2 missions.',
      blue_cp_after: 92, red_cp_after: 76, penetration_km_after: 8.1,
      doctrine_refs: ['FM 3-90 §3.4'],
    },
    {
      turn: 3, elapsed_hours: 18,
      blue_action_key: 'reorient_fires', blue_action_label: 'REORIENT FIRES',
      blue_note: 'HIMARS retasked from counter-battery to deep logistics strike',
      red_action_label: 'PRESS ON AXIS',
      narrative: 'BLUE HIMARS deep strike hit RED logistics column near Forward Staging Area. RED BTG #1 took 18% attrition in supply disruption. Iskander reload cycle disrupted. RED advance slowed.',
      blue_cp_after: 86, red_cp_after: 68, penetration_km_after: 11.4,
      doctrine_refs: ['FM 3-0 §5.3'],
    },
  ],
  pending_decision: GREY_HORIZON_DECISIONS[4],
  aar: null,
}

export const GAME_STATE_COMPLETED: GameState = {
  scenario_id:        'SCN-001',
  run_id:             'IC-001',
  status:             'ended',
  current_turn:       24,
  next_checkin_iso:   null,
  blue_force:         { ...IRON_BLUE, combat_power: 71 },
  red_force:          { ...IRON_RED,  combat_power: 29 },
  max_penetration_km: 0,
  turn_log: [
    ...GAME_STATE_IN_PROGRESS.turn_log,
    { turn: 4, elapsed_hours: 24, blue_action_key: 'reorient_fires', blue_action_label: 'REORIENT FIRES', blue_note: '', red_action_label: 'FLANK ATTEMPT', narrative: 'BLUE fires decisive at River Crossing. RED BTG #2 flank via forest blocked. HIMARS suppressed RED arty. Blue CP: 78, Red CP: 54.', blue_cp_after: 78, red_cp_after: 54, penetration_km_after: 14.2, doctrine_refs: ['FM 3-0 §5.3'] },
    { turn: 7, elapsed_hours: 42, blue_action_key: 'reorient_fires', blue_action_label: 'REORIENT FIRES', blue_note: 'HIMARS deep strike Iskander reload site', red_action_label: 'CONTINUE PUSH', narrative: 'HIMARS strike destroyed RED Iskander reload depot. RED long-range fires unavailable turns 7–13. RED operational tempo declining sharply.', blue_cp_after: 70, red_cp_after: 46, penetration_km_after: 14.2, doctrine_refs: ['FM 3-90 §3.4'] },
    { turn: 19, elapsed_hours: 114, blue_action_key: 'commit_reserve', blue_action_label: 'COMMIT RESERVE', blue_note: 'SOF + cyber enabled counterattack on Northern Depot', red_action_label: 'DEFEND DEPOT', narrative: 'BLUE SOF + Cyber disruption enabled armored counterattack. Northern Depot recaptured. RED BTG #3 at 20% strength. Economic attrition trigger approaching for RED.', blue_cp_after: 71, red_cp_after: 29, penetration_km_after: 0, doctrine_refs: ['JP 3-05 §II-8'] },
  ],
  pending_decision: null,
  aar: IC_AAR,
}
