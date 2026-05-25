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

const TRANSLATIONS = {
  'en_US': {
    class: 'Class', spec: 'Spec', bracket: 'Bracket',
    share: 'Share', count: 'Count', takes: 'Takes', flex: 'Flex',
    global: 'GLOBAL', same: 'same across all clusters', pvp: 'PvP Talents',
    slot: 'SLOT', modal: 'Modal pick', alts: 'Alternatives',
    core: 'CORE', contested: 'CLUSTER TAKE', skip: 'SKIP',
    rankDist: 'Rank distribution', notTaken: 'Not taken in this cluster',
    pickRate: 'Pick rate', overall: 'overall', inCluster: 'in cluster',
    variance: 'Cluster variance',
    tweaks: 'Tweaks', flexHighlight: 'Flex highlight', heatmap: 'Pick-rate heatmap',
    signature: 'Cluster signature', go: 'Go', selectSpec: 'Select Spec...', selectBracket: 'Select Bracket...',
    gear: 'Gear', avgIlvl: 'avg ilvl', topPick: 'top pick per slot', ench: 'ENCH', noEnch: 'no enchant',
  },
  'zh_CN': {
    class: '职业', spec: '专精', bracket: '赛制',
    share: '占比', count: '人数', takes: '核心', flex: '灵活',
    global: '全局', same: '所有流派通用', pvp: 'PvP 天赋',
    slot: '槽位', modal: '主流选择', alts: '备选',
    core: '核心', contested: '流派特色', skip: '未选取',
    rankDist: '点数分布', notTaken: '此流派未选取',
    pickRate: '选取率', overall: '总计', inCluster: '本流派',
    variance: '流派变体',
    tweaks: '设置', flexHighlight: '灵活高亮', heatmap: '热力图',
    signature: '流派特征', go: '前往', selectSpec: '选择专精...', selectBracket: '选择赛制...',
    gear: '装备', avgIlvl: '平均装等', topPick: '部位最佳选择', ench: '附魔', noEnch: '无附魔',
    
    // Classes
    'Death Knight': '死亡骑士', 'Demon Hunter': '恶魔猎手', 'Druid': '德鲁伊', 'Evoker': '唤魔师',
    'Hunter': '猎人', 'Mage': '法师', 'Monk': '武僧', 'Paladin': '圣骑士', 'Priest': '牧师',
    'Rogue': '潜行者', 'Shaman': '萨满祭司', 'Warlock': '术士', 'Warrior': '战士',

    // Specs
    'Blood': '鲜血', 'Frost': '冰霜', 'Unholy': '邪恶',
    'Havoc': '浩劫', 'Vengeance': '复仇',
    'Balance': '平衡', 'Feral': '野性', 'Guardian': '守护', 'Restoration': '恢复',
    'Devastation': '湮灭', 'Preservation': '恩护', 'Augmentation': '增辉',
    'Beast Mastery': '野兽控制', 'Marksmanship': '射击', 'Survival': '生存',
    'Arcane': '奥术', 'Fire': '火焰',
    'Brewmaster': '酒仙', 'Mistweaver': '织雾', 'Windwalker': '踏风',
    'Holy': '神圣', 'Protection': '防护', 'Retribution': '惩戒',
    'Discipline': '戒律', 'Shadow': '暗影',
    'Assassination': '奇袭', 'Outlaw': '狂徒', 'Subtlety': '敏锐',
    'Elemental': '元素', 'Enhancement': '增强',
    'Affliction': '痛苦', 'Demonology': '恶魔学识', 'Destruction': '毁灭',
    'Arms': '武器', 'Fury': '狂怒',

    // Brackets
    '2v2': '2v2', '3v3': '3v3', 'Solo Shuffle': '单排轮斗', 'RBG': '评级战场', 'Blitz': '战场闪电战',
  }
};

const getLocale = () => window.location.pathname.endsWith('_zh.html') ? 'zh_CN' : 'en_US';
const t = (key) => (TRANSLATIONS[getLocale()] || TRANSLATIONS['en_US'])[key] || key;
window.t = t;

const normalizeBracket = (b) => {
  if (b === 'Solo Shuffle' || b === 'shuffle') return 'solo-shuffle';
  if (b === 'Blitz' || b === 'battlegrounds/blitz') return 'blitz';
  return b.toLowerCase();
};

