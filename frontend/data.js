// Sample clustered build data. Shape your backend output to look like this.
//
// Per-node state shape:
//   { role: 'core',  pts, pickRate, rankDist? }   — taken by ~everyone in this cluster
//   { role: 'flex',  pts, pickRate, rankDist? }   — varies; doesn't change playstyle
//   omitted                                       — not taken in this cluster
//
// `pts` is the MODAL rank shown in the node body. For multi-rank talents,
// `rankDist` is an array of percentages (length = maxPoints) where rankDist[i]
// = % of cluster taking rank i+1. Sum should be ≤ pickRate. When rankDist
// is "split" (no single rank dominates), the node is marked rank-flex —
// statically taken but the rank itself is a flex point.
//
// `flexSlots` groups flex nodes that are alternatives to each other
// (you take ONE of the listed options).
//
// `pvp` declares the PvP talent picks for this cluster.
//   modal: top 3 most-picked PvP talent ids
//   dist:  pvpId → pickRate (% of cluster taking it)

window.PVP_POOL = [
  { id:'p1', name:'Counterspell Totem',  desc:'Placeholder: 3s silence on enemies hit. Interrupts a cast on activation.' },
  { id:'p2', name:'Grounding Field',     desc:'Placeholder: redirects the next harmful spell back to its caster.' },
  { id:'p3', name:'Sky Charge',          desc:'Placeholder: empowers party with movement speed and crit damage.' },
  { id:'p4', name:'Phantom Recovery',    desc:'Placeholder: heal increased while a defensive is active.' },
  { id:'p5', name:'Tidal Surge',         desc:'Placeholder: instant-cast a hard-cast heal once per cooldown.' },
  { id:'p6', name:'Static Coil',         desc:'Placeholder: stuns the target if they cast while debuffed.' },
  { id:'p7', name:'Discharge',           desc:'Placeholder: AoE knockback around the caster.' },
  { id:'p8', name:'Burrow',              desc:'Placeholder: short-duration immune root with self-damage.' },
  { id:'p9', name:'Power Spike',         desc:'Placeholder: 40% increased throughput for 8 seconds, 90s CD.' },
];

