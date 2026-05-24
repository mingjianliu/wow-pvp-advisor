// Tree renderer — converts (col, row) nodes + edges to SVG with diamond/circle shapes.
// Receives current cluster's node-state map so it can render core/flex/skip + rank-flex.

const COL_W = 70;
const ROW_H = 78;
const PAD_X = 36;
const PAD_Y = 28;

function nodeXY(node) {
  return {
    x: PAD_X + node.col * COL_W,
    y: PAD_Y + node.row * ROW_H,
  };
}

function isRankFlex(node, state) {
  if (!state || !state.rankDist || node.maxPoints < 2) return false;
  const total = state.rankDist.reduce((s, v) => s + v, 0);
  if (total <= 0) return false;
  const max = Math.max(...state.rankDist);
  // Rank-flex: no single rank dominates >= 75% of the picks
  return max / total < 0.75;
}

function modalRank(state) {
  if (!state.rankDist) return state.pts;
  let bestI = 0, bestV = -1;
  state.rankDist.forEach((v, i) => { if (v > bestV) { bestV = v; bestI = i; } });
  return bestI + 1;
}

function shapeFor(node, x, y, size) {
  if (node.type === 'diamond' || node.type === 'capstone') {
    const s = size;
    return `${x},${y - s} ${x + s},${y} ${x},${y + s} ${x - s},${y}`;
  }
  return null;
}

function NodeShape({ node, x, y, scale = 1, extraClass = '', heat }) {
  const r = (node.type === 'capstone' ? 20 : node.type === 'diamond' ? 16 : 15) * scale;
  if (node.type === 'diamond' || node.type === 'capstone') {
    return <polygon
      className={`node-shape ${extraClass}`}
      data-heat={heat}
      points={`${x},${y - r} ${x + r},${y} ${x},${y + r} ${x - r},${y}`}
    />;
  }
  return <circle className={`node-shape ${extraClass}`} data-heat={heat} cx={x} cy={y} r={r} />;
}

// Inside-shape icon — sized to fit comfortably inside circle (or inscribed
// square of a diamond) so the colored border remains visible as a frame.
function NodeIcon({ node, x, y, iconUrl }) {
  if (!iconUrl) return null;
  const baseR = node.type === 'capstone' ? 20 : node.type === 'diamond' ? 16 : 15;
  // For diamonds: side of inscribed square = r * sqrt(2) ≈ r * 1.414.  We
  // size the icon at ~r * 1.4 so it fills the diamond's interior; CSS
  // clip-path then trims the corners back to the diamond shape.
  const size = (node.type === 'diamond' || node.type === 'capstone' ? baseR * 1.45 : baseR * 1.7);
  const isDiamond = node.type === 'diamond' || node.type === 'capstone';
  return (
    <image
      className={`node-icon ${isDiamond ? 'diamond' : 'circle'}`}
      href={iconUrl}
      xlinkHref={iconUrl}
      x={x - size / 2}
      y={y - size / 2}
      width={size}
      height={size}
      preserveAspectRatio="xMidYMid slice"
    />
  );
}

// Pick-rate ring — a circumscribed arc whose length encodes pickRate %.
// We always use a circle (even for diamonds) so the visual cue is
// consistent across node shapes.
function PickRateRing({ node, x, y, pickRate, role }) {
  if (pickRate == null) return null;
  // Skip the ring when pick rate is essentially 100% — it'd just be a
  // closed circle, indistinguishable from a regular outline and adds noise.
  if (pickRate >= 99.5) return null;
  const baseR = node.type === 'capstone' ? 20 : node.type === 'diamond' ? 16 : 15;
  const r = baseR + 5;
  const circ = 2 * Math.PI * r;
  const len = Math.max(0.5, (circ * pickRate) / 100);
  return (
    <g className={`rate-ring rate-ring-${role}`} transform={`rotate(-90 ${x} ${y})`}>
      <circle cx={x} cy={y} r={r}
        className="rate-ring-track"
        fill="none" />
      <circle cx={x} cy={y} r={r}
        className="rate-ring-fill"
        fill="none"
        strokeDasharray={`${len} ${circ - len}`}
        strokeLinecap="round" />
    </g>
  );
}

function heatBucket(rate) {
  if (rate >= 95) return 5;
  if (rate >= 80) return 4;
  if (rate >= 65) return 3;
  if (rate >= 45) return 2;
  if (rate >= 25) return 1;
  return 0;
}

