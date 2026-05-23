// Main app — composes topbar, cluster tabs, tree pane, global PvP panel,
// sidebar (Cluster Signature), bottom Gear panel, tooltip, and tweaks panel.
//
// Wired to the flat backend shape (one bracket per CLUSTER_DATA):
//   data.spec, data.bracket, data.specLabel, data.sample_size, data.avg_ilvl,
//   data.pvp_talents, data.talents.{core|flex|contested}, data.clusters,
//   data.gear.{avg_ilvl, slots}

const { useState, useEffect, useMemo } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "flexStyle": "glow",
  "heatmap": false,
  "showSignature": true
} /*EDITMODE-END*/;

const FLEX_STYLES = [
{ value: 'glow', label: 'Glow' },
{ value: 'dashed', label: 'Dashed' },
{ value: 'fill', label: 'Tint' },
{ value: 'pulse', label: 'Pulse' }];


// === WoW classes / specs / brackets for the breadcrumb dropdowns ============
const CLASSES = {
  'Death Knight': { color: '#C41E3A', specs: ['Blood', 'Frost', 'Unholy'] },
  'Demon Hunter': { color: '#A330C9', specs: ['Havoc', 'Vengeance'] },
  'Druid':        { color: '#FF7C0A', specs: ['Balance', 'Feral', 'Guardian', 'Restoration'] },
  'Evoker':       { color: '#33937F', specs: ['Devastation', 'Preservation', 'Augmentation'] },
  'Hunter':       { color: '#AAD372', specs: ['Beast Mastery', 'Marksmanship', 'Survival'] },
  'Mage':         { color: '#3FC7EB', specs: ['Arcane', 'Fire', 'Frost'] },
  'Monk':         { color: '#00FF98', specs: ['Brewmaster', 'Mistweaver', 'Windwalker'] },
  'Paladin':      { color: '#F48CBA', specs: ['Holy', 'Protection', 'Retribution'] },
  'Priest':       { color: '#FFFFFF', specs: ['Discipline', 'Holy', 'Shadow'] },
  'Rogue':        { color: '#FFF468', specs: ['Assassination', 'Outlaw', 'Subtlety'] },
  'Shaman':       { color: '#0070DD', specs: ['Elemental', 'Enhancement', 'Restoration'] },
  'Warlock':      { color: '#8788EE', specs: ['Affliction', 'Demonology', 'Destruction'] },
  'Warrior':      { color: '#C69B6D', specs: ['Arms', 'Fury', 'Protection'] }
};
const BRACKETS = ['2v2', '3v3', 'Solo Shuffle', 'RBG', 'Blitz'];

const slugify = (s) => s.toLowerCase().replace(/ /g, '-');

const normalizeBracket = (b) => {
  const low = b.toLowerCase();
  if (low.includes('shuffle')) return 'shuffle';
  if (low.includes('blitz')) return 'blitz';
  return low.replace(/ /g, '-');
};

const buildHref = (cls, spec, bracket) => {
  const specSlug = `${slugify(spec)}-${slugify(cls)}`;
  const bracketSlug = normalizeBracket(bracket);
  const filename = `${specSlug}_${bracketSlug}.html`;
  // If served via local server, use absolute path to ensure on-demand gen hits the server
  if (window.location.protocol === 'http:' && window.location.hostname === 'localhost') {
    return `/pages/${filename}`;
  }
  return filename;
};

// Wowhead serves class icons keyed by squashed lowercase names ("deathknight", "demonhunter", "shaman", ...)
const classIconSlug = (cls) => cls.toLowerCase().replace(/[\s-]/g, '');
const classIconUrl = (cls) =>
  `https://wow.zamimg.com/images/wow/icons/large/classicon_${classIconSlug(cls)}.jpg`;

function CrumbDrop({ trigger, active, align, children }) {
  return (
    <div className={`crumb-drop ${align === 'right' ? 'crumb-drop-right' : ''}`}>
      <span className={`crumb-trigger ${active ? 'active' : ''}`}>{trigger}</span>
      <div className="crumb-menu">{children}</div>
    </div>);

}


