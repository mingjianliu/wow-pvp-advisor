// Main app — composes topbar, cluster tabs, tree pane, PvP panel, sidebar, tooltip, and tweaks panel.

const { useState, useEffect, useRef, useMemo } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "flexStyle": "glow",
  "heatmap": false
}/*EDITMODE-END*/;

const FLEX_STYLES = [
  { value: 'glow',   label: 'Glow' },
  { value: 'dashed', label: 'Dashed' },
  { value: 'fill',   label: 'Tint' },
  { value: 'pulse',  label: 'Pulse' },
];

const PVP_BY_ID = (window.PVP_POOL || []).reduce((m, p) => { m[p.id] = p; return m; }, {});

function App() {
  const [groupSize, setGroupSize] = useState('Shuffle');
  const data = window.CLUSTER_DATA;
  const group = data.byGroup[groupSize];

  const clusters = useMemo(
    () => [...group.clusters].sort((a, b) => b.pct - a.pct),
    [group]
  );

  const [activeId, setActiveId] = useState(clusters[0].id);
  useEffect(() => {
    if (!clusters.find(c => c.id === activeId)) setActiveId(clusters[0].id);
  }, [clusters, activeId]);

  const cluster = clusters.find(c => c.id === activeId) || clusters[0];

  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tip, setTip] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    function onKey(e) {
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
      const idx = clusters.findIndex(c => c.id === activeId);
      if (e.key === 'ArrowRight') setActiveId(clusters[(idx + 1) % clusters.length].id);
      else if (e.key === 'ArrowLeft') setActiveId(clusters[(idx - 1 + clusters.length) % clusters.length].id);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [clusters, activeId]);

  const onCopy = () => {
    navigator.clipboard.writeText(cluster.buildString).catch(() => {});
    setToast('Build string copied');
    setTimeout(() => setToast(null), 1500);
  };

  return (
    <div className="app" data-screen-label="Talent cluster picker">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"></div>
          CLUSTER<span style={{color:'var(--text-2)'}}>·</span>PICK
        </div>
        <div className="crumb">
          <span>{data.spec.class}</span>
          <span className="sep">/</span>
          <span className="active">{data.spec.spec}</span>
          <span className="sep">/</span>
          <span style={{color:'var(--text-3)'}}>solo / shuffle</span>
        </div>

        <div className="topbar-right">
          <div className="filter-group">
            <span className="filter-label">Group</span>
            <div className="seg" role="tablist">
              {data.groupSizes.map(g => (
                <button
                  key={g}
                  className={g === groupSize ? 'active' : ''}
                  onClick={() => setGroupSize(g)}
                >{g}</button>
              ))}
            </div>
          </div>
          <div className="filter-group">
            <span className="filter-label">N=</span>
            <span style={{fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-1)'}}>
              {group.sampleSize.toLocaleString()}
            </span>
          </div>
        </div>
      </header>

      <nav className="tabs" role="tablist" aria-label="Cluster">
        {clusters.map(c => (
          <button
            key={c.id}
            className={`tab ${c.id === activeId ? 'active' : ''}`}
            onClick={() => setActiveId(c.id)}
            role="tab"
            data-screen-label={`Cluster: ${c.name}`}
          >
            <span className="tab-name">{c.name}</span>
            <span className="tab-meta">
              <span><span className="pct">{c.pct}%</span></span>
              <span>n={c.sample.toLocaleString()}</span>
            </span>
            <span className="tab-bar"><span className="tab-bar-fill" style={{width: `${c.pct}%`}}></span></span>
          </button>
        ))}
      </nav>

      <main className="main">
        <section className="tree-pane">
          <div className="tree-pane-inner">
            <div className="trees-row">
              {window.TREE.trees.map(tree => (
                <div className="tree" key={tree.id}>
                  <div className="tree-header">
                    <h3>{tree.label}</h3>
                    <div className="stat">
                      <span className="num">{tree.nodes.reduce((s, tn) => {
                        const st = cluster.nodes[tn.id];
                        return s + (st ? (st.rankDist ? window.modalRank(st) : st.pts) : 0);
                      }, 0)}</span> pts
                    </div>
                  </div>
                  <TalentTree
                    tree={tree}
                    cluster={cluster}
                    flexStyle={tweaks.flexStyle}
                    heatmap={tweaks.heatmap}
                    onHover={setTip}
                    onLeave={() => setTip(null)}
                  />
                </div>
              ))}
            </div>

            <PvpPanel cluster={cluster} onHover={setTip} onLeave={() => setTip(null)} />
          </div>
        </section>

        <Sidebar cluster={cluster} onCopy={onCopy} heatmap={tweaks.heatmap} />
      </main>

      {tip && <Tooltip {...tip} />}
      {toast && <div className="copy-toast">✓ {toast}</div>}

      <TweaksPanel title="Tweaks">
        <TweakSection label="Flex highlight">
          <TweakSelect
            label="Style"
            value={tweaks.flexStyle}
            onChange={(v) => setTweak('flexStyle', v)}
            options={FLEX_STYLES}
          />
        </TweakSection>
        <TweakSection label="Pick-rate heatmap">
          <TweakToggle
            label="Color by pick rate"
            value={tweaks.heatmap}
            onChange={(v) => setTweak('heatmap', v)}
          />
        </TweakSection>
      </TweaksPanel>
    </div>
  );
}