window.CLUSTER_DATA = {
  spec: { class: 'Shaman', spec: 'Restoration' },
  groupSizes: ['2v2', '3v3', 'Shuffle', 'RBG'],

  byGroup: {
    'Shuffle': {
      sampleSize: 4218,
      clusters: [
        {
          id: 'burst-control',
          name: 'Burst Control',
          pct: 38,
          sample: 1604,
          tagline: 'High-pressure setups around Ascendance windows. Trades sustain for CC density.',
          nodes: {
            c01:{role:'core',pts:1,pickRate:100}, c02:{role:'core',pts:1,pickRate:100},
            c03:{role:'core',pts:1,pickRate:99},  c05:{role:'core',pts:1,pickRate:98},
            c06:{role:'core',pts:1,pickRate:97},
            c07:{role:'core',pts:2,pickRate:96,rankDist:[14,82]},
            c08:{role:'flex',pts:1,pickRate:62,rankDist:[48,14]},
            c10:{role:'core',pts:1,pickRate:94},
            c11:{role:'flex',pts:1,pickRate:55},  c12:{role:'core',pts:1,pickRate:91},
            c13:{role:'core',pts:1,pickRate:89},  c14:{role:'core',pts:1,pickRate:100},
            c16:{role:'core',pts:1,pickRate:97},
            s01:{role:'core',pts:1,pickRate:100}, s02:{role:'core',pts:1,pickRate:100},
            s03:{role:'core',pts:1,pickRate:99},
            s04:{role:'flex',pts:1,pickRate:38,rankDist:[28,10]},
            s05:{role:'core',pts:1,pickRate:96},
            s06:{role:'core',pts:1,pickRate:95},  s07:{role:'flex',pts:1,pickRate:71},
            s08:{role:'core',pts:1,pickRate:93},  s10:{role:'core',pts:1,pickRate:91},
            s11:{role:'flex',pts:1,pickRate:48},
            s13:{role:'core',pts:2,pickRate:88,rankDist:[12,76]},
            s14:{role:'core',pts:1,pickRate:100}, s16:{role:'core',pts:1,pickRate:84},
          },
          flexSlots: [
            { id:'cls-row3', label:'Row 3 utility',     options:['c08','c11'] },
            { id:'spec-r3',  label:'Tank pivot',        options:['s07','s11'] },
          ],
          pvp: {
            modal: ['p1','p3','p6'],
            dist:  { p1:94, p3:81, p6:78, p2:38, p9:18, p4:14, p5:9, p7:6, p8:4 },
          },
          buildString: 'CkXcGZ4hKtP7yQ2vN8m1wRpFb3sLjA9eHdVu0YxIoTaW',
        },
        {
          id: 'sustained',
          name: 'Sustained Throughput',
          pct: 27,
          sample: 1138,
          tagline: 'Long-fight HPS optimized. Heavier Cloudburst and Wellspring stacking.',
          nodes: {
            c01:{role:'core',pts:1,pickRate:100}, c02:{role:'core',pts:1,pickRate:99},
            c03:{role:'core',pts:1,pickRate:100}, c04:{role:'flex',pts:1,pickRate:68},
            c05:{role:'core',pts:1,pickRate:95},
            c07:{role:'core',pts:2,pickRate:97,rankDist:[38,59]},
            c09:{role:'flex',pts:1,pickRate:54},  c10:{role:'core',pts:1,pickRate:92},
            c12:{role:'core',pts:1,pickRate:88},  c14:{role:'core',pts:1,pickRate:100},
            c15:{role:'core',pts:1,pickRate:91},
            s01:{role:'core',pts:1,pickRate:100}, s02:{role:'core',pts:1,pickRate:100},
            s03:{role:'core',pts:1,pickRate:100},
            s04:{role:'core',pts:2,pickRate:98,rankDist:[8,90]},
            s05:{role:'core',pts:1,pickRate:97},  s06:{role:'core',pts:1,pickRate:96},
            s08:{role:'core',pts:1,pickRate:90},  s10:{role:'core',pts:1,pickRate:95},
            s12:{role:'core',pts:2,pickRate:93,rankDist:[36,57]},
            s13:{role:'flex',pts:1,pickRate:42,rankDist:[30,12]},
            s14:{role:'core',pts:1,pickRate:100}, s15:{role:'core',pts:1,pickRate:79},
          },
          flexSlots: [
            { id:'cls-r2', label:'Row 2 mobility/utility', options:['c04','c09'] },
            { id:'spec-r5', label:'Last row HoT split',    options:['s13','s12'] },
          ],
          pvp: {
            modal: ['p4','p5','p9'],
            dist:  { p4:88, p5:84, p9:71, p2:46, p1:31, p3:18, p6:12, p7:7, p8:3 },
          },
          buildString: 'PqM2nXvR8tL4kY6jW3cBhFs0aD9zE7uI1oG5HbVrNxTy',
        },
        {
          id: 'defensive',
          name: 'Defensive Pivot',
          pct: 18,
          sample: 760,
          tagline: 'Stoneskin + Astral Shift line. Built to survive double-melee pressure.',
          nodes: {
            c01:{role:'core',pts:1,pickRate:100}, c02:{role:'core',pts:1,pickRate:100},
            c03:{role:'core',pts:1,pickRate:100}, c04:{role:'core',pts:1,pickRate:92},
            c05:{role:'core',pts:1,pickRate:94},
            c07:{role:'core',pts:2,pickRate:100,rankDist:[4,96]},
            c08:{role:'core',pts:2,pickRate:98,rankDist:[18,80]},
            c10:{role:'core',pts:1,pickRate:88},
            c12:{role:'core',pts:1,pickRate:96},  c13:{role:'flex',pts:1,pickRate:51},
            c14:{role:'core',pts:1,pickRate:100}, c15:{role:'flex',pts:1,pickRate:58},
            s01:{role:'core',pts:1,pickRate:100}, s02:{role:'core',pts:1,pickRate:100},
            s03:{role:'core',pts:1,pickRate:97},
            s04:{role:'core',pts:2,pickRate:91,rankDist:[42,49]},
            s05:{role:'core',pts:1,pickRate:93},  s08:{role:'core',pts:1,pickRate:96},
            s10:{role:'core',pts:1,pickRate:89},  s11:{role:'core',pts:1,pickRate:82},
            s13:{role:'core',pts:2,pickRate:90,rankDist:[6,84]},
            s14:{role:'core',pts:1,pickRate:100},
            s16:{role:'flex',pts:1,pickRate:46},
          },
          flexSlots: [
            { id:'cls-r5', label:'Row 5 totem swap',  options:['c12','c13'] },
            { id:'cls-r7', label:'Capstone follow',   options:['c15','c16'] },
            { id:'spec-r7', label:'Closer talent',    options:['s15','s16'] },
          ],
          pvp: {
            modal: ['p2','p4','p8'],
            dist:  { p2:93, p4:88, p8:76, p1:42, p6:33, p5:20, p9:11, p3:7, p7:4 },
          },
          buildString: 'B8jK3tR5pXmQ7nL2vW4cYsHdFa6zE0iU9oG1bVrNxTyM',
        },
        {
          id: 'mobility',
          name: 'Mobility Specialist',
          pct: 11,
          sample: 464,
          tagline: 'Spirit Walk + Wind Rush kiting build. Niche vs heavy melee comps.',
          nodes: {
            c01:{role:'core',pts:1,pickRate:100}, c02:{role:'core',pts:1,pickRate:100},
            c03:{role:'core',pts:1,pickRate:96},  c04:{role:'core',pts:1,pickRate:100},
            c05:{role:'core',pts:1,pickRate:88},
            c07:{role:'core',pts:1,pickRate:79,rankDist:[64,15]},
            c09:{role:'core',pts:1,pickRate:87},  c10:{role:'core',pts:1,pickRate:91},
            c12:{role:'core',pts:1,pickRate:94},  c14:{role:'core',pts:1,pickRate:100},
            c15:{role:'flex',pts:1,pickRate:53},
            s01:{role:'core',pts:1,pickRate:100}, s02:{role:'core',pts:1,pickRate:100},
            s03:{role:'core',pts:1,pickRate:94},  s05:{role:'core',pts:1,pickRate:90},
            s06:{role:'core',pts:1,pickRate:88},  s07:{role:'core',pts:1,pickRate:85},
            s10:{role:'core',pts:1,pickRate:86},
            s12:{role:'core',pts:1,pickRate:80,rankDist:[71,9]},
            s14:{role:'core',pts:1,pickRate:100}, s15:{role:'core',pts:1,pickRate:78},
          },
          flexSlots: [
            { id:'cls-r7', label:'Capstone follow',   options:['c15','c16'] },
          ],
          pvp: {
            modal: ['p3','p8','p1'],
            dist:  { p3:91, p8:84, p1:78, p2:31, p6:24, p4:14, p9:8, p5:5, p7:3 },
          },
          buildString: 'Mq4Lj2Xk8Vr5Tn3Bp9YcHsFdA1zE6uI0oG7HbWrNxKyP',
        },
        {
          id: 'hybrid',
          name: 'Off-meta Hybrid',
          pct: 6,
          sample: 252,
          tagline: 'Experimental mixed line. Low sample — proceed with caution.',
          nodes: {
            c01:{role:'core',pts:1,pickRate:100}, c02:{role:'flex',pts:1,pickRate:62},
            c03:{role:'core',pts:1,pickRate:91},  c05:{role:'core',pts:1,pickRate:84},
            c06:{role:'flex',pts:1,pickRate:51},
            c07:{role:'core',pts:1,pickRate:73,rankDist:[40,33]},
            c08:{role:'flex',pts:1,pickRate:48,rankDist:[28,20]},
            c10:{role:'core',pts:1,pickRate:80},
            c11:{role:'flex',pts:1,pickRate:45},  c12:{role:'core',pts:1,pickRate:82},
            c14:{role:'core',pts:1,pickRate:100}, c15:{role:'flex',pts:1,pickRate:50},
            c16:{role:'flex',pts:1,pickRate:50},
            s01:{role:'core',pts:1,pickRate:100}, s02:{role:'core',pts:1,pickRate:100},
            s05:{role:'core',pts:1,pickRate:78},  s06:{role:'flex',pts:1,pickRate:60},
            s07:{role:'flex',pts:1,pickRate:55},  s08:{role:'core',pts:1,pickRate:81},
            s10:{role:'core',pts:1,pickRate:83},
            s12:{role:'flex',pts:1,pickRate:48,rankDist:[26,22]},
            s13:{role:'flex',pts:1,pickRate:44,rankDist:[24,20]},
            s14:{role:'core',pts:1,pickRate:100},
            s16:{role:'flex',pts:1,pickRate:52},
          },
          flexSlots: [
            { id:'cls-r1', label:'Opener',           options:['c02','c03'] },
            { id:'cls-r3', label:'Row 3 utility',    options:['c07','c08'] },
            { id:'cls-r7', label:'Capstone follow',  options:['c15','c16'] },
            { id:'spec-r3', label:'Tank pivot',      options:['s07','s08'] },
            { id:'spec-r5', label:'Last row',        options:['s12','s13'] },
          ],
          pvp: {
            modal: ['p9','p2','p5'],
            dist:  { p9:62, p2:58, p5:54, p1:46, p4:38, p3:31, p6:25, p7:18, p8:12 },
          },
          buildString: 'Xq7Mj1Lk3Vr2Tn5Bp8YcHsFdA9zE4uI6oG0HbWrNcKyQ',
        },
      ],
    },
  },
};

// Mirror the same clusters for the other group sizes with slight pct/sample variations
// so the filter feels live. In production each group size has its own clustering result.
['2v2','3v3','RBG'].forEach((g, i) => {
  const offset = [-3, +2, -5][i];
  window.CLUSTER_DATA.byGroup[g] = {
    sampleSize: Math.round(4218 * (0.45 + i * 0.18)),
    clusters: window.CLUSTER_DATA.byGroup.Shuffle.clusters.map((c, idx) => ({
      ...c,
      pct: Math.max(3, c.pct + offset + (idx === 0 ? -i : i)),
      sample: Math.round(c.sample * (0.45 + i * 0.18)),
    })),
  };
});
