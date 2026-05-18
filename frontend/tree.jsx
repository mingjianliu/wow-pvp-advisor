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
            const pa = nodeXY(na);
            const pb = nodeXY(nb);
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
            const { x, y } = nodeXY(node);
            const st = stateFor(node.id);
            const role = st ? st.role : 'skip';
            const pickRate = st ? st.pickRate : 0;
            const heat = heatBucket(pickRate);
            const rankFlex = st && isRankFlex(node, st);
            const contestedTake = st && st.contested;
            const displayRank = st ? (st.rankDist ? modalRank(st) : st.pts) : 0;

            const onEnter = (e) => onHover({ node, state: st, x: e.clientX, y: e.clientY });
            const onMove = (e) => onHover({ node, state: st, x: e.clientX, y: e.clientY });

            return (
              <g key={node.id}
                className={`node-group ${role} ${rankFlex ? 'rank-flex' : ''} ${contestedTake ? 'contested-take' : ''}`}
                onMouseEnter={onEnter}
                onMouseMove={onMove}
                onMouseLeave={onLeave}
              >
                <NodeShape node={node} x={x} y={y} heat={heat} />
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
                {displayRank > 0 && (
                  <text className="node-points" x={x} y={y + 3}>
                    {displayRank}{node.maxPoints > 1 ? `/${node.maxPoints}` : ''}
                  </text>
                )}
                <text className="node-label" x={x} y={y + 32}>
                  {truncateLabel(node.name)}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}

function truncateLabel(s) {
  return s.length > 14 ? s.slice(0, 13) + '…' : s;
}

window.TalentTree = TalentTree;
window.isRankFlex = isRankFlex;
window.modalRank = modalRank;
