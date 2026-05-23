import { Node, Edge, Position } from '@xyflow/react';
import dagre from 'dagre';
import { QueryGraph, EvidenceGraph } from '../types/api';

type LayoutDirection = 'TB' | 'LR';

function getNodeSize(node: Node, direction: LayoutDirection) {
  const data = node.data as { kind?: string; width?: number; height?: number };
  if (typeof data.width === 'number' && typeof data.height === 'number') {
    return { width: data.width, height: data.height };
  }

  if (direction === 'LR') {
    return { width: 280, height: 126 };
  }

  if (data.kind === 'root') return { width: 250, height: 74 };
  if (data.kind === 'intent') return { width: 230, height: 66 };
  if (data.kind === 'constraint') return { width: 150, height: 150 };
  return { width: 132, height: 44 };
}

export function getLayoutedElements<T extends Node>(
  nodes: T[],
  edges: Edge[],
  direction: LayoutDirection = 'TB',
) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: direction === 'LR' ? 88 : 88,
    ranksep: direction === 'LR' ? 72 : 76,
    marginx: 40,
    marginy: 40,
  });

  nodes.forEach((node) => {
    const { width, height } = getNodeSize(node, direction);
    dagreGraph.setNode(node.id, { width, height });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const { width, height } = getNodeSize(node, direction);
    return {
      ...node,
      targetPosition: direction === 'LR' ? Position.Left : Position.Top,
      sourcePosition: direction === 'LR' ? Position.Right : Position.Bottom,
      position: {
        x: nodeWithPosition.x - width / 2,
        y: nodeWithPosition.y - height / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

export function transformQueryGraph(graph: QueryGraph): { nodes: Node[], edges: Edge[] } {
  const nodes: Node[] = graph.nodes.map(n => ({
    id: n.id,
    type: 'custom',
    position: { x: 0, y: 0 },
    data: {
      label: n.label,
      kind: n.kind,
      weight: n.weight,
      terms: n.terms,
      width: n.kind === 'root' ? 250 : n.kind === 'intent' ? 230 : 132,
      height: n.kind === 'root' ? 74 : n.kind === 'intent' ? 66 : 44,
    },
  }));

  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: `e-${i}-${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    label: formatRelation(e.relation),
    type: 'smoothstep',
    animated: e.relation === 'decomposes_to',
    style: { stroke: 'rgba(139, 92, 246, 0.78)', strokeWidth: 1.4 },
    labelStyle: { fill: 'var(--color-text-muted)', fontSize: 10, fontWeight: 600 },
    labelBgStyle: { fill: 'var(--color-bg-base)', fillOpacity: 0.94 },
    labelBgPadding: [8, 4],
    labelBgBorderRadius: 6,
  }));

  return getLayoutedElements(nodes, edges, 'TB');
}

export function transformEvidenceGraph(graph: EvidenceGraph): { nodes: Node[], edges: Edge[] } {
  const nodes: Node[] = graph.nodes.map(n => ({
    id: n.id,
    type: 'evidence',
    position: { x: 0, y: 0 },
    data: { 
      title: n.title, 
      confidence: n.confidence, 
      score: n.score, 
      document_id: n.document_id,
      width: 280,
      height: 126,
    },
  }));

  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: `e-${i}-${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    label: formatRelation(e.relation),
    type: 'smoothstep',
    animated: e.relation === 'cites' || e.relation === 'supports',
    style: { stroke: 'rgba(148, 163, 184, 0.48)', strokeWidth: 1.4 },
    labelStyle: { fill: 'var(--color-text-muted)', fontSize: 10, fontWeight: 600 },
    labelBgStyle: { fill: 'var(--color-bg-base)', fillOpacity: 0.96 },
    labelBgPadding: [8, 4],
    labelBgBorderRadius: 6,
  }));

  return getLayoutedElements(nodes, edges, 'LR');
}

function formatRelation(relation: string): string {
  return relation.replaceAll('_', ' ').toUpperCase();
}
