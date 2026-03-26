'use client';

import { useEffect, useMemo, useState } from 'react';

interface GraphNode {
  id: string;
  label: string;
}

interface GraphEdge {
  source: string;
  target: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphEdge[];
}

const fallbackData: GraphData = {
  nodes: [
    { id: 'omega', label: 'Ω' },
    { id: 'memory', label: 'Memory' },
    { id: 'voice', label: 'Voice' },
    { id: 'research', label: 'Research' },
  ],
  links: [
    { source: 'omega', target: 'memory' },
    { source: 'omega', target: 'voice' },
    { source: 'omega', target: 'research' },
  ],
};

export default function SovereignGraph() {
  const [data, setData] = useState<GraphData>(fallbackData);

  useEffect(() => {
    fetch('/graph/ace_graph_snapshot.json')
      .then(res => res.ok ? res.json() : null)
      .then((json: unknown) => {
        if (!json || typeof json !== 'object') return;
        const typed = json as { nodes?: Array<{ id: string; type?: string; label?: string }>; edges?: Array<{ from: string; to: string }> };
        const nodes = (typed.nodes ?? []).map(node => ({
          id: node.id,
          label: node.label ?? node.type ?? node.id,
        }));
        const links = (typed.edges ?? []).map(edge => ({ source: edge.from, target: edge.to }));
        if (nodes.length > 0 && links.length > 0) {
          setData({ nodes, links });
        }
      })
      .catch(() => {});
  }, []);

  const layout = useMemo(() => {
    const centerX = 160;
    const centerY = 160;
    const radius = 95;
    return data.nodes.map((node, index) => {
      if (index === 0) return { ...node, x: centerX, y: centerY };
      const angle = (index / (data.nodes.length - 1)) * Math.PI * 2;
      return {
        ...node,
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
      };
    });
  }, [data.nodes]);

  const nodeById = Object.fromEntries(layout.map(node => [node.id, node]));

  return (
    <svg viewBox="0 0 320 320" role="img" aria-label="OmegA sovereign graph" style={{ width: '100%', height: 'auto', display: 'block' }}>
      <defs>
        <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(196,181,253,0.95)" />
          <stop offset="100%" stopColor="rgba(139,92,246,0.1)" />
        </radialGradient>
      </defs>
      <rect width="320" height="320" rx="24" fill="rgba(2,2,12,0.95)" />
      {data.links.map((link, index) => {
        const source = nodeById[link.source];
        const target = nodeById[link.target];
        if (!source || !target) return null;
        return (
          <line
            key={`${link.source}-${link.target}-${index}`}
            x1={source.x}
            y1={source.y}
            x2={target.x}
            y2={target.y}
            stroke="rgba(196,181,253,0.25)"
            strokeWidth="1.2"
          />
        );
      })}
      {layout.map(node => (
        <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
          <circle r="18" fill="url(#nodeGlow)" />
          <circle r="8" fill="rgba(255,255,255,0.85)" />
          <text y="34" textAnchor="middle" fill="rgba(241,245,249,0.7)" fontSize="10" fontFamily="Space Grotesk, sans-serif">
            {node.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