function TalentTree({ tree, cluster, onHover, onLeave, flexStyle, heatmap, showSignature }) {
  const widthCols = Math.max(...tree.nodes.map(n => n.col)) + 1;
  const heightRows = Math.max(...tree.nodes.map(n => n.row)) + 1;
  const W = PAD_X * 2 + (widthCols - 1) * COL_W;
  const H = PAD_Y * 2 + (heightRows - 1) * ROW_H;

  const meta = window.useTalentMeta();

  // Center any row that contains exactly one node across the tree's column
  // span — gives the hero tree's top/bottom singletons a balanced look.
  const effectiveCol = React.useMemo(() => {
    const rowsCountMap = {};
    tree.nodes.forEach(n => { rowsCountMap[n.row] = (rowsCountMap[n.row] || 0) + 1; });
    const cols = tree.nodes.map(n => n.col);
    const midCol = (Math.min(...cols) + Math.max(...cols)) / 2;
    return (n) => (rowsCountMap[n.row] === 1 ? midCol : n.col);
  }, [tree.id, tree.nodes]);
  const xyFor = (n) => ({
    x: PAD_X + effectiveCol(n) * COL_W,
    y: PAD_Y + n.row * ROW_H,
  });

  // Preload icons for every node in this tree on mount / when tree changes.
  React.useEffect(() => {
    const ids = tree.nodes.map(n => n.spellId).filter(Boolean);
    if (ids.length) window.TalentMeta.preload(ids);
  }, [tree.id]);

  const stateFor = (id) => cluster.nodes[id];

  const svgClass = [
    'tree-svg',
    flexStyle ? `flex-${flexStyle}` : '',
    heatmap ? 'heatmap' : '',
    showSignature ? 'show-signature' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className="tree-svg-wrap">
      <svg
        className={svgClass}
        width={W} height={H}
        viewBox={`0 0 ${W} ${H}`}
      >
        <g>
          {tree.edges.map(([a, b], i) => {
            const na = tree.nodes.find(n => n.id === a);
            const nb = tree.nodes.find(n => n.id === b);
            if (!na || !nb) return null;
            const pa = xyFor(na);
            const pb = xyFor(nb);
            const sa = stateFor(a);
            const sb = stateFor(b);
            let cls = 'edge';
            if (sa && sb) {
              if (sa.role === 'flex' || sb.role === 'flex') cls = 'edge flex';
              else cls = 'edge active';
            }
            return (
              <line key={i} className={cls}
                x1={pa.x} y1={pa.y} x2={pb.x} y2={pb.y}
              />
            );
          })}
        </g>

        <g>
          {tree.nodes.map((node) => {
            const { x, y } = xyFor(node);
            const st = stateFor(node.id);
            const role = st ? st.role : 'skip';
            const pickRate = st ? st.pickRate : 0;
            const heat = heatBucket(pickRate);
            const rankFlex = st && isRankFlex(node, st);
            const contestedTake = st && st.contested;
            const displayRank = st ? (st.rankDist ? modalRank(st) : st.pts) : 0;

            const onEnter = (e) => onHover({ node, state: st, x: e.clientX, y: e.clientY });

            return (
              <g key={node.id}
                className={`node-group ${role} ${rankFlex ? 'rank-flex' : ''} ${contestedTake ? 'contested-take' : ''}`}
                onMouseEnter={onEnter}
                onMouseLeave={onLeave}
              >
                <NodeShape node={node} x={x} y={y} heat={heat} />
                <NodeIcon node={node} x={x} y={y}
                  iconUrl={meta.get(node.spellId) && meta.get(node.spellId).icon} />
                {st ? <PickRateRing node={node} x={x} y={y} pickRate={pickRate} role={role} /> : null}
                {/* Inner dashed ring for rank-flex core nodes */}
                {rankFlex && (
                  <NodeShape
                    node={node} x={x} y={y}
                    scale={0.62}
                    extraClass="node-inner-ring"
                  />
                )}
                {/* Cluster-take accent ring for contested takes */}
                {contestedTake && !rankFlex && (
                  <NodeShape
                    node={node} x={x} y={y}
                    scale={0.55}
                    extraClass="node-signature-ring"
                  />
                )}
                {node.maxPoints > 1 && (
                  <g className="node-rank-badge">
                    <rect x={x + 10} y={y + 8} width={14} height={14} rx={3} />
                    <text x={x + 17} y={y + 18.5}>{displayRank}</text>
                  </g>
                )}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}

window.TalentTree = TalentTree;
window.isRankFlex = isRankFlex;
window.modalRank = modalRank;
