// Right sidebar — cluster summary, signature (takes + flex), legend, build code + copy.
// Gear moved out to its own bottom panel in the main pane.

function Sidebar({ cluster, group, onCopy, heatmap }) {
  const takes = [...(cluster.takes || [])].sort((a, b) => b.pct - a.pct);
  const flex = [...((group.talents && group.talents.flex) || [])].sort((a, b) => b.pct - a.pct);
  const meta = window.useTalentMeta();

  // Resolve spellIds and maxPoints for the tree-node ids referenced in cluster.takes.
  // The flat group.talents lists carry only {id, name, pct} — the actual
  // data lives on the tree-node, so we walk every tree to build the map.
  const nodeMetaById = React.useMemo(() => {
    const m = {};
    const trees = (group.tree && group.tree.trees) || [];
    const heroTrees = group.tree && group.tree.heroTrees;
    const allNodes = [
      ...trees.flatMap(t => t.nodes || []),
      ...((heroTrees && heroTrees.left && heroTrees.left.nodes) || []),
      ...((heroTrees && heroTrees.right && heroTrees.right.nodes) || []),
    ];
    allNodes.forEach(n => { 
      m[n.id] = { spellId: n.spellId, maxPoints: n.maxPoints || 1 };
    });
    return m;
  }, [group]);

  // Preload icons for everything we'll render in the sidebar.
  React.useEffect(() => {
    const ids = [];
    takes.forEach(t => { 
      const meta = nodeMetaById[t.id];
      const sid = t.spellId || (meta && meta.spellId);
      if (sid) ids.push(sid); 
    });
    flex.forEach(t => { if (t.spellId) ids.push(t.spellId); });
    if (ids.length) window.TalentMeta.preload(ids);
  }, [cluster.rank, nodeMetaById]);

  const TalentLink = ({ t, className }) => {
    const nodeMeta = nodeMetaById[t.id];
    const sid = t.spellId || (nodeMeta && nodeMeta.spellId);
    const m = sid && meta.get(sid);
    const icon = m && m.icon;
    const Iconlet = icon
      ? <img className="sig-icon" src={icon} alt="" loading="lazy" />
      : <span className="sig-icon placeholder"></span>;
    if (!sid) {
      return <span className={className}>{Iconlet}<span className="sig-text">{t.name}</span></span>;
    }
    return (
      <a
        className={`${className} talent-link`}
        href={`https://www.wowhead.com/spell=${sid}`}
        target="_blank"
        rel="noopener"
        data-wowhead={`spell=${sid}`}
      >{Iconlet}<span className="sig-text">{t.name}</span></a>
    );
  };

  const RankTag = ({ t }) => {
    const nodeMeta = nodeMetaById[t.id];
    const max = (nodeMeta && nodeMeta.maxPoints) || 1;
    const current = t.pts || 1;
    // Show rank tag if it's a multi-rank talent, even if current rank is 1
    if (max > 1) {
      return <span className="sig-pts">R{current}</span>;
    }
    return null;
  };

  return (
    <aside className="sidebar" data-screen-label="Cluster details">
      <div className="side-section">
        <div className="kpi-row">
          <div className="kpi">
            <div className="kpi-label">{window.t('share')}</div>
            <div className="kpi-value">{cluster.pct}<span className="pct">%</span></div>
          </div>
          <div className="kpi">
            <div className="kpi-label">{window.t('count')}</div>
            <div className="kpi-value">{cluster.count}</div>
          </div>
          <div className="kpi">
            <div className="kpi-label">{window.t('takes')}</div>
            <div className="kpi-value">{takes.length}</div>
          </div>
          <div className="kpi">
            <div className="kpi-label">{window.t('flex')}</div>
            <div className="kpi-value" style={{color:'var(--flex)'}}>{flex.length}</div>
          </div>
        </div>
      </div>

      <div className="side-section">
        <h4>{window.t('signature')} <span className="side-h-hint">contested talents this cluster picks</span></h4>
        <div className="signature-block">
          <div className="signature-row-head"><span className="dot-take"></span> {window.t('takes')} <span className="num">{takes.length}</span></div>
          <ul className="signature-list">
            {takes.map(t => (
              <li key={t.id} className="sig-item take">
                <div className="sig-name-row">
                  <TalentLink t={t} className="sig-name" />
                  <RankTag t={t} />
                </div>
                <span className="sig-bar"><span className="sig-bar-fill" style={{width: `${t.pct}%`}}></span></span>
                <span className="sig-pct">{t.pct}%</span>
              </li>
            ))}
          </ul>
          <div className="signature-row-head" style={{marginTop:14}}>
            <span className="dot-flex"></span> {window.t('flex')}
            <span className="num">{flex.length}</span>
            <span className="signature-row-hint">{window.t('global')} · varies</span>
          </div>
          {flex.length > 0 ? (
            <ul className="signature-list">
              {flex.map(t => (
                <li key={t.id} className="sig-item flex">
                  <div className="sig-name-row">
                    <TalentLink t={t} className="sig-name" />
                    <RankTag t={t} />
                  </div>
                  <span className="sig-bar"><span className="sig-bar-fill flex" style={{width: `${t.pct}%`}}></span></span>
                  <span className="sig-pct">{t.pct}%</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="signature-empty">No flex points for this spec</div>
          )}
        </div>
      </div>

      <div className="side-section">
        <h4>Legend</h4>
        <div className="legend">
          <div className="legend-row"><span className="legend-dot core"></span> Core — ~100% of players take this</div>
          <div className="legend-row"><span className="legend-dot core contested-mini"></span> Cluster take — this cluster's pick of a contested talent</div>
          <div className="legend-row"><span className="legend-dot flex"></span> Flex — rare, varies; doesn't change playstyle</div>
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
            <div className="heat-strip-labels"><span>0%</span><span>50%</span><span>100%</span></div>
          </div>
        )}
      </div>

      <div className="side-section">
        <h4>Build code <span className="side-h-hint">canonical · WoW import string</span></h4>
        <div className="build-string">{cluster.canonical_code}</div>
        <div className="build-actions">
          <button className="btn primary" onClick={onCopy}>
            <CopyIcon /> Copy code
          </button>
        </div>
      </div>
    </aside>
  );
}

// Bottom panel — full-width gear grid. Lives below the trees / PvP in the main pane.
function GearPanel({ group }) {
  if (!group.gear || !group.gear.slots) return null;
  const isZh = window.location.pathname.endsWith('_zh.html');
  const whDomain = isZh ? 'cn.wowhead.com' : 'www.wowhead.com';
  const whDomainAttr = isZh ? '&domain=cn' : '';
  
  return (
    <div className="gear-panel" data-screen-label="Gear">
      <div className="gear-panel-head">
        <h3>{window.t('gear')}</h3>
        <div className="stat">
          <span style={{color:'var(--flex)',marginRight:8,fontFamily:'var(--font-mono)',fontSize:9,letterSpacing:'0.12em'}}>{window.t('global')}</span>
          <span>{window.t('avgIlvl')} <span className="num">{group.gear.avg_ilvl}</span> · {window.t('topPick')} · n={group.sample_size.toLocaleString()}</span>
        </div>
      </div>
      <ul className="gear-grid">
        {group.gear.slots.map(s => (
          <li className="gear-card" key={s.slot}>
            <div className="gear-card-head">
              <span className="gear-card-slot">{s.slot}</span>
              <span className="gear-card-pct">{s.item.pct}%</span>
            </div>
            {s.item.id ? (
              <a className="gear-card-item"
                 href={`https://${whDomain}/item=${s.item.id}`}
                 target="_blank"
                 rel="noopener"
                 data-wowhead={`item=${s.item.id}${whDomainAttr}`}>{s.item.name}</a>
            ) : (
              <span className="gear-card-item">{s.item.name}</span>
            )}
            {s.enchant ? (
              <div className="gear-card-enchant">
                <span className="enchant-tag">{window.t('ench')}</span>
                <span className="enchant-name">{s.enchant.name}</span>
                <span className="enchant-pct">{s.enchant.pct}%</span>
              </div>
            ) : (
              <div className="gear-card-enchant placeholder">
                <span className="enchant-tag dim">—</span>
                <span className="enchant-name dim">{window.t('noEnch')}</span>
              </div>
            )}
          </li>
        ))}
      </ul>
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
window.GearPanel = GearPanel;
