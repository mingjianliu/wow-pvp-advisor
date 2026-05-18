// Placeholder talent tree shape — two side-by-side trees (Class + Spec).
// Replace `name`/`desc` strings and add nodes when you wire real data in.
//
// Each node: { id, name, desc, type: 'circle'|'diamond'|'capstone', maxPoints, col, row }
// `diamond` nodes are choice nodes (the player picks one of two effects).
// `capstone` nodes render as large diamonds.

window.TREE = (function () {
  const placeholderDesc = (n) =>
    `Placeholder description for ${n}. Replace with the talent's tooltip text from your data source.`;

  function n(id, name, opts = {}) {
    return {
      id,
      name,
      desc: opts.desc || placeholderDesc(name),
      type: opts.type || 'circle',
      maxPoints: opts.maxPoints || 1,
      col: opts.col,
      row: opts.row,
    };
  }

  // Class tree (left)
  const classNodes = [
    n('c01', 'Elemental Focus',     { col: 2, row: 0 }),
    n('c02', 'Wind Rush',           { col: 1, row: 1 }),
    n('c03', 'Ancestral Vigor',     { col: 3, row: 1 }),
    n('c04', 'Spirit Walk',         { col: 0, row: 2 }),
    n('c05', 'Totemic Resonance',   { col: 2, row: 2, type: 'diamond' }),
    n('c06', 'Static Charge',       { col: 4, row: 2 }),
    n('c07', 'Stoneskin',           { col: 1, row: 3, maxPoints: 2 }),
    n('c08', 'Earthbind',           { col: 3, row: 3, maxPoints: 2 }),
    n('c09', 'Hex Mastery',         { col: 0, row: 4 }),
    n('c10', 'Lava Surge',          { col: 2, row: 4, type: 'diamond' }),
    n('c11', 'Cleansing Tides',     { col: 4, row: 4 }),
    n('c12', 'Astral Shift',        { col: 1, row: 5 }),
    n('c13', 'Capacitor Totem',     { col: 3, row: 5 }),
    n('c14', 'Ascendance',          { col: 2, row: 6, type: 'capstone' }),
    n('c15', 'Primal Elementalist', { col: 1, row: 7 }),
    n('c16', 'Stormkeeper',         { col: 3, row: 7 }),
  ];

  const classEdges = [
    ['c01','c02'], ['c01','c03'],
    ['c02','c04'], ['c02','c05'],
    ['c03','c05'], ['c03','c06'],
    ['c04','c07'], ['c05','c07'], ['c05','c08'], ['c06','c08'],
    ['c07','c09'], ['c07','c10'], ['c08','c10'], ['c08','c11'],
    ['c09','c12'], ['c10','c12'], ['c10','c13'], ['c11','c13'],
    ['c12','c14'], ['c13','c14'],
    ['c14','c15'], ['c14','c16'],
  ];

  // Spec tree (right)
  const specNodes = [
    n('s01', 'Healing Surge',       { col: 2, row: 0 }),
    n('s02', 'Riptide',             { col: 1, row: 1 }),
    n('s03', 'Chain Heal',          { col: 3, row: 1 }),
    n('s04', 'Tidal Waves',         { col: 0, row: 2, maxPoints: 2 }),
    n('s05', 'Earthliving',         { col: 2, row: 2, type: 'diamond' }),
    n('s06', 'Resurgence',          { col: 4, row: 2 }),
    n('s07', 'Healing Stream',      { col: 1, row: 3 }),
    n('s08', 'Spirit Link',         { col: 3, row: 3 }),
    n('s09', 'Mana Tide',           { col: 0, row: 4 }),
    n('s10', 'Cloudburst',          { col: 2, row: 4, type: 'diamond' }),
    n('s11', 'Healing Tide',        { col: 4, row: 4 }),
    n('s12', 'Wellspring',          { col: 1, row: 5, maxPoints: 2 }),
    n('s13', 'Downpour',            { col: 3, row: 5, maxPoints: 2 }),
    n('s14', 'Ancestral Guidance',  { col: 2, row: 6, type: 'capstone' }),
    n('s15', 'Deluge',              { col: 1, row: 7 }),
    n('s16', 'Unleash Life',        { col: 3, row: 7 }),
  ];

  const specEdges = [
    ['s01','s02'], ['s01','s03'],
    ['s02','s04'], ['s02','s05'],
    ['s03','s05'], ['s03','s06'],
    ['s04','s07'], ['s05','s07'], ['s05','s08'], ['s06','s08'],
    ['s07','s09'], ['s07','s10'], ['s08','s10'], ['s08','s11'],
    ['s09','s12'], ['s10','s12'], ['s10','s13'], ['s11','s13'],
    ['s12','s14'], ['s13','s14'],
    ['s14','s15'], ['s14','s16'],
  ];

  // Hero tree (middle) — placeholder Farseer layout (~10 nodes, narrower).
  // Swap label per cluster (e.g. "Hero · Totemic") when backend wires hero choice.
  const heroNodes = [
    n('h01', 'Call of the Ancestors', { col: 1, row: 0 }),
    n('h02', 'Latent Wisdom',         { col: 0, row: 1 }),
    n('h03', 'Ancient Fellowship',    { col: 2, row: 1 }),
    n('h04', 'Routine Communion',     { col: 1, row: 2, type: 'diamond' }),
    n('h05', 'Heed My Call',          { col: 0, row: 3 }),
    n('h06', 'Offering from Beyond',  { col: 2, row: 3 }),
    n('h07', 'Primordial Capacity',   { col: 1, row: 4 }),
    n('h08', 'Maelstrom Supremacy',   { col: 0, row: 5 }),
    n('h09', 'Final Calling',         { col: 1, row: 6, type: 'capstone' }),
    n('h10', 'Earthen Communion',     { col: 2, row: 5 }),
  ];

  const heroEdges = [
    ['h01','h02'], ['h01','h03'],
    ['h02','h04'], ['h03','h04'],
    ['h04','h05'], ['h04','h06'],
    ['h05','h07'], ['h06','h07'],
    ['h07','h08'], ['h07','h10'],
    ['h08','h09'], ['h10','h09'],
  ];

  const byId = {};
  [...classNodes, ...specNodes, ...heroNodes].forEach(node => { byId[node.id] = node; });

  return {
    trees: [
      { id: 'class', label: 'Class Tree',     nodes: classNodes, edges: classEdges },
      { id: 'hero',  label: 'Hero · Farseer', nodes: heroNodes,  edges: heroEdges },
      { id: 'spec',  label: 'Spec Tree',      nodes: specNodes,  edges: specEdges },
    ],
    byId,
  };
})();
