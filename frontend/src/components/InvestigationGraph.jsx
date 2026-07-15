/**
 * InvestigationGraph.jsx  — v2 (progressive, performant)
 *
 * Architecture:
 *  - Initial view: identity node + its direct neighbours only (1-hop from backend)
 *  - Expand: click a collapsed node to load its neighbours on demand
 *  - Node inspector stores only plain data (not live Cytoscape objects)
 *  - All Cytoscape mutations via cyRef.current, zero React state for graph state
 *  - Labels hidden until zoom > 0.6, scaled beyond 1.2
 *  - fcose layout runs only when topology changes, not on every interaction
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import cytoscape from 'cytoscape';
import {
  Search, Maximize2, ZoomIn, ZoomOut,
  Info, Activity, X, ChevronRight, Layers
} from 'lucide-react';

// ── fcose: register once at module level via dynamic import ──────────────────
let _layoutReady = null;
function getLayoutName() {
  if (!_layoutReady) {
    _layoutReady = import('cytoscape-fcose').then((mod) => {
      const fcose = mod.default || mod;
      try { cytoscape.use(fcose); } catch (_) { /* already registered */ }
      return 'fcose';
    }).catch(() => 'cose');
  }
  return _layoutReady;
}
// Kick off registration immediately so it's ready by the time we need it
getLayoutName();

// ── Visual config (pure data, never changes) ─────────────────────────────────
const NODE_CFG = {
  identity:    { bg: '#1FB6C9', border: '#0E8A9A', shape: 'ellipse',          icon: '👤', size: 72 },
  device:      { bg: '#8BD450', border: '#5FA830', shape: 'roundrectangle',   icon: '📱', size: 52 },
  ip:          { bg: '#6366f1', border: '#4338ca', shape: 'diamond',          icon: '🌐', size: 48 },
  beneficiary: { bg: '#f59e0b', border: '#d97706', shape: 'roundrectangle',   icon: '👥', size: 52 },
  transaction: { bg: '#06b6d4', border: '#0891b2', shape: 'hexagon',          icon: '💸', size: 48 },
  alert:       { bg: '#ef4444', border: '#b91c1c', shape: 'star',             icon: '⚡', size: 56 },
  case:        { bg: '#8b5cf6', border: '#6d28d9', shape: 'roundrectangle',   icon: '📁', size: 48 },
  cluster:     { bg: '#4b5563', border: '#374151', shape: 'roundrectangle',   icon: '📂', size: 52 },
};
const EDGE_COLORS = { low: '#475569', medium: '#f59e0b', high: '#ef4444', critical: '#dc2626' };
const EDGE_WIDTHS  = { low: 1.5, medium: 2.5, high: 4, critical: 5 };

// ── Stylesheet (built once, never rebuilt) ───────────────────────────────────
const STYLESHEET = (() => {
  const base = [
    {
      selector: 'node',
      style: {
        'width': 'data(size)', 'height': 'data(size)',
        'background-color': 'data(bg)',
        'border-color': 'data(borderColor)',
        'border-width': 3,
        'shape': 'data(shape)',
        'label': 'data(label)',
        'font-size': 10,
        'font-family': 'IBM Plex Mono, monospace',
        'text-valign': 'bottom', 'text-halign': 'center',
        'text-margin-y': 5,
        'text-wrap': 'wrap', 'text-max-width': 90,
        'color': '#e2e8f0',
        'text-background-color': 'rgba(7,16,30,0.82)',
        'text-background-opacity': 1,
        'text-background-padding': '3px',
        'text-background-shape': 'roundrectangle',
        'min-zoomed-font-size': 6,
        'transition-property': 'opacity, border-width, border-color',
        'transition-duration': '120ms',
        'z-index': 1,
      }
    },
    // collapsed node indicator
    { selector: 'node[collapsed="true"]', style: { 'border-style': 'dashed', 'border-width': 2, 'opacity': 0.8 } },
    { selector: 'node.root', style: { 'border-width': 5, 'border-color': '#fff', 'z-index': 10 } },
    { selector: 'node.highlighted', style: { 'border-width': 5, 'border-color': '#fff', 'opacity': 1, 'z-index': 5 } },
    { selector: 'node.faded',       style: { 'opacity': 0.12 } },
    { selector: 'node.selected',    style: { 'border-color': '#ffffff', 'border-width': 5, 'z-index': 8 } },
    {
      selector: 'edge',
      style: {
        'width': 'data(width)',
        'line-color': 'data(color)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'triangle',
        'arrow-scale': 0.7,
        'curve-style': 'bezier',
        'label': '',               // edge labels off by default — too noisy
        'opacity': 0.7,
        'transition-property': 'opacity, width',
        'transition-duration': '120ms',
        'z-index': 0,
      }
    },
    { selector: 'edge.highlighted', style: { 'opacity': 1, 'width': 'data(widthHL)', 'z-index': 4 } },
    { selector: 'edge.faded',       style: { 'opacity': 0.05 } },
  ];
  // risk-level border tint
  base.push({ selector: 'node[risk="high"]',     style: { 'border-color': '#ef4444', 'border-width': 4 } });
  base.push({ selector: 'node[risk="critical"]', style: { 'border-color': '#dc2626', 'border-width': 5 } });
  return base;
})();

