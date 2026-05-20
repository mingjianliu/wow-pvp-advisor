// Main app — composes topbar, cluster tabs, tree pane, global PvP panel,
// sidebar, tooltip, and tweaks panel. Wired to the real backend shape.

const { useState, useEffect, useRef, useMemo } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "flexStyle": "glow",
  "heatmap": false,
  "showSignature": true
}/*EDITMODE-END*/;

const FLEX_STYLES = [
  { value: 'glow',   label: 'Glow' },
  { value: 'dashed', label: 'Dashed' },
  { value: 'fill',   label: 'Tint' },
  { value: 'pulse',  label: 'Pulse' },
];

const PVP_BY_ID = {};

// === Derive per-cluster node state from backend shape =====================
// Global core → core; Global flex → flex; Cluster.takes → core (with
// `contested: true` flag so the renderer can mark cluster-defining picks).
// Cluster.skips and everything else → not in map (renders as skip).
function deriveNodeMap(data, cluster) {
  const map = {};
  data.talents.core.forEach(t => {
    map[t.id] = { role: 'core', pts: 1, pickRate: t.pct, sourceName: t.name };
  });
  data.talents.flex.forEach(t => {
    map[t.id] = { role: 'flex', pts: 1, pickRate: t.pct, sourceName: t.name };
  });
  cluster.takes.forEach(t => {
    map[t.id] = { role: 'core', pts: 1, pickRate: t.pct, sourceName: t.name, contested: true };
  });
  // Skips: nothing added — the tree renderer treats missing IDs as skip.
  return map;
}

function clusterLabel(c, customLabels) {
  if (customLabels && customLabels[c.rank]) return customLabels[c.rank];
  return `Cluster #${c.rank}`;
}

function App() {
  const data = window.CLUSTER_DATA;
  
  

  // Sort clusters by share desc (backend gives them roughly sorted by rank).
  const clusters = useMemo(
    () => [...data.clusters].sort((a, b) => b.pct - a.pct),
    [data]
  );

  const [activeRank, setActiveRank] = useState(clusters[0].rank);
  useEffect(() => {
    if (!clusters.find(c => c.rank === activeRank)) setActiveRank(clusters[0].rank);
  }, [clusters, activeRank]);

  const cluster = clusters.find(c => c.rank === activeRank) || clusters[0];

  // User-applied cluster labels — persisted in localStorage so they survive reload.
  const [customLabels, setCustomLabels] = useState(() => {
    try { return JSON.parse(localStorage.getItem('cp.labels') || '{}'); }
    catch { return {}; }
  });
  const setLabel = (rank, label) => {
    const next = { ...customLabels };
    if (label && label.trim()) next[rank] = label.trim();
    else delete next[rank];
    setCustomLabels(next);
    try { localStorage.setItem('cp.labels', JSON.stringify(next)); } catch {}
  };

  // Derived node state map for the active cluster.
  const nodeMap = useMemo(() => deriveNodeMap(data, cluster), [data, cluster]);
  const clusterForRenderer = { ...cluster, nodes: nodeMap, name: clusterLabel(cluster, customLabels) };

  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tip, setTip] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    function onKey(e) {
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
      const idx = clusters.findIndex(c => c.rank === activeRank);
      if (e.key === 'ArrowRight') setActiveRank(clusters[(idx + 1) % clusters.length].rank);
      else if (e.key === 'ArrowLeft') setActiveRank(clusters[(idx - 1 + clusters.length) % clusters.length].rank);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [clusters, activeRank]);

  const onCopy = () => {
    navigator.clipboard.writeText(cluster.canonical_code).catch(() => {});
    setToast('Build code copied');
    setTimeout(() => setToast(null), 1500);
  };

  // Build PvP lookup once per group (it's global, doesn't depend on cluster).
  useMemo(() => {