function PvpPanel({ cluster, onHover, onLeave }) {
  if (!cluster.pvp) return null;
  const modal = cluster.pvp.modal;
  const dist = cluster.pvp.dist || {};
  const alts = Object.entries(dist)
    .filter(([id]) => !modal.includes(id))
    .sort((a, b) => b[1] - a[1]);

  const onHoverPvp = (e, id) => {
    const meta = PVP_BY_ID[id];
    if (!meta) return;
    // Build a synthetic node-like object so the existing Tooltip can render it.
    const fakeNode = { name: meta.name, desc: meta.desc, maxPoints: 1 };
    const pickRate = dist[id] || 0;
    onHover({
      node: fakeNode,
      state: { role: modal.includes(id) ? 'core' : 'flex', pts: 1, pickRate },
      x: e.clientX, y: e.clientY,
    });
  };

  return (
    <div className="pvp-panel" data-screen-label="PvP talents">
      <div className="pvp-head">
        <h3>PvP Talents</h3>
        <div className="stat">
          <span className="num">3</span> slots · top picks for this cluster
        </div>
      </div>
      <div className="pvp-grid">
        {modal.map((id, i) => {
          const meta = PVP_BY_ID[id];
          const pct = dist[id] || 0;
          return (
            <div className="pvp-slot" key={id}
                 onMouseEnter={(e) => onHoverPvp(e, id)}
                 onMouseMove={(e) => onHoverPvp(e, id)}
                 onMouseLeave={onLeave}>
              <span className="pvp-slot-tag">SLOT {i + 1}</span>
              <div className="pvp-slot-pos">Modal pick</div>
              <div className="pvp-slot-name">{meta ? meta.name : id}</div>
              <div className="pvp-slot-pct">{pct}<span className="unit">%</span></div>
            </div>
          );
        })}
        <div className="pvp-alts">
          <div className="pvp-alts-head">Alternatives · {alts.length}</div>
          <div className="pvp-alts-list">
            {alts.map(([id, pct]) => {
              const meta = PVP_BY_ID[id];
              return (
                <div className="pvp-alt-row" key={id}
                     onMouseEnter={(e) => onHoverPvp(e, id)}
                     onMouseMove={(e) => onHoverPvp(e, id)}
                     onMouseLeave={onLeave}>
                  <span className="pvp-alt-name">{meta ? meta.name : id}</span>
                  <span className="pvp-alt-bar">
                    <span className="pvp-alt-bar-fill" style={{width: `${pct}%`}}></span>
                  </span>
                  <span className="pvp-alt-pct">{pct}%</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function Tooltip({ node, state, x, y }) {
  const role = state ? state.role : 'skip';
  const tooltipStyle = {
    left: Math.min(x, window.innerWidth - 300),
    top: Math.min(y, window.innerHeight - 240),
  };
  const isMulti = node.maxPoints && node.maxPoints > 1;
  const rankDist = state && state.rankDist;
  const displayRank = state ? (rankDist ? window.modalRank(state) : state.pts) : 0;
  const rankFlex = state && window.isRankFlex(node, state);
  return (
    <div className="tooltip" style={tooltipStyle}>
      <div className="tooltip-head">
        <span className="tooltip-name">{node.name}</span>
        <span className={`tooltip-tag ${role}`}>
          {role === 'core' ? (rankFlex ? 'CORE · RANK-FLEX' : 'CORE') : role === 'flex' ? 'FLEX' : 'SKIP'}
        </span>
      </div>
      <div className="tooltip-desc">{node.desc}</div>
      {state ? (
        <>
          <div className="tooltip-stat">
            <span>Pick rate</span>
            <span className="v">{state.pickRate}%</span>
          </div>
          <div className="tooltip-bar">
            <div className="tooltip-bar-fill" style={{width: `${state.pickRate}%`}}></div>
          </div>
          {isMulti && rankDist ? (
            <>
              <div className="tooltip-rank-title">Rank distribution</div>
              {rankDist.map((pct, i) => {
                const modalI = displayRank - 1;
                return (
                  <div className="tooltip-rank-row" key={i}>
                    <span className="lbl">R {i + 1}</span>
                    <span className="bar">
                      <span className={`fill ${i === modalI ? 'modal' : ''}`} style={{width: `${pct}%`}}></span>
                    </span>
                    <span className="pct">{pct}%</span>
                  </div>
                );
              })}
              {/* Skip share, if any */}
              {(() => {
                const skipPct = Math.max(0, 100 - rankDist.reduce((s,v) => s+v, 0));
                if (skipPct < 0.5) return null;
                return (
                  <div className="tooltip-rank-row">
                    <span className="lbl">skip</span>
                    <span className="bar">
                      <span className="fill" style={{width: `${skipPct}%`, background:'var(--text-3)'}}></span>
                    </span>
                    <span className="pct skip">{Math.round(skipPct)}%</span>
                  </div>
                );
              })()}
            </>
          ) : (
            <div className="tooltip-stat" style={{marginTop:4, borderTop:'none', paddingTop:0}}>
              <span>Points</span>
              <span className="v">{displayRank || state.pts}{isMulti ? ` / ${node.maxPoints}` : ''}</span>
            </div>
          )}
        </>
      ) : (
        <div className="tooltip-stat">
          <span>Not taken in this cluster</span>
        </div>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