// ── API helpers (colocated, not in api.js to avoid circular dep) ─────────────
const API = '/api';
async function apiFetch(path) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

// ── Convert a single GraphNode/GraphEdge from API into Cytoscape element data ─
function nodeElement(n) {
  const cfg = NODE_CFG[n.type] || NODE_CFG.identity;
  return {
    group: 'nodes',
    data: {
      id: n.id,
      label: n.label,
      sublabel: n.sublabel || '',
      nodeType: n.type,
      risk: n.risk || 'low',
      payload: n.data || {},
      bg: cfg.bg,
      borderColor: cfg.border,
      shape: cfg.shape,
      icon: cfg.icon,
      size: cfg.size,
      // expandable initially for non-root types that could have neighbours
      collapsed: (n.type !== 'identity') ? 'true' : 'false',
    }
  };
}

function edgeElement(e) {
  const color = EDGE_COLORS[e.risk] || EDGE_COLORS.low;
  const width  = EDGE_WIDTHS[e.risk]  || 1.5;
  return {
    group: 'edges',
    data: {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      edgeType: e.type,
      risk: e.risk || 'low',
      color,
      width,
      widthHL: Math.max(width * 2, 4),
    }
  };
}

// ── Run layout (only when topology actually changed) ─────────────────────────
function runLayout(cy, layoutName, fit = false) {
  const layout = cy.layout(layoutName === 'fcose' ? {
    name: 'fcose',
    quality: 'default',        // 'proof' is too slow for interaction
    randomize: false,
    animate: true,
    animationDuration: 400,
    fit,
    padding: 60,
    nodeDimensionsIncludeLabels: false,
    packComponents: true,
    nodeRepulsion: 4500,
    idealEdgeLength: 50,
    edgeElasticity: 0.45,
    gravity: 0.25,
    numIter: 1200,
    tile: true,
    gravityRange: 3.5,
  } : {
    name: 'cose',
    animate: true,
    animationDuration: 400,
    fit,
    padding: 60,
    nodeRepulsion: 6000,
    idealEdgeLength: 100,
    edgeElasticity: 100,
    gravity: 80,
    numIter: 800,
    randomize: false,
  });
  layout.run();
  return layout;
}



