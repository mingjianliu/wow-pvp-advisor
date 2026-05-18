// === Backend data shape ===
//
// Matches the real summarize_talent_clusters() backend output:
//
//   spec, bracket, sample_size, avg_ilvl
//   pvp_talents:  [{ id, name, pct }]                  ← global, not per-cluster
//   talents:
//     core:       [{ id, name, pct }]                  ← taken by ~all players
//     flex:       [{ id, name, pct }]                  ← rarely taken, varies
//     contested:  [{ id, name, pct }]                  ← cluster-defining
//   clusters: [{
//     rank, pct, count, canonical_code,
//     takes: [{ id, name, pct }]                       ← contested talents THIS cluster takes
//     skips: [{ id, name, pct }]                       ← contested talents THIS cluster skips
//   }]
//
// `id` is a tree-node id — match it to the entries in tree-data.js.
// Real WoW talent IDs (e.g. 81018) can be remapped to tree positions when
// you wire the backend in; here we use synthetic `c01`/`s01` ids that match
// the placeholder tree layout.

window.CLUSTER_DATA = {
  spec: 'restoration-shaman',
  specLabel: { class: 'Shaman', spec: 'Restoration' },
  brackets: ['2v2', '3v3', 'Shuffle', 'RBG'],

  byBracket: {
    '3v3': {
      sample_size: 50,
      avg_ilvl: 248,

      pvp_talents: [
        { id: 'p1', name: 'Grounding Totem',     pct: 92 },
        { id: 'p2', name: 'Rain Dance',          pct: 80 },
        { id: 'p3', name: 'Static Field Totem',  pct: 40 },
        { id: 'p4', name: 'Storm Conduit',       pct: 38 },
        { id: 'p5', name: 'Lightning Lasso',     pct: 38 },
        { id: 'p6', name: 'Spectral Recovery',   pct: 22 },
        { id: 'p7', name: 'Burrow',              pct: 14 },
        { id: 'p8', name: 'Counterstrike Totem', pct: 8  },
      ],

      talents: {
        core: [
          { id: 's01', name: 'Living Stream',       pct: 100 },
          { id: 's02', name: 'Riptide',             pct: 100 },
          { id: 's05', name: 'Deluge',              pct: 100 },
          { id: 's08', name: 'Spirit Link Totem',   pct: 100 },
          { id: 's04', name: 'Tidal Waves',         pct: 98  },
          { id: 'c01', name: 'Elemental Focus',     pct: 100 },
          { id: 'c02', name: 'Wind Rush',           pct: 100 },
          { id: 'c05', name: 'Totemic Resonance',   pct: 96  },
          { id: 's14', name: 'Ancestral Guidance',  pct: 100 },
          { id: 'c14', name: 'Ascendance',          pct: 100 },
          { id: 's03', name: 'Chain Heal',          pct: 99  },
          { id: 'h01', name: 'Call of the Ancestors', pct: 100 },
          { id: 'h04', name: 'Routine Communion',     pct: 96  },
          { id: 'h07', name: 'Primordial Capacity',   pct: 98  },
          { id: 'h09', name: 'Final Calling',         pct: 100 },
        ],
        flex: [
          { id: 's16', name: 'Overflowing Shores',  pct: 18 },
          { id: 's15', name: 'Rip Current',         pct: 14 },
          { id: 'h05', name: 'Heed My Call',        pct: 12 },
        ],
        contested: [
          { id: 's13', name: 'Acid Rain',           pct: 66 },
          { id: 's06', name: 'Brimming with Life',  pct: 76 },
          { id: 's11', name: 'Windveil',            pct: 74 },
          { id: 's07', name: 'Soothing Rain',       pct: 58 },
          { id: 'c07', name: 'Resurgence',          pct: 34 },
          { id: 'c08', name: 'Refreshing Waters',   pct: 42 },
          { id: 'c10', name: 'Voodoo Mastery',      pct: 42 },
          { id: 'c11', name: 'Current Control',     pct: 28 },
          { id: 'c03', name: 'Ancestral Awakening', pct: 32 },
          { id: 'h02', name: 'Latent Wisdom',       pct: 54 },
          { id: 'h03', name: 'Ancient Fellowship',  pct: 46 },
          { id: 'h06', name: 'Offering from Beyond',pct: 62 },
          { id: 'h08', name: 'Maelstrom Supremacy', pct: 48 },
          { id: 'h10', name: 'Earthen Communion',   pct: 52 },
        ],
      },

      clusters: [
        {
          rank: 1, pct: 22, count: 11,
          canonical_code: 'CgQARUG2fGwHkLP0T7/MoTNl/AAAAAEZHghYYkZbmtZWkZ20MzMb',
          takes: [
            { id: 's13', name: 'Acid Rain',           pct: 66 },
            { id: 's07', name: 'Soothing Rain',       pct: 58 },
            { id: 's06', name: 'Brimming with Life',  pct: 76 },
            { id: 's11', name: 'Windveil',            pct: 74 },
            { id: 'c08', name: 'Refreshing Waters',   pct: 42 },
            { id: 'h06', name: 'Offering from Beyond',pct: 62 },
            { id: 'h10', name: 'Earthen Communion',   pct: 52 },
          ],
          skips: [
            { id: 'c07', name: 'Resurgence',          pct: 34 },
            { id: 'c11', name: 'Current Control',     pct: 28 },
            { id: 'c10', name: 'Voodoo Mastery',      pct: 42 },
            { id: 'c03', name: 'Ancestral Awakening', pct: 32 },
            { id: 'h02', name: 'Latent Wisdom',       pct: 54 },
            { id: 'h08', name: 'Maelstrom Supremacy', pct: 48 },
          ],
        },
        {
          rank: 2, pct: 16, count: 8,
          canonical_code: 'CgQARUG2fGwHkLP0T7/MoTNl/BBBBBkZHghYYkZbmtZWkZ20MzMb',
          takes: [
            { id: 's13', name: 'Acid Rain',           pct: 66 },
            { id: 'c03', name: 'Ancestral Awakening', pct: 32 },
            { id: 's11', name: 'Windveil',            pct: 74 },
            { id: 's06', name: 'Brimming with Life',  pct: 76 },
            { id: 'h02', name: 'Latent Wisdom',       pct: 54 },
            { id: 'h06', name: 'Offering from Beyond',pct: 62 },
          ],
          skips: [
            { id: 's07', name: 'Soothing Rain',       pct: 58 },
            { id: 'c08', name: 'Refreshing Waters',   pct: 42 },
            { id: 'c11', name: 'Current Control',     pct: 28 },
            { id: 'c10', name: 'Voodoo Mastery',      pct: 42 },
            { id: 'c07', name: 'Resurgence',          pct: 34 },
            { id: 'h03', name: 'Ancient Fellowship',  pct: 46 },
          ],
        },
        {
          rank: 3, pct: 14, count: 7,
          canonical_code: 'CgQARUG2fGwHkLP0T7/MoTNl/CCCCC2dHghYYkZbmtZWkZ20MzMb',
          takes: [
            { id: 's06', name: 'Brimming with Life',  pct: 76 },
            { id: 's11', name: 'Windveil',            pct: 74 },
            { id: 'c07', name: 'Resurgence',          pct: 34 },
            { id: 'c10', name: 'Voodoo Mastery',      pct: 42 },
            { id: 'h03', name: 'Ancient Fellowship',  pct: 46 },
            { id: 'h08', name: 'Maelstrom Supremacy', pct: 48 },
          ],
          skips: [
            { id: 's13', name: 'Acid Rain',           pct: 66 },
            { id: 's07', name: 'Soothing Rain',       pct: 58 },
            { id: 'c08', name: 'Refreshing Waters',   pct: 42 },
            { id: 'c11', name: 'Current Control',     pct: 28 },
            { id: 'c03', name: 'Ancestral Awakening', pct: 32 },
            { id: 'h06', name: 'Offering from Beyond',pct: 62 },
          ],
        },
        {
          rank: 4, pct: 12, count: 6,
          canonical_code: 'CgQARUG2fGwHkLP0T7/MoTNl/DDDDDQfHghYYkZbmtZWkZ20MzMb',
          takes: [
            { id: 's06', name: 'Brimming with Life',  pct: 76 },
            { id: 'c08', name: 'Refreshing Waters',   pct: 42 },
            { id: 'c11', name: 'Current Control',     pct: 28 },
            { id: 's11', name: 'Windveil',            pct: 74 },
            { id: 'h02', name: 'Latent Wisdom',       pct: 54 },
            { id: 'h10', name: 'Earthen Communion',   pct: 52 },
          ],
          skips: [
            { id: 's13', name: 'Acid Rain',           pct: 66 },
            { id: 's07', name: 'Soothing Rain',       pct: 58 },
            { id: 'c10', name: 'Voodoo Mastery',      pct: 42 },
            { id: 'c03', name: 'Ancestral Awakening', pct: 32 },
            { id: 'c07', name: 'Resurgence',          pct: 34 },
            { id: 'h08', name: 'Maelstrom Supremacy', pct: 48 },
          ],
        },
        {
          rank: 5, pct: 10, count: 5,
          canonical_code: 'CgQARUG2fGwHkLP0T7/MoTNl/EEEEE9hHghYYkZbmtZWkZ20MzMb',
          takes: [
            { id: 's13', name: 'Acid Rain',           pct: 66 },
            { id: 'c10', name: 'Voodoo Mastery',      pct: 42 },
            { id: 'c03', name: 'Ancestral Awakening', pct: 32 },
            { id: 's11', name: 'Windveil',            pct: 74 },
            { id: 's06', name: 'Brimming with Life',  pct: 76 },
            { id: 'h06', name: 'Offering from Beyond',pct: 62 },
            { id: 'h08', name: 'Maelstrom Supremacy', pct: 48 },
          ],
          skips: [
            { id: 's07', name: 'Soothing Rain',       pct: 58 },
            { id: 'c08', name: 'Refreshing Waters',   pct: 42 },
            { id: 'c11', name: 'Current Control',     pct: 28 },
            { id: 'c07', name: 'Resurgence',          pct: 34 },
            { id: 'h02', name: 'Latent Wisdom',       pct: 54 },
          ],
        },
      ],

      // Gear summary — per-slot top item + top enchant. Backend can produce
      // this from the full gear+enchants data. Slots without a meaningful
      // enchant (neck, trinkets, rings already enchanted on the embed slot,
      // etc.) omit the `enchant` field.
      gear: {
        avg_ilvl: 248,
        slots: [
          { slot: 'Head',     item: { name: "Crown of the Tideborne",          pct: 78 }, enchant: { name: 'Sacred Stat — Versatility', pct: 64 } },
          { slot: 'Neck',     item: { name: "Tideborne Choker",                pct: 72 } },
          { slot: 'Shoulder', item: { name: "Pauldrons of the Murkbreaker",    pct: 70 }, enchant: { name: 'Whisper of the Vow',        pct: 58 } },
          { slot: 'Back',     item: { name: "Cloak of the Sunken King",        pct: 66 }, enchant: { name: 'Chant of Winged Grace',     pct: 71 } },
          { slot: 'Chest',    item: { name: "Robes of the Drowned Saint",      pct: 74 }, enchant: { name: 'Crystalline Radiance',      pct: 68 } },
          { slot: 'Wrist',    item: { name: "Bracers of the Brinekeeper",      pct: 62 }, enchant: { name: 'Chant of Armored Avoidance', pct: 54 } },
          { slot: 'Hands',    item: { name: "Gloves of the Hollow Tide",       pct: 68 }, enchant: { name: 'Chant of Burrowing Rapidity', pct: 49 } },
          { slot: 'Waist',    item: { name: "Belt of the Salt-Cured",          pct: 60 } },
          { slot: 'Legs',     item: { name: "Greaves of the Sea-Wraith",       pct: 72 }, enchant: { name: 'Roiling Spellthread',       pct: 76 } },
          { slot: 'Feet',     item: { name: "Sandals of the Drowned Pilgrim",  pct: 64 }, enchant: { name: 'Cavalry\'s March',          pct: 55 } },
          { slot: 'Ring 1',   item: { name: "Signet of the Tideborne",         pct: 56 }, enchant: { name: 'Cursed Versatility',        pct: 70 } },
          { slot: 'Ring 2',   item: { name: "Band of the Crystal Vault",       pct: 48 }, enchant: { name: 'Cursed Critical Strike',    pct: 52 } },
          { slot: 'Trinket 1',item: { name: "Algeth'ar Puzzle Box",            pct: 64 } },
          { slot: 'Trinket 2',item: { name: "Voice of the Silent Star",        pct: 58 } },
          { slot: 'Weapon',   item: { name: "Voice of the Silent Star",        pct: 58 }, enchant: { name: 'Authority of Storms',       pct: 81 } },
          { slot: 'Off-hand', item: { name: "Drape of the Murkbreaker",        pct: 54 } },
        ],
      },
    },
  },
};

// Mirror the bracket data with slight variations so the filter feels live.
['2v2', 'Shuffle', 'RBG'].forEach((b, i) => {
  const src = window.CLUSTER_DATA.byBracket['3v3'];
  const sizeMul = [0.7, 1.4, 0.5][i];
  const offsetClusters = [-1, +2, -2][i];
  window.CLUSTER_DATA.byBracket[b] = {
    ...src,
    sample_size: Math.round(src.sample_size * sizeMul),
    avg_ilvl: src.avg_ilvl + [-2, +3, -5][i],
    clusters: src.clusters.map((c, idx) => ({
      ...c,
      pct: Math.max(2, c.pct + offsetClusters + (idx === 0 ? -i : 0)),
      count: Math.max(1, Math.round(c.count * sizeMul)),
    })),
  };
});