// === Auto-name a cluster by its 1–2 most defining contested takes ==========
// "Most defining" = lowest global pick rate among takes (most selective choice).
function autoClusterName(cluster) {
  const takes = (cluster.takes || []).
  filter((t) => t.name && t.pct >= 20 && t.pct <= 80).
  sort((a, b) => a.pct - b.pct);
  if (!takes.length) return `#${cluster.rank}`;
  const word1 = (name) => name.split(' ')[0];
  if (takes.length === 1) return word1(takes[0].name);
  return word1(takes[0].name) + ' + ' + word1(takes[1].name);
}

// === Derive per-cluster tree-node state =====================================
// Global core → core; global flex → flex; cluster.takes → core+contested.
// Everything else → not in map (renders as skip).
function deriveNodeMap(data, cluster) {
  const map = {};
  (data.talents.core || []).forEach((t) => {
    map[t.id] = { role: 'core', pts: t.pts || 1, pickRate: t.pct, sourceName: t.name, rankDist: t.rankDist };
  });
  (data.talents.flex || []).forEach((t) => {
    map[t.id] = { role: 'flex', pts: t.pts || 1, pickRate: t.pct, sourceName: t.name, rankDist: t.rankDist };
  });
  (cluster.takes || []).forEach((t) => {
    map[t.id] = { role: 'core', pts: t.pts || 1, pickRate: t.pct, sourceName: t.name, contested: true, rankDist: t.rankDist };
  });
  return map;
}


// Pick the hero tree whose nodeIds have the most overlap with the cluster's
// core+takes node IDs. Falls back to the right tree (Totemic for Resto Shaman).
function selectHeroTree(data, nodeMap) {
  const heroTrees = data.tree && data.tree.heroTrees;
  if (!heroTrees) return null;
  const dominated = (ht) => ht.nodeIds.filter((id) => nodeMap[id]).length;
  return dominated(heroTrees.left) >= dominated(heroTrees.right) ?
  heroTrees.left : heroTrees.right;
}

