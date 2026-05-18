// === Backend data shape ===
//
// Matches the real summarize_talent_clusters() backend output for one bracket.
// Replace this object with the response from get_full_summary(spec, bracket).
//
//   spec, bracket, sample_size, avg_ilvl
//   specLabel: { class, spec }            ← derived from spec string
//   pvp_talents:  [{ id, name, pct }]     ← global, not per-cluster
//   talents:
//     core:       [{ id, name, pct }]     ← taken by ~all players
//     flex:       [{ id, name, pct }]     ← rarely taken, varies
//     contested:  [{ id, name, pct }]     ← cluster-defining
//   clusters: [{
//     rank, pct, count, canonical_code,
//     takes: [{ id, name, pct }]          ← contested talents THIS cluster takes
//     skips: [{ id, name, pct }]          ← contested talents THIS cluster skips
//   }]
//   gear: {
//     avg_ilvl,
//     slots: [{ slot, item: { id, name, pct }, enchant?: { name, pct } }]
//   }
//
// `id` on talent nodes is a tree-node id matching tree-data.js.
// Real WoW talent IDs (e.g. 81018) need mapping to tree positions (c01, s01…).

window.CLUSTER_DATA = {
  spec: "restoration-shaman",
  specLabel: { class: "Shaman", spec: "Restoration" },
  bracket: "3v3",
  sample_size: 50,
  avg_ilvl: 248,

  pvp_talents: [
    { id: "p1", name: "Grounding Totem", pct: 92 },
    { id: "p2", name: "Rain Dance", pct: 80 },
    { id: "p3", name: "Static Field Totem", pct: 40 },
    { id: "p4", name: "Storm Conduit", pct: 38 },
    { id: "p5", name: "Lightning Lasso", pct: 38 },
    { id: "p6", name: "Spectral Recovery", pct: 22 },
    { id: "p7", name: "Burrow", pct: 14 },
    { id: "p8", name: "Counterstrike Totem", pct: 8 },
  ],

  talents: {
    core: [
      { id: "s01", name: "Living Stream", pct: 100 },
      { id: "s02", name: "Riptide", pct: 100 },
      { id: "s05", name: "Deluge", pct: 100 },
      { id: "s08", name: "Spirit Link Totem", pct: 100 },
      { id: "s04", name: "Tidal Waves", pct: 98 },
      { id: "c01", name: "Elemental Focus", pct: 100 },
      { id: "c02", name: "Wind Rush", pct: 100 },
      { id: "c05", name: "Totemic Resonance", pct: 96 },
      { id: "s14", name: "Ancestral Guidance", pct: 100 },
      { id: "c14", name: "Ascendance", pct: 100 },
      { id: "s03", name: "Chain Heal", pct: 99 },
    ],
    flex: [
      { id: "s16", name: "Overflowing Shores", pct: 18 },
      { id: "s15", name: "Rip Current", pct: 14 },
    ],
    contested: [
      { id: "s13", name: "Acid Rain", pct: 66 },
      { id: "s06", name: "Brimming with Life", pct: 76 },
      { id: "s11", name: "Windveil", pct: 74 },
      { id: "s07", name: "Soothing Rain", pct: 58 },
      { id: "c07", name: "Resurgence", pct: 34 },
      { id: "c08", name: "Refreshing Waters", pct: 42 },
      { id: "c10", name: "Voodoo Mastery", pct: 42 },
      { id: "c11", name: "Current Control", pct: 28 },
      { id: "c03", name: "Ancestral Awakening", pct: 32 },
    ],
  },

  clusters: [
    {
      rank: 1,
      pct: 22,
      count: 11,
      canonical_code: "CgQARUG2fGwHkLP0T7/MoTNl/AAAAAEZHghYYkZbmtZWkZ20MzMb",
      takes: [
        { id: "s13", name: "Acid Rain", pct: 66 },
        { id: "s07", name: "Soothing Rain", pct: 58 },
        { id: "s06", name: "Brimming with Life", pct: 76 },
        { id: "s11", name: "Windveil", pct: 74 },
        { id: "c08", name: "Refreshing Waters", pct: 42 },
      ],
      skips: [
        { id: "c07", name: "Resurgence", pct: 34 },
        { id: "c11", name: "Current Control", pct: 28 },
        { id: "c10", name: "Voodoo Mastery", pct: 42 },
        { id: "c03", name: "Ancestral Awakening", pct: 32 },
      ],
    },
    {
      rank: 2,
      pct: 16,
      count: 8,
      canonical_code: "CgQARUG2fGwHkLP0T7/MoTNl/BBBBBkZHghYYkZbmtZWkZ20MzMb",
      takes: [
        { id: "s13", name: "Acid Rain", pct: 66 },
        { id: "c03", name: "Ancestral Awakening", pct: 32 },
        { id: "s11", name: "Windveil", pct: 74 },
        { id: "s06", name: "Brimming with Life", pct: 76 },
      ],
      skips: [
        { id: "s07", name: "Soothing Rain", pct: 58 },
        { id: "c08", name: "Refreshing Waters", pct: 42 },
        { id: "c11", name: "Current Control", pct: 28 },
        { id: "c10", name: "Voodoo Mastery", pct: 42 },
        { id: "c07", name: "Resurgence", pct: 34 },
      ],
    },
    {
      rank: 3,
      pct: 14,
      count: 7,
      canonical_code: "CgQARUG2fGwHkLP0T7/MoTNl/CCCCC2dHghYYkZbmtZWkZ20MzMb",
      takes: [
        { id: "s06", name: "Brimming with Life", pct: 76 },
        { id: "s11", name: "Windveil", pct: 74 },
        { id: "c07", name: "Resurgence", pct: 34 },
        { id: "c10", name: "Voodoo Mastery", pct: 42 },
      ],
      skips: [
        { id: "s13", name: "Acid Rain", pct: 66 },
        { id: "s07", name: "Soothing Rain", pct: 58 },
        { id: "c08", name: "Refreshing Waters", pct: 42 },
        { id: "c11", name: "Current Control", pct: 28 },
        { id: "c03", name: "Ancestral Awakening", pct: 32 },
      ],
    },
    {
      rank: 4,
      pct: 12,
      count: 6,
      canonical_code: "CgQARUG2fGwHkLP0T7/MoTNl/DDDDDQfHghYYkZbmtZWkZ20MzMb",
      takes: [
        { id: "s06", name: "Brimming with Life", pct: 76 },
        { id: "c08", name: "Refreshing Waters", pct: 42 },
        { id: "c11", name: "Current Control", pct: 28 },
        { id: "s11", name: "Windveil", pct: 74 },
      ],
      skips: [
        { id: "s13", name: "Acid Rain", pct: 66 },
        { id: "s07", name: "Soothing Rain", pct: 58 },
        { id: "c10", name: "Voodoo Mastery", pct: 42 },
        { id: "c03", name: "Ancestral Awakening", pct: 32 },
        { id: "c07", name: "Resurgence", pct: 34 },
      ],
    },
    {
      rank: 5,
      pct: 10,
      count: 5,
      canonical_code: "CgQARUG2fGwHkLP0T7/MoTNl/EEEEE9hHghYYkZbmtZWkZ20MzMb",
      takes: [
        { id: "s13", name: "Acid Rain", pct: 66 },
        { id: "c10", name: "Voodoo Mastery", pct: 42 },
        { id: "c03", name: "Ancestral Awakening", pct: 32 },
        { id: "s11", name: "Windveil", pct: 74 },
        { id: "s06", name: "Brimming with Life", pct: 76 },
      ],
      skips: [
        { id: "s07", name: "Soothing Rain", pct: 58 },
        { id: "c08", name: "Refreshing Waters", pct: 42 },
        { id: "c11", name: "Current Control", pct: 28 },
        { id: "c07", name: "Resurgence", pct: 34 },
      ],
    },
  ],

  gear: {
    avg_ilvl: 248,
    slots: [
      {
        slot: "Head",
        item: { id: 249979, name: "Locus of the Primal Core", pct: 90 },
        enchant: { name: "Empowered Blessing of Speed", pct: 52 },
      },
      {
        slot: "Neck",
        item: { id: 240952, name: "Thalassian Competitor's Amulet", pct: 78 },
      },
      {
        slot: "Shoulder",
        item: { id: 249977, name: "Tempests of the Primal Core", pct: 46 },
        enchant: { name: "Akil'zon's Swiftness", pct: 70 },
      },
      {
        slot: "Back",
        item: { id: 255548, name: "Galactic Gladiator's Shawl", pct: 60 },
        enchant: { name: "Chant of Winged Grace", pct: 71 },
      },
      {
        slot: "Chest",
        item: { id: 249982, name: "Embrace of the Primal Core", pct: 94 },
        enchant: { name: "Mark of the Magister", pct: 90 },
      },
      {
        slot: "Wrist",
        item: {
          id: 255544,
          name: "Galactic Gladiator's Chain Wristguards",
          pct: 52,
        },
        enchant: { name: "Chant of Armored Avoidance", pct: 54 },
      },
      {
        slot: "Hands",
        item: { id: 249980, name: "Earthgrips of the Primal Core", pct: 92 },
      },
      {
        slot: "Waist",
        item: {
          id: 244565,
          name: "Thalassian Competitor's Chain Girdle",
          pct: 78,
        },
      },
      {
        slot: "Legs",
        item: { id: 249978, name: "Leggings of the Primal Core", pct: 64 },
        enchant: { name: "Roiling Spellthread", pct: 88 },
      },
      {
        slot: "Feet",
        item: { id: 255533, name: "Galactic Gladiator's Chain Boots", pct: 54 },
        enchant: { name: "Farstrider's Hunt", pct: 76 },
      },
      {
        slot: "Ring 1",
        item: { id: 240951, name: "Thalassian Competitor's Signet", pct: 82 },
        enchant: { name: "Zul'jin's Mastery", pct: 70 },
      },
      {
        slot: "Ring 2",
        item: { id: 240951, name: "Thalassian Competitor's Signet", pct: 76 },
        enchant: { name: "Zul'jin's Mastery", pct: 74 },
      },
      {
        slot: "Trinket 1",
        item: {
          id: 255614,
          name: "Galactic Gladiator's Insignia of Alacrity",
          pct: 54,
        },
      },
      {
        slot: "Trinket 2",
        item: { id: 255616, name: "Galactic Gladiator's Medallion", pct: 56 },
      },
      {
        slot: "Weapon",
        item: { id: 255624, name: "Galactic Gladiator's Scepter", pct: 86 },
        enchant: { name: "Acuity of the Ren'dorei", pct: 92 },
      },
      {
        slot: "Off-hand",
        item: { id: 255632, name: "Galactic Gladiator's Bulwark", pct: 86 },
      },
    ],
  },
};