// ── Node Inspector (stores PLAIN DATA, not live Cytoscape object) ─────────────
function NodeInspector({ nodeData, onClose }) {
  if (!nodeData) return null;
  const { nodeType, label, sublabel, risk, payload } = nodeData;
  const cfg = NODE_CFG[nodeType] || NODE_CFG.identity;
  const riskColor = EDGE_COLORS[risk] || EDGE_COLORS.low;

  return (
    <div className="graph-inspector" style={{ borderLeftColor: cfg.bg }}>
      <div className="graph-inspector__header">
        <span style={{ fontSize: '1.5rem', lineHeight: 1 }}>{cfg.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: '0.88rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</div>
          {sublabel && (
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono, monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sublabel}</div>
          )}
        </div>
        <span style={{ fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.06em', padding: '2px 6px', borderRadius: 4, border: `1px solid ${riskColor}`, color: riskColor, textTransform: 'uppercase', flexShrink: 0 }}>
          {risk}
        </span>
        <button className="btn btn--ghost" style={{ padding: '2px 4px' }} onClick={onClose}><X size={14} /></button>
      </div>

      <div style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase', margin: '10px 0 8px' }}>
        {nodeType.replace(/_/g, ' ')} · details
      </div>

      {Object.entries(payload || {}).map(([k, v]) => {
        if (v == null || v === '' || v === 0) return null;
        let display;
        if (typeof v === 'boolean') display = v ? 'Yes' : 'No';
        else if (Array.isArray(v)) display = v.length ? v.join(', ') : '—';
        else if (typeof v === 'number') display = v % 1 === 0 ? v.toString() : v.toFixed(3);
        else display = String(v);
        return (
          <div key={k} style={{ display: 'flex', gap: 8, padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <span style={{ color: 'var(--text-muted)', flex: '0 0 96px', textTransform: 'uppercase', fontSize: '0.62rem', letterSpacing: '0.04em' }}>{k.replace(/_/g, ' ')}</span>
            <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600, fontSize: '0.7rem', wordBreak: 'break-all', color: 'var(--text-primary)' }}>{display}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Legend ───────────────────────────────────────────────────────────────────
function GraphLegend() {
  const [open, setOpen] = useState(false);

  const renderShape = (s) => {
    const base = { width: 12, height: 12, background: s.bg, border: `2px solid ${s.border}`, display: 'inline-block', flexShrink: 0, boxSizing: 'border-box' };
    if (s.shape === 'ellipse') base.borderRadius = '50%';
    else if (s.shape === 'roundrectangle') base.borderRadius = 3;
    else if (s.shape === 'diamond') { base.transform = 'rotate(45deg) scale(0.85)'; }
    else if (s.shape === 'hexagon') { base.clipPath = 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)'; base.borderRadius = 0; }
    else if (s.shape === 'star') { base.clipPath = 'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)'; base.borderRadius = 0; }
    return <span style={base} />;
  };

  return (
    <div className="graph-legend-btn">
      <button className="btn btn--secondary btn--small" onClick={() => setOpen(o => !o)} style={{ gap: 5 }}>
        <Info size={12} /> Legend
      </button>
      {open && (
        <div className="graph-legend-panel">
          <div style={{ fontWeight: 700, fontSize: '0.73rem', marginBottom: 8, color: 'var(--text-primary)' }}>Node Types</div>
          {Object.entries(NODE_CFG).map(([type, s]) => (
            <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
              <div style={{ width: 14, height: 14, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {renderShape(s)}
              </div>
              <span style={{ fontSize: '0.7rem', textTransform: 'capitalize', color: 'var(--text-secondary)', flex: 1 }}>{type}</span>
              <span style={{ fontSize: '0.85rem' }}>{s.icon}</span>
            </div>
          ))}
          <div style={{ fontWeight: 700, fontSize: '0.73rem', margin: '10px 0 6px', color: 'var(--text-primary)' }}>Edge Risk</div>
          {Object.entries(EDGE_COLORS).map(([risk, color]) => (
            <div key={risk} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 3 }}>
              <span style={{ width: 22, height: 3, background: color, display: 'inline-block', borderRadius: 2 }} />
              <span style={{ fontSize: '0.7rem', textTransform: 'capitalize', color: 'var(--text-secondary)' }}>{risk}</span>
            </div>
          ))}
          <div style={{ marginTop: 10, padding: '8px 0 0', borderTop: '1px solid rgba(255,255,255,0.08)', fontSize: '0.65rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            <strong style={{ color: 'var(--text-secondary)' }}>Click a node</strong> to inspect.<br />
            <strong style={{ color: 'var(--text-secondary)' }}>Double-click</strong> to expand neighbours.
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function InvestigationGraph({ identityId, titleComponent }) {
  const containerRef  = useRef(null);
  const cyRef         = useRef(null);
  const layoutNameRef = useRef('cose');
  const loadedIds     = useRef(new Set());   // which node IDs we've expanded
  const isExpandingRef = useRef(false);      // prevent concurrent expansions

  // Plain serialisable data only — no live Cytoscape objects in React state
  const [inspectedData, setInspectedData] = useState(null);
  const [statsText, setStatsText]         = useState('');
  const [expandingId, setExpandingId]     = useState(null);
  const [searchText, setSearchText]       = useState('');

  const qc = useQueryClient();

  // ── Initial 1-hop graph ───────────────────────────────────────────────────
  const { data: seedData, isLoading, error } = useQuery({
    queryKey: ['graph-seed', identityId],
    queryFn: () => apiFetch(`/graph/${encodeURIComponent(identityId)}?depth=1`),
    staleTime: 120_000,
    retry: 1,
  });

  // ── Bootstrap Cytoscape once (no deps on state) ──────────────────────────
  useEffect(() => {
    if (!containerRef.current || !seedData) return;
    if (cyRef.current) return;   // already initialised

    let alive = true;

    getLayoutName().then((name) => {
      if (!alive || !containerRef.current) return;
      layoutNameRef.current = name;

      const elements = [
        ...seedData.nodes.map(nodeElement),
        ...seedData.edges.map(edgeElement),
      ];

      const cy = cytoscape({
        container: containerRef.current,
        elements,
        style: STYLESHEET,
        layout: { name: 'preset' },   // positions set by layout below
        minZoom: 0.08,
        maxZoom: 6,
        wheelSensitivity: 0.25,
        boxSelectionEnabled: false,
        selectionType: 'single',
      });

      // Mark root node
      cy.getElementById(identityId).addClass('root');
      // Mark seed nodes as loaded
      loadedIds.current.add(identityId);

      // Run initial layout
      runLayout(cy, name, true);



      // ── Click (single tap) → inspect only, NO layout ─────────────────────
      cy.on('tap', 'node', (e) => {
        const n = e.target;
        // Store ONLY plain serialisable data — never the Cytoscape object itself
        setInspectedData({
          nodeType: n.data('nodeType'),
          label:    n.data('label'),
          sublabel: n.data('sublabel'),
          risk:     n.data('risk'),
          payload:  n.data('payload'),   // already a plain object
        });

        // Highlight neighbourhood using Cytoscape API only — no React state for this
        cy.batch(() => {
          cy.elements().removeClass('highlighted faded selected');
          const hood = n.closedNeighborhood();
          cy.elements().not(hood).addClass('faded');
          hood.addClass('highlighted');
          n.addClass('selected');
        });
      });

      // ── Double-tap → expand neighbours ───────────────────────────────────
      cy.on('dblclick', 'node', (e) => {
        const n = e.target;
        const nid = n.data('id');
        const ntype = n.data('nodeType');

        // Only expandable types
        if (!['identity', 'alert', 'device', 'ip', 'cluster'].includes(ntype)) return;
        if (loadedIds.current.has(nid) || isExpandingRef.current) return;

        isExpandingRef.current = true;
        setExpandingId(nid);

        qc.fetchQuery({
          queryKey: ['graph-expand', nid],
          queryFn: () => apiFetch(`/graph/expand/${encodeURIComponent(nid)}`),
          staleTime: 120_000,
        }).then((expansion) => {
          if (!cyRef.current) return;
          loadedIds.current.add(nid);
          n.data('collapsed', 'false');

          const existingIds = new Set(cy.nodes().map(nd => nd.id()));
          const existingEdgeIds = new Set(cy.edges().map(ed => ed.id()));

          const newNodes = expansion.nodes.filter(nd => !existingIds.has(nd.id)).map(nodeElement);
          const newEdges = expansion.edges.filter(ed => !existingEdgeIds.has(ed.id)).map(edgeElement);

          if (newNodes.length === 0 && newEdges.length === 0) {
            setExpandingId(null);
            isExpandingRef.current = false;
            return;
          }

          cy.add([...newNodes, ...newEdges]);

          // Layout only the new subgraph + their direct neighbourhood
          const newNodeIds = new Set(newNodes.map(nd => nd.data.id));
          const subgraph = cy.nodes().filter(nd => newNodeIds.has(nd.id()) || nd.id() === nid).closedNeighborhood();

          const subLayout = subgraph.layout({
            name: layoutNameRef.current === 'fcose' ? 'fcose' : 'cose',
            animate: true,
            animationDuration: 350,
            fit: false,
            padding: 40,
            nodeRepulsion: 4500,
            idealEdgeLength: 50,
            gravity: 0.25,
            numIter: 600,
            randomize: false,
            packComponents: true,
          });
          subLayout.run();
          subLayout.on('layoutstop', () => {
            updateStats(cy);
            setExpandingId(null);
            isExpandingRef.current = false;
          });
        }).catch(() => {
          setExpandingId(null);
          isExpandingRef.current = false;
        });
      });

      // ── Background tap → clear ─────────────────────────────────────────
      cy.on('tap', (e) => {
        if (e.target === cy) {
          cy.elements().removeClass('highlighted faded selected');
          setInspectedData(null);
        }
      });

      cyRef.current = cy;
      updateStats(cy);
    });

    return () => {
      alive = false;
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seedData]);   // only re-init when seed data changes (i.e., different identity)

  function updateStats(cy) {
    setStatsText(`${cy.nodes().length} nodes · ${cy.edges().length} edges`);
  }

  // ── Search (pure Cytoscape API, no state for highlight) ──────────────────
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    
    cy.batch(() => {
      cy.elements().removeClass('highlighted faded selected');
      if (!searchText.trim()) return;
      const q = searchText.toLowerCase();
      const matches = cy.nodes().filter(n =>
        (n.data('label') || '').toLowerCase().includes(q) ||
        (n.data('sublabel') || '').toLowerCase().includes(q) ||
        (n.data('nodeType') || '').toLowerCase().includes(q)
      );
      if (matches.length > 0) {
        cy.elements().addClass('faded');
        matches.closedNeighborhood().removeClass('faded').addClass('highlighted');
        matches.addClass('selected highlighted');
      }
    });
  }, [searchText]);

  // ── Toolbar actions ───────────────────────────────────────────────────────
  const fitScreen = useCallback(() => cyRef.current?.fit(undefined, 60), []);
  const zoomIn    = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() * 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  }, []);
  const zoomOut   = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() * 0.76, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  }, []);
  const clearAll  = useCallback(() => {
    cyRef.current?.elements().removeClass('highlighted faded selected');
    setInspectedData(null);
    setSearchText('');
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────
  if (isLoading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, color: 'var(--text-muted)' }}>
      <div className="spinner" /> Building investigation graph…
    </div>
  );
  if (error) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 10, color: 'var(--text-muted)', padding: 40 }}>
      <Activity size={32} style={{ opacity: 0.4 }} />
      <span style={{ fontSize: '0.85rem' }}>Could not load graph: {error.message}</span>
    </div>
  );

  return (
    <div className="graph-workspace">
      {/* ── Toolbar ─────────────────────────────────────────────────────── */}
      <div className="graph-toolbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
          {titleComponent}
          {/* Search */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--input-bg)', borderRadius: 'var(--radius-sm)', border: 'var(--surface-border)', padding: '4px 10px' }}>
            <Search size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <input
              type="text"
              placeholder="Search nodes…"
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              style={{ background: 'transparent', border: 'none', outline: 'none', color: 'var(--text-primary)', fontSize: '0.76rem', width: 130 }}
            />
            {searchText && <button onClick={() => setSearchText('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 0, display: 'flex' }}><X size={11} /></button>}
          </div>

          {/* Stats */}
          {statsText && (
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono, monospace' }}>
              {statsText}
            </span>
          )}

          {/* Expanding indicator */}
          {expandingId && (
            <span style={{ fontSize: '0.72rem', color: 'var(--accent)', fontFamily: 'IBM Plex Mono, monospace', display: 'flex', alignItems: 'center', gap: 5 }}>
              <div className="spinner" style={{ width: 10, height: 10 }} /> expanding…
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <GraphLegend />
          <button className="btn btn--secondary btn--small" onClick={zoomIn}  title="Zoom In" ><ZoomIn  size={13} /></button>
          <button className="btn btn--secondary btn--small" onClick={zoomOut} title="Zoom Out"><ZoomOut size={13} /></button>
          <button className="btn btn--secondary btn--small" onClick={fitScreen} title="Fit to Screen"><Maximize2 size={13} /></button>
          {(inspectedData || searchText) && (
            <button className="btn btn--ghost btn--small" onClick={clearAll}><X size={12} /> Clear</button>
          )}
        </div>
      </div>

      {/* ── Hint bar ────────────────────────────────────────────────────── */}
      <div style={{ padding: '4px 14px', background: 'rgba(99,102,241,0.07)', borderBottom: '1px solid rgba(99,102,241,0.12)', fontSize: '0.65rem', color: 'var(--text-muted)', display: 'flex', gap: 16 }}>
        <span><strong style={{ color: 'var(--text-secondary)' }}>Click</strong> to inspect &nbsp;·&nbsp; <strong style={{ color: 'var(--text-secondary)' }}>Double-click</strong> identity/alert/device/IP to expand &nbsp;·&nbsp; <strong style={{ color: 'var(--text-secondary)' }}>Scroll</strong> to zoom &nbsp;·&nbsp; <strong style={{ color: 'var(--text-secondary)' }}>Drag</strong> to pan or move nodes</span>
      </div>

      {/* ── Canvas ──────────────────────────────────────────────────────── */}
      <div className="graph-container-outer">
        <div ref={containerRef} className="graph-canvas" />

        {/* Node Inspector (floats over canvas) */}
        {inspectedData && (
          <NodeInspector
            nodeData={inspectedData}
            onClose={() => {
              cyRef.current?.elements().removeClass('highlighted faded selected');
              setInspectedData(null);
            }}
          />
        )}
      </div>
    </div>
  );
}