function App() {
  const data = window.CLUSTER_DATA;

  // Navigation builder state for the breadcrumbs
  const [navSelection, setNavSelection] = useState({
    class: data.specLabel.class,
    spec: data.specLabel.spec,
    bracket: data.bracket
  });

  const isSelectionComplete = navSelection.class && navSelection.spec && navSelection.bracket;
  const isNavigating = isSelectionComplete && (
    navSelection.class !== data.specLabel.class ||
    navSelection.spec !== data.specLabel.spec ||
    navSelection.bracket !== data.bracket
  );

  // Sort clusters by share descending.
  const clusters = useMemo(
    () => [...data.clusters].sort((a, b) => b.pct - a.pct),
    [data]
  );
  // Only display clusters with 2+ players; single-player outliers are noise.
  const majorClusters = useMemo(() => clusters.filter((c) => c.count >= 2), [clusters]);
  const minorCount = clusters.length - majorClusters.length;

  const [activeRank, setActiveRank] = useState(majorClusters[0].rank);
  useEffect(() => {
    if (!majorClusters.find((c) => c.rank === activeRank)) setActiveRank(majorClusters[0].rank);
  }, [majorClusters, activeRank]);

  const cluster = clusters.find((c) => c.rank === activeRank) || clusters[0];

  // Derived node-state map for the active cluster.
  const nodeMap = useMemo(() => deriveNodeMap(data, cluster), [data, cluster]);
  const clusterForRenderer = { ...cluster, nodes: nodeMap, name: autoClusterName(cluster) };
  const heroTree = useMemo(() => selectHeroTree(data, nodeMap), [data, nodeMap]);

  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tip, setTip] = useState(null);
  const [toast, setToast] = useState(null);

  // Keyboard nav — ← / → between clusters.
  useEffect(() => {
    function onKey(e) {
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
      const idx = majorClusters.findIndex((c) => c.rank === activeRank);
      if (e.key === 'ArrowRight') setActiveRank(majorClusters[(idx + 1) % majorClusters.length].rank);else
      if (e.key === 'ArrowLeft') setActiveRank(majorClusters[(idx - 1 + majorClusters.length) % majorClusters.length].rank);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [clusters, activeRank]);

  const onCopy = () => {
    navigator.clipboard.writeText(cluster.canonical_code).catch(() => {});
    setToast('Build code copied');
    setTimeout(() => setToast(null), 1500);
  };

  return (
    <div className="app" data-screen-label="Talent cluster picker">
      <header className="topbar" data-comment-anchor="51655c5842-header-111-7">
        <div className="brand">
          <img className="brand-mark"
               data-comment-anchor="23de2b0743-div-113-11"
               src={classIconUrl(navSelection.class)}
               alt={navSelection.class}
               style={{ '--class-color': (CLASSES[navSelection.class] && CLASSES[navSelection.class].color) || 'var(--accent)' }} />
        </div>
        <div className="crumb">
          <CrumbDrop trigger={navSelection.class}>
            <div className="crumb-menu-title">Class</div>
            <div className="crumb-menu-grid">
              {Object.entries(CLASSES).map(([cls, info]) =>
                <a key={cls}
                   href="#"
                   onClick={(e) => {
                     e.preventDefault();
                     setNavSelection({ class: cls, spec: null, bracket: null });
                   }}
                   className={`crumb-menu-item ${cls === navSelection.class ? 'current' : ''}`}>
                  <span className="cls-dot" style={{ background: info.color }}></span>
                  <span className="cls-name" style={{ color: info.color }}>{cls}</span>
                </a>
              )}
            </div>
          </CrumbDrop>
          <span className="sep">/</span>

          {navSelection.class ? (
            <CrumbDrop trigger={navSelection.spec || <span className="select-hint">Select Spec...</span>} active={!navSelection.spec}>
              <div className="crumb-menu-title">Spec · {navSelection.class}</div>
              {(CLASSES[navSelection.class] ? CLASSES[navSelection.class].specs : []).map((sp) =>
                <a key={sp}
                   href="#"
                   onClick={(e) => {
                     e.preventDefault();
                     setNavSelection({ ...navSelection, spec: sp, bracket: null });
                   }}
                   className={`crumb-menu-item ${sp === navSelection.spec ? 'current' : ''}`}>
                  <span className="cls-dot" style={{ background: CLASSES[navSelection.class].color }}></span>
                  <span>{sp}</span>
                </a>
              )}
            </CrumbDrop>
          ) : (
            <span className="crumb-trigger disabled">Spec</span>
          )}

          <span className="sep">/</span>

          {navSelection.spec ? (
            <CrumbDrop trigger={navSelection.bracket || <span className="select-hint">Select Bracket...</span>} active={!navSelection.bracket}>
              <div className="crumb-menu-title">Bracket</div>
              {BRACKETS.map((b) =>
                <a key={b}
                   href={isNavigating ? buildHref(navSelection.class, navSelection.spec, b) : "#"}
                   onClick={(e) => {
                     if (!isNavigating && b === navSelection.bracket) e.preventDefault();
                     setNavSelection({ ...navSelection, bracket: b });
                   }}
                   className={`crumb-menu-item ${b === navSelection.bracket ? 'current' : ''}`}>
                  <span className="bracket-tag">{b}</span>
                </a>
              )}
            </CrumbDrop>
          ) : (
            <span className="crumb-trigger disabled">Bracket</span>
          )}

          {isNavigating && (
            <a className="nav-go-btn" href={buildHref(navSelection.class, navSelection.spec, navSelection.bracket)}>
              Go →
            </a>
          )}
        </div>

      </header>

      <nav className="tabs" role="tablist" aria-label="Cluster">
        {majorClusters.map((c) =>
        <button
          key={c.rank}
          className={`tab ${c.rank === activeRank ? 'active' : ''}`}
          onClick={() => setActiveRank(c.rank)}
          role="tab"
          data-screen-label={autoClusterName(c)}>
          
            <span className="tab-rank">#{c.rank}</span>
            <span className="tab-name">{autoClusterName(c)}</span>
            <span className="tab-meta">
              <span><span className="pct">{c.pct}%</span></span>
              <span>n={c.count}</span>
            </span>
            <span className="tab-bar">
              <span className="tab-bar-fill" style={{ width: `${Math.min(100, c.pct * 4)}%` }}></span>
            </span>
          </button>
        )}
        {minorCount > 0 &&
        <div className="tab tab-minor" title={`${minorCount} more clusters with n=1 (outliers)`}>
            +{minorCount} minor
          </div>
        }
      </nav>

      <main className="main">
        <section className="tree-pane">
          <div className="tree-pane-inner">
            <div className="trees-row">
              {(() => {const src = window.CLUSTER_DATA.tree || window.TREE;const trees = heroTree ? [src.trees[0], heroTree, src.trees[1]] : src.trees;return trees;})().map((tree) =>
              <div className="tree" key={tree.id}>
                  <div className="tree-header">
                    <h3>{tree.label}</h3>
                    <div className="stat">
                      <span className="num">{tree.nodes.reduce((s, tn) =>
                      s + (nodeMap[tn.id] ? nodeMap[tn.id].pts || 1 : 0), 0
                      )}</span> pts
                    </div>
                  </div>
                  <TalentTree
                  tree={tree}
                  cluster={clusterForRenderer}
                  flexStyle={tweaks.flexStyle}
                  heatmap={tweaks.heatmap}
                  showSignature={tweaks.showSignature}
                  onHover={setTip}
                  onLeave={() => setTip(null)} />
                
                </div>
              )}
            </div>

            <GlobalPvpPanel data={data} onHover={setTip} onLeave={() => setTip(null)} />
            <GearPanel group={data} />
          </div>
        </section>

        <Sidebar
          cluster={cluster}
          group={data}
          onCopy={onCopy}
          heatmap={tweaks.heatmap} />
        
      </main>

      {tip && <Tooltip {...tip} />}
      {toast && <div className="copy-toast">✓ {toast}</div>}

      <TweaksPanel title="Tweaks">
        <TweakSection label="Flex highlight">
          <TweakSelect label="Style" value={tweaks.flexStyle}
          onChange={(v) => setTweak('flexStyle', v)} options={FLEX_STYLES} />
        </TweakSection>
        <TweakSection label="Pick-rate heatmap">
          <TweakToggle label="Color by pick rate" value={tweaks.heatmap}
          onChange={(v) => setTweak('heatmap', v)} />
        </TweakSection>
        <TweakSection label="Cluster signature">
          <TweakToggle label="Mark contested takes" value={tweaks.showSignature}
          onChange={(v) => setTweak('showSignature', v)} />
        </TweakSection>
      </TweaksPanel>
    </div>);

}

function GlobalPvpPanel({ data, onHover, onLeave }) {
  const all = data.pvp_talents || [];

  React.useEffect(() => {
    const ids = all.map(p => p.id).filter(Boolean);
    if (ids.length) window.TalentMeta.preload(ids);
  }, [all]);

  if (all.length === 0) return null;
  const modal = all.slice(0, 3);
  const alts = all.slice(3);

  const onHoverPvp = (e, p) => {
    onHover({
      node: { name: p.name, spellId: p.id, maxPoints: 1 },
      state: { role: 'core', pts: 1, pickRate: p.pct },
      x: e.clientX, y: e.clientY
    });
  };

  return (
    <div className="pvp-panel" data-screen-label="PvP talents (global)">
      <div className="pvp-head">
        <h3>PvP Talents</h3>
        <div className="stat">
          <span style={{ color: 'var(--flex)', marginRight: 8, fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em' }}>GLOBAL</span>
          <span>same across all clusters · n={data.sample_size.toLocaleString()}</span>
        </div>
      </div>
      <div className="pvp-grid">
        {modal.map((p, i) =>
        <div className="pvp-slot" key={p.id}
        onMouseEnter={(e) => onHoverPvp(e, p)}
        onMouseLeave={onLeave}>
            <span className="pvp-slot-tag">SLOT {i + 1}</span>
            <div className="pvp-slot-pos">Modal pick</div>
            <div className="pvp-slot-name">{p.name}</div>
            <div className="pvp-slot-pct">{p.pct}<span className="unit">%</span></div>
          </div>
        )}
        <div className="pvp-alts">
          <div className="pvp-alts-head">Alternatives · {alts.length}</div>
          <div className="pvp-alts-list">
            {alts.map((p) =>
            <div className="pvp-alt-row" key={p.id}
            onMouseEnter={(e) => onHoverPvp(e, p)}
            onMouseLeave={onLeave}>
                <span className="pvp-alt-name">{p.name}</span>
                <span className="pvp-alt-bar">
                  <span className="pvp-alt-bar-fill" style={{ width: `${p.pct}%` }}></span>
                </span>
                <span className="pvp-alt-pct">{p.pct}%</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>);

}

function Tooltip({ node, state, x, y }) {
  const meta = window.useTalentMeta();
  const sid = node && node.spellId;
  const m = sid && meta.get(sid);
  React.useEffect(() => { if (sid) window.TalentMeta.fetchDesc(sid); }, [sid]);

  const role = state ? state.role : 'skip';
  const isContested = state && state.contested;
  // Generous viewport padding so the wider tooltip never goes off-screen.
  const TOOLTIP_W = 340;
  const TOOLTIP_H_EST = 320;
  const tooltipStyle = {
    left: Math.min(x + 14, window.innerWidth - TOOLTIP_W - 8),
    top: Math.min(y + 14, window.innerHeight - TOOLTIP_H_EST)
  };
  const isMulti = node.maxPoints && node.maxPoints > 1;
  const rankDist = state && state.rankDist;
  const displayRank = state ? rankDist ? window.modalRank(state) : state.pts : 0;
  const rankFlex = state && window.isRankFlex(node, state);

  let tag = 'SKIP';
  if (role === 'core') tag = rankFlex ? 'CORE · RANK-FLEX' : isContested ? 'CLUSTER TAKE' : 'CORE';else
  if (role === 'flex') tag = 'FLEX';

  return (
    <div className="tooltip" style={tooltipStyle}>
      <div className="tooltip-head">
        {m && m.icon ? <img className="tooltip-icon" src={m.icon} alt="" /> : null}
        <span className="tooltip-name">{node.name}</span>
        <span className={`tooltip-tag ${role} ${isContested ? 'contested' : ''}`}>{tag}</span>
      </div>
      {m && m.descHtml ? (
        <div className="tooltip-wh"
             dangerouslySetInnerHTML={{ __html: m.descHtml }} />
      ) : (
        <div className="tooltip-desc tooltip-desc-loading">
          {sid ? 'Loading description…' : (node.desc || '')}
        </div>
      )}
      {state ?
      <>
          <div className="tooltip-stat">
            <span>Pick rate {isContested ? '(overall)' : ''}</span>
            <span className="v">{state.pickRate}%</span>
          </div>
          <div className="tooltip-bar">
            <div className="tooltip-bar-fill" style={{ width: `${state.pickRate}%` }}></div>
          </div>
          {rankDist ?
        <>
              <div className="tooltip-rank-title">Rank distribution</div>
              {rankDist.map((pct, i) => {
            const modalI = displayRank - 1;
            return (
              <div className="tooltip-rank-row" key={i}>
                    <span className="lbl">R {i + 1}</span>
                    <span className="bar">
                      <span className={`fill ${i === modalI ? 'modal' : ''}`} style={{ width: `${pct}%` }}></span>
                    </span>
                    <span className="pct">{pct}%</span>
                  </div>);

          })}
              {(() => {
            const skipPct = Math.max(0, 100 - rankDist.reduce((s, v) => s + v, 0));
            if (skipPct < 0.5) return null;
            return (
              <div className="tooltip-rank-row">
                    <span className="lbl">skip</span>
                    <span className="bar">
                      <span className="fill" style={{ width: `${skipPct}%`, background: 'var(--text-3)' }}></span>
                    </span>
                    <span className="pct skip">{Math.round(skipPct)}%</span>
                  </div>);

          })()}
            </> :
        null}
        </> :

      <div className="tooltip-stat">
          <span>Not taken in this cluster</span>
        </div>
      }
    </div>);

}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);