const buildHref = (cls, spec, bracket, locale) => {
  if (!cls || !spec || !bracket) return '#';
  
  // Normalize spec to slug: spec-class (e.g. restoration-shaman)
  let specSlug = spec.toLowerCase().replace(/ /g, '-');
  const classSlug = cls.toLowerCase().replace(/ /g, '-');
  if (!specSlug.includes(classSlug)) {
    specSlug = `${specSlug}-${classSlug}`;
  }
  
  const slug = specSlug + '_' + normalizeBracket(bracket);
  const suffix = (locale || getLocale()) === 'zh_CN' ? '_zh' : '';
  const filename = slug + suffix + '.html';
  
  // If served via local server, use absolute path to ensure on-demand gen hits the server
  if (window.location.protocol === 'http:' && window.location.hostname === 'localhost') {
    return `/pages/${filename}`;
  }
  return filename;
};

function classIconSlug(cls) {
  if (!cls) return 'unknown';
  return cls.toLowerCase().replace(/[\s-]/g, '');
}

const classIconUrl = (cls) =>
  `https://wow.zamimg.com/images/wow/icons/large/classicon_${classIconSlug(cls)}.jpg`;

function CrumbDrop({ trigger, active, align, children }) {
  return (
    <div className={`crumb-drop ${align === 'right' ? 'crumb-drop-right' : ''}`}>
      <span className={`crumb-trigger ${active ? 'active' : ''}`}>{trigger}</span>
      <div className="crumb-menu">{children}</div>
    </div>);

}

function autoClusterName(c) {
  if (c.name) return c.name;
  if (!c.takes || c.takes.length === 0) return 'Static';
  // Use top 2 distinguishing talents as the name
  return c.takes.slice(0, 2).map((t) => t.name.split(' ')[0]).join(' + ');
}

// Derive the per-node role (core/flex/skip) and rank for a cluster.
function deriveNodeMap(data, cluster) {
  const map = {};
  data.talents.core.forEach((t) => map[t.id] = { role: 'core', pts: t.pts, rankDist: t.rankDist, pickRate: t.pct, global: true, pickers: t.pickers });
  data.talents.flex.forEach((t) => map[t.id] = { role: 'flex', pickRate: t.pct, global: true, pickers: t.pickers });
  cluster.takes.forEach((t) => {
    map[t.id] = { ...map[t.id], role: 'core', pts: t.rank, contested: true, pickRate: t.pct, global: false, pickers: t.pickers };
  });
  cluster.skips.forEach((t) => {
    map[t.id] = { ...map[t.id], role: 'skip', contested: true, pickRate: t.pct, global: false, pickers: t.pickers };
  });
  if (cluster.flex_takes) {
    cluster.flex_takes.forEach((t) => {
      map[t.id] = { ...map[t.id], role: 'flex', contested: true, pickRate: t.pct, global: false, pickers: t.pickers };
    });
  }
  return map;
}

// Pick the hero tree whose nodeIds have the most overlap with the cluster's
// core+takes node IDs. Falls back to the right tree (Totemic for Resto Shaman).
// Also overrides the pickRate of the selected hero tree's nodes to 100% for this cluster.
function selectHeroTree(data, nodeMap) {
  const heroTrees = data.tree && data.tree.heroTrees;
  if (!heroTrees) return null;
  const dominated = (ht) => ht.nodeIds.filter((id) => nodeMap[id]).length;
  const selected = dominated(heroTrees.left) >= dominated(heroTrees.right) ?
    heroTrees.left : heroTrees.right;
  
  // Override nodeMap for the selected hero tree so tooltips show 100% (in cluster)
  selected.nodeIds.forEach(id => {
    if (nodeMap[id]) {
      nodeMap[id] = { ...nodeMap[id], pickRate: 100.0, global: false };
    } else {
      // If it wasn't even in global core (rare, but possible if hero tree is totally new)
      nodeMap[id] = { role: 'core', pts: 1, pickRate: 100.0, global: false };
    }
  });
  
  return selected;
}

