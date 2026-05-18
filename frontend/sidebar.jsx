// Right sidebar — cluster summary, flex slots, legend, build string + copy.

function Sidebar({ cluster, onCopy, heatmap }) {
  const coreCount = Object.values(cluster.nodes).filter(n => n.role === 'core').length;
  const flexCount = Object.values(cluster.nodes).filter(n => n.role === 'flex').length;
  const totalPoints = Object.values(cluster.nodes).reduce((s, n) => s + n.pts, 0);

  return (
    <aside className="sidebar" data-screen-label="Cluster details">
      <div className="side-section">
        <h4>Selected cluster</h4>
        <div className="cluster-title">{cluster.name}</div>
        <div className="cluster-tagline">{cluster.tagline}</div>
        <div className="kpi-row">
          <div className="kpi">
            <div className="kpi-label">Share</div>
            <div className="kpi-value">{cluster.pct}<span className="pct">%</span></div>
          </div>
          <div className="kpi">
            <div className="kpi-label">Sample</div>
            <div className="kpi-value">{cluster.sample.toLocaleString()}</div>
          </div>
          <div className="kpi">
            <div className="kpi-label">Core nodes</div>
            <div className="kpi-value">{coreCount}</div>
          </div>
          <div className="kpi">
            <div className="kpi-label">Flex nodes</div>
            <div className="kpi-value" style={{color:'var(--flex)'}}>{flexCount}</div>
          </div>
        </div>
      </div>

      <div className="side-section">
        <h4>Flexible points <span style={{color:'var(--text-3)',marginLeft:6,fontWeight:400}}>· {cluster.flexSlots.length}</span></h4>
        {cluster.flexSlots.length === 0 && (
          <div style={{color:'var(--text-2)', fontSize:11.5}}>No flex slots in this cluster — fully locked-in build.</div>
        )}
        {cluster.flexSlots.map(slot => (
          <FlexSlot key={slot.id} slot={slot} cluster={cluster} />
        ))}
      </div>

      <div className="side-section">
        <h4>Legend</h4>
        <div className="legend">
          <div className="legend-row"><span className="legend-dot core"></span> Core — taken by ~all players in this cluster</div>
          <div className="legend-row"><span className="legend-dot core rank-flex-mini"></span> Core, rank-flex — taken by all, rank varies</div>
          <div className="legend-row"><span className="legend-dot flex"></span> Flex — varies; doesn't change playstyle</div>
          <div className="legend-row"><span className="legend-dot skip"></span> Skipped in this cluster</div>
          <div className="legend-row"><span className="legend-dot core diamond"></span> Choice node (diamond)</div>
        </div>
        {heatmap && (
          <div style={{marginTop:14}}>
            <div className="kpi-label" style={{marginBottom:6}}>Pick-rate heatmap</div>
            <div className="heat-strip">
              <div style={{background:'var(--heat-0)'}}></div>
              <div style={{background:'var(--heat-1)'}}></div>
              <div style={{background:'var(--heat-2)'}}></div>
              <div style={{background:'var(--heat-3)'}}></div>
              <div style={{background:'var(--heat-4)'}}></div>
              <div style={{background:'var(--heat-5)'}}></div>
            </div>
            <div className="heat-strip-labels">
              <span>0%</span><span>50%</span><span>100%</span>
            </div>
          </div>
        )}
      </div>

      <div className="side-section">
        <h4>Build string</h4>
        <div className="kpi-label" style={{marginBottom:4}}>{totalPoints} points · paste into your client</div>
        <div className="build-string">{cluster.buildString}</div>
        <div className="build-actions">
          <button className="btn primary" onClick={onCopy}>
            <CopyIcon /> Copy build string
          </button>
        </div>
      </div>
    </aside>
  );
}

function FlexSlot({ slot, cluster }) {
  const opts = slot.options.map(id => {
    const node = window.TREE.byId[id];
    const st = cluster.nodes[id];
    return { id, node, rate: st ? st.pickRate : 0 };
  });
  const total = opts.reduce((s, o) => s + o.rate, 0) || 1;
  return (
    <div className="flex-slot">
      <div className="flex-slot-head">
        <span className="flex-slot-label">{slot.label}</span>
        <span className="flex-slot-tag">{opts.length} options</span>
      </div>
      {opts.map(opt => {
        const share = Math.round((opt.rate / total) * 100);
        return (
          <div className="flex-opt" key={opt.id}>
            <span className="flex-opt-dot"></span>
            <span className="flex-opt-name">{opt.node ? opt.node.name : opt.id}</span>
            <span className="flex-opt-bar">
              <span className="flex-opt-bar-fill" style={{width: `${share}%`}}></span>
            </span>
            <span className="flex-opt-pct">{share}%</span>
          </div>
        );
      })}
    </div>
  );
}

function CopyIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
      <rect x="3" y="3" width="9" height="11" rx="1" stroke="currentColor" strokeWidth="1.4"/>
      <path d="M6 1.5h7a1 1 0 0 1 1 1V11" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
    </svg>
  );
}

window.Sidebar = Sidebar;