function useTweaks(initial) {
  const [v, setV] = useState(() => {
    try {
      const saved = localStorage.getItem('wow-advisor-tweaks');
      return saved ? JSON.parse(saved) : initial;
    } catch (e) {return initial;}
  });
  const set = (k, val) => setV((prev) => {
    const next = { ...prev, [k]: val };
    localStorage.setItem('wow-advisor-tweaks', JSON.stringify(next));
    return next;
  });
  return [v, set];
}

function App() {
  const data = window.CLUSTER_DATA;
  
  // Immediately merge prefetched data into the persistent meta cache 
  // so it's ready before the first render.
  if (window.__talentMetaCache) {
    const cache = window.TalentMeta.getCache();
    Object.keys(window.__talentMetaCache).forEach(id => {
      if (!cache[id]) cache[id] = window.__talentMetaCache[id];
    });
  }

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
  const majorClusters = clusters;

  const [activeRank, setActiveRank] = useState(null);
  const [activePlayer, setActivePlayer] = useState(null);

  useEffect(() => {
    if (majorClusters.length > 0) {
      if (activeRank === null || !majorClusters.find((c) => c.rank === activeRank)) {
        setActiveRank(majorClusters[0].rank);
      }
    }
  }, [majorClusters, activeRank]);

  useEffect(() => {
    setActivePlayer(null);
  }, [data]);

  const cluster = majorClusters.find((c) => c.rank === activeRank) || majorClusters[0];

  // Derived node-state map for the active cluster.
  const nodeMap = useMemo(() => {
    if (activePlayer) {
      const map = {};
      const selectedNodes = new Set([
        ...(activePlayer.talent?.class_node_ids || []),
        ...(activePlayer.talent?.spec_node_ids || []),
        ...(activePlayer.talent?.hero_node_ids || []),
        ...Object.keys(activePlayer.talent?.node_ranks || {}).map(Number)
      ]);
      selectedNodes.forEach(nid => {
        const pts = activePlayer.talent?.node_ranks?.[nid] || 1;
        map[nid] = {
          role: 'core',
          pts: pts,
          pickRate: 100,
          global: false,
          pickers: [activePlayer]
        };
      });
      return map;
    }
    if (!cluster) return {};
    return deriveNodeMap(data, cluster);
  }, [data, cluster, activePlayer]);

  const playerGearGroup = useMemo(() => {
    if (!activePlayer) return null;
    const isZh = window.location.pathname.endsWith('_zh.html');
    const slotLabels = isZh ? {
      "head": "头部", "neck": "项链", "shoulder": "肩部", "back": "背部",
      "chest": "胸部", "wrist": "护腕", "hands": "手部", "waist": "腰部",
      "legs": "腿部", "feet": "脚部", "finger_1": "戒指 1", "finger_2": "戒指 2",
      "trinket_1": "饰品 1", "trinket_2": "饰品 2",
      "main_hand": "主手", "off_hand": "副手",
    } : {
      "head": "Head", "neck": "Neck", "shoulder": "Shoulder", "back": "Back",
      "chest": "Chest", "wrist": "Wrist", "hands": "Hands", "waist": "Waist",
      "legs": "Legs", "feet": "Feet", "finger_1": "Ring 1", "finger_2": "Ring 2",
      "trinket_1": "Trinket 1", "trinket_2": "Trinket 2",
      "main_hand": "Weapon", "off_hand": "Off-hand",
    };
    
    const slots = (activePlayer.gear || []).map(g => {
      const slotKey = g.slot.toLowerCase();
      const label = slotLabels[slotKey] || g.slot;
      return {
        slot: label,
        item: {
          id: g.item_id,
          name: g.item_name,
          pct: 100
        },
        enchant: g.enchant_id ? {
          id: g.enchant_id,
          name: g.enchant_name,
          pct: 100
        } : null
      };
    });
    
    return {
      gear: {
        avg_ilvl: activePlayer.ilvl,
        slots: slots
      },
      sample_size: 1
    };
  }, [activePlayer]);

  const clusterForRenderer = useMemo(() => {
    if (!cluster) return null;
    return { ...cluster, nodes: nodeMap, name: autoClusterName(cluster) };
  }, [cluster, nodeMap]);

  const heroTree = useMemo(() => {
    if (!cluster || !nodeMap) return null;
    return selectHeroTree(data, nodeMap);
  }, [data, nodeMap, cluster]);

  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tip, setTip] = useState(null);
  const [toast, setToast] = useState(null);
  
  const tipRef = React.useRef(null);
  const hideTipTimeout = React.useRef(null);

  const handleHover = (tipData) => {
    if (hideTipTimeout.current) clearTimeout(hideTipTimeout.current);
    tipRef.current = tipData;
    setTip(tipData);
  };

  const handleLeave = () => {
    if (hideTipTimeout.current) clearTimeout(hideTipTimeout.current);
    const currentTip = tipRef.current;
    const hasPickers = currentTip && currentTip.state && currentTip.state.pickers && currentTip.state.pickers.length > 0;
    const delay = hasPickers ? 2000 : 300;
    hideTipTimeout.current = setTimeout(() => {
      setTip(null);
      tipRef.current = null;
    }, delay);
  };

  const handlePlayerClick = (p) => {
    console.log("Player clicked:", p);
    const found = (data.players || []).find(
      (pl) => pl.name.toLowerCase() === p.n.toLowerCase() && pl.realm.toLowerCase() === p.r.toLowerCase()
    );
    if (found) {
      console.log("Player found:", found);
      setActivePlayer(found);
      setTip(null);
      tipRef.current = null;
    } else {
      console.error("Player not found in data.players:", p, "players count:", (data.players || []).length);
    }
  };

  const handleTooltipEnter = () => {
    if (hideTipTimeout.current) clearTimeout(hideTipTimeout.current);
  };

  // Keyboard nav — ← / → between clusters.
  useEffect(() => {
    function onKey(e) {
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
      const idx = majorClusters.findIndex((c) => c.rank === activeRank);
      if (idx === -1) return;
      if (e.key === 'ArrowRight') setActiveRank(majorClusters[(idx + 1) % majorClusters.length].rank);else
      if (e.key === 'ArrowLeft') setActiveRank(majorClusters[(idx - 1 + majorClusters.length) % majorClusters.length].rank);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [majorClusters, activeRank]);

  if (!cluster) return <div className="loading">Loading cluster data...</div>;

  const onCopy = () => {
    navigator.clipboard.writeText(cluster.canonical_code).catch(() => {});
    setToast('Build code copied');
    setTimeout(() => setToast(null), 1500);
  };

  return (
    <div className="app" data-screen-label="Talent cluster picker">
      <header className="topbar">
        <div className="brand">
          <img className="brand-mark"
               src={classIconUrl(navSelection.class)}
               alt={navSelection.class}
               style={{ '--class-color': (CLASSES[navSelection.class] && CLASSES[navSelection.class].color) || 'var(--accent)' }} />
        </div>
        <div className="crumb">
          <CrumbDrop trigger={t(navSelection.class)}>
            <div className="crumb-menu-title">{t('class')}</div>
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
                  <span className="cls-name" style={{ color: info.color }}>{t(cls)}</span>
                </a>
              )}
            </div>
          </CrumbDrop>
          <span className="sep">/</span>

          {navSelection.class ? (
            <CrumbDrop trigger={navSelection.spec ? t(navSelection.spec) : <span className="select-hint">{t('selectSpec')}</span>} active={!navSelection.spec}>
              <div className="crumb-menu-title">{t('spec')} · {t(navSelection.class)}</div>
              {(CLASSES[navSelection.class] ? CLASSES[navSelection.class].specs : []).map((sp) =>
                <a key={sp}
                   href="#"
                   onClick={(e) => {
                     e.preventDefault();
                     setNavSelection({ ...navSelection, spec: sp, bracket: null });
                   }}
                   className={`crumb-menu-item ${sp === navSelection.spec ? 'current' : ''}`}>
                  <span className="cls-dot" style={{ background: CLASSES[navSelection.class].color }}></span>
                  <span>{t(sp)}</span>
                </a>
              )}
            </CrumbDrop>
          ) : (
            <span className="crumb-trigger disabled">{t('spec')}</span>
          )}

          <span className="sep">/</span>

          {navSelection.spec ? (
            <CrumbDrop trigger={navSelection.bracket ? t(navSelection.bracket) : <span className="select-hint">{t('selectBracket')}</span>} active={!navSelection.bracket}>
              <div className="crumb-menu-title">{t('bracket')}</div>
              {BRACKETS.map((b) =>
                <a key={b}
                   href={isNavigating ? buildHref(navSelection.class, navSelection.spec, b) : "#"}
                   onClick={(e) => {
                     if (!isNavigating && b === navSelection.bracket) e.preventDefault();
                     setNavSelection({ ...navSelection, bracket: b });
                   }}
                   className={`crumb-menu-item ${b === navSelection.bracket ? 'current' : ''}`}>
                  <span className="bracket-tag">{t(b)}</span>
                </a>
              )}
            </CrumbDrop>
          ) : (
            <span className="crumb-trigger disabled">{t('bracket')}</span>
          )}

          {isNavigating && (
            <a className="nav-go-btn" href={buildHref(navSelection.class, navSelection.spec, navSelection.bracket)}>
              {t('go')} →
            </a>
          )}
        </div>

        <div className="topbar-right">
          <div className="lang-toggle">
            <a href={buildHref(data.specLabel.class, data.specLabel.spec, data.bracket, 'en_US')}
               className={`lang-btn ${getLocale() === 'en_US' ? 'active' : ''}`}>EN</a>
            <span className="lang-sep">|</span>
            <a href={buildHref(data.specLabel.class, data.specLabel.spec, data.bracket, 'zh_CN')}
               className={`lang-btn ${getLocale() === 'zh_CN' ? 'active' : ''}`}>ZH</a>
          </div>
        </div>

      </header>

      {activePlayer ? (
        <div className="player-view-banner">
          <div className="player-view-info">
            <span className="dot active"></span>
            Viewing Player: <strong style={{color: 'var(--accent)'}}>{activePlayer.name}-{activePlayer.realm}</strong> · Spec: <strong>{activePlayer.spec} {activePlayer.class}</strong> · Rating: <strong>{activePlayer.rating}</strong> · Item Level: <strong>{activePlayer.ilvl}</strong>
          </div>
          <button onClick={() => setActivePlayer(null)} className="btn-back">
            ← Back to Cluster View
          </button>
        </div>
      ) : (
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
              {c.count === 1 && <span className="tab-unique">UNIQUE</span>}
              <span className="tab-bar">
                <span className="tab-bar-fill" style={{ width: `${Math.min(100, c.pct * 4)}%` }}></span>
              </span>
            </button>
          )}
        </nav>
      )}

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
                  onHover={handleHover}
                  onLeave={handleLeave} />
                
                </div>
              )}
            </div>

            {!activePlayer && <GlobalPvpPanel data={data} onHover={handleHover} onLeave={handleLeave} />}
            <GearPanel group={activePlayer ? playerGearGroup : data} />
          </div>
        </section>

        <Sidebar
          cluster={cluster}
          group={data}
          onCopy={onCopy}
          heatmap={tweaks.heatmap}
          onHover={handleHover}
          onLeave={handleLeave}
          activePlayer={activePlayer}
          setActivePlayer={setActivePlayer}
          nodeMap={nodeMap} />
        
      </main>

      {tip && <Tooltip {...tip} onEnter={handleTooltipEnter} onLeave={handleLeave} region={data.region} onPlayerClick={handlePlayerClick} sampleSize={data.sample_size} />}
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
      state: { role: 'core', pts: 1, pickRate: p.pct, pickers: p.pickers || [] },
      x: e.clientX, y: e.clientY
    });
  };

  return (
    <div className="pvp-panel" data-screen-label="PvP talents (global)">
      <div className="pvp-head">
        <h3>{t('pvp')}</h3>
        <div className="stat">
          <span style={{ color: 'var(--flex)', marginRight: 8, fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.12em' }}>{t('global')}</span>
          <span>{t('same')} · n={data.sample_size.toLocaleString()}</span>
        </div>
      </div>
      <div className="pvp-grid">
        {modal.map((p, i) =>
        <div className="pvp-slot" key={p.id}
        onMouseEnter={(e) => onHoverPvp(e, p)}
        onMouseLeave={onLeave}>
            <span className="pvp-slot-tag">{t('slot')} {i + 1}</span>
            <div className="pvp-slot-pos">{t('modal')}</div>
            <div className="pvp-slot-name">{p.name}</div>
            <div className="pvp-slot-pct">{p.pct}<span className="unit">%</span></div>
          </div>
        )}
        <div className="pvp-alts">
          <div className="pvp-alts-head">{t('alts')} · {alts.length}</div>
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

function Tooltip({ node, state, x, y, onEnter, onLeave, region, onPlayerClick, sampleSize }) {
  const meta = window.useTalentMeta();
  const sid = node && node.spellId;
  const cacheKey = node && node.isEnchant ? `ench-${sid}` : sid;
  const m = cacheKey && meta.get(cacheKey);

  React.useEffect(() => { 
    if (cacheKey && !m?.descHtml) {
      // Only trigger fetch if NOT prefetched (though most are now)
      if (typeof cacheKey !== 'string' || !cacheKey.startsWith('ench-')) {
        window.TalentMeta.fetchDesc(cacheKey);
      }
    }
  }, [cacheKey, m?.descHtml]);

  const role = state ? state.role : 'skip';
  const isContested = state && state.contested;
  // Position to the right of cursor by default, but if it overflows the screen width,
  // place it to the left of the cursor instead.
  const TOOLTIP_W = 340;
  const TOOLTIP_H_EST = 320;
  const left = (x + 14 + TOOLTIP_W > window.innerWidth)
    ? Math.max(8, x - TOOLTIP_W - 14)
    : x + 14;
  const top = (y + 14 + TOOLTIP_H_EST > window.innerHeight)
    ? Math.max(8, y - TOOLTIP_H_EST - 14)
    : y + 14;
  const tooltipStyle = {
    left: left,
    top: top
  };
  const isMulti = node.maxPoints && node.maxPoints > 1;
  const rankDist = state && state.rankDist;
  const displayRank = state ? rankDist ? window.modalRank(state) : state.pts : 0;
  const rankFlex = state && window.isRankFlex(node, state);

  let tag = t('skip');
  if (role === 'core') tag = rankFlex ? `${t('core')} · RANK-FLEX` : isContested ? t('contested') : t('core');else
  if (role === 'flex') tag = t('flex');

  const armoryBase = `https://worldofwarcraft.blizzard.com/en-${region}/character/${region}/`;

  return (
    <div className="tooltip" style={tooltipStyle} onMouseEnter={onEnter} onMouseLeave={onLeave}>
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
            <span>{t('pickRate')} <span style={{fontSize: 10, color: 'var(--text-2)'}}>{state.global ? `(${t('overall')})` : `(${t('inCluster')})`}</span></span>
            <span className="v">{state.pickRate}%</span>
          </div>
          <div className="tooltip-bar">
            <div className="tooltip-bar-fill" style={{ width: `${state.pickRate}%` }}></div>
          </div>
          {state.pickers && state.pickers.length > 0 && state.pickers.length < (sampleSize || 100) && (
            <div className="tooltip-pickers">
              <div className="tooltip-pickers-title">Players picking this:</div>
              <div className="tooltip-pickers-list">
                {state.pickers.map((p, i) => (
                  <a key={i}
                     href="#"
                     onClick={(e) => {
                       e.preventDefault();
                       if (onPlayerClick) onPlayerClick(p);
                     }}
                     className="tooltip-picker-link">
                    {p.n}-{p.r}
                  </a>
                ))}
              </div>
            </div>
          )}
          {rankDist ?
        <>
              <div className="tooltip-rank-title">{t('rankDist')}</div>
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
                    <span className="lbl">{t('skip')}</span>
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
          <span>{t('notTaken')}</span>
        </div>
      }
    </div>);

}

try {
  ReactDOM.createRoot(document.getElementById('root')).render(<App />);
} catch (e) {
  console.error("React Render Error:", e);
  document.getElementById('root').innerHTML = `
    <div style="padding: 40px; color: #ff6b6b; font-family: sans-serif;">
      <h2>React Render Error</h2>
      <pre style="background: #1a1a1a; padding: 20px; border-radius: 8px; overflow: auto;">${e.stack || e.message}</pre>
      <p>Check the browser console for details.</p>
    </div>
  `;
}
