import React, { useEffect, useMemo } from 'react';
import { ReactFlow, Controls, Background, NodeProps, Handle, Position, Panel, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { QueryGraph } from '../../types/api';
import { transformQueryGraph } from '../../utils/graph-layout';
import { motion } from 'framer-motion';
import { Braces, CircleDot, GitBranch, Tag } from 'lucide-react';

function QueryNode({ data, sourcePosition = Position.Bottom, targetPosition = Position.Top }: NodeProps) {
  const { label, kind, terms } = data as { label: string; kind: string; terms?: string[] };

  if (kind === 'constraint') {
    return (
      <motion.div initial={{ scale: 0.92, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="query-node-diamond">
        <Handle type="target" position={targetPosition} className="graph-handle" />
        <div className="query-node-diamond-inner">
          <Braces size={14} />
          <span>{label}</span>
        </div>
        <Handle type="source" position={sourcePosition} className="graph-handle" />
      </motion.div>
    );
  }

  const Icon = kind === 'root' ? CircleDot : kind === 'intent' ? GitBranch : Tag;
  const kindLabel = kind === 'root' ? 'Root query' : kind === 'intent' ? 'Sub-intent' : 'Entity';
  const nodeClass = kind === 'root' ? 'query-node query-node-root' : kind === 'intent' ? 'query-node query-node-intent' : 'query-node query-node-entity';

  return (
    <motion.div 
      initial={{ scale: 0.92, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={nodeClass}
      title={label}
    >
      <Handle type="target" position={targetPosition} className="graph-handle" />
      <div className="flex items-start gap-3">
        <div className="query-node-icon">
          <Icon size={15} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="query-node-kicker">{kindLabel}</div>
          <div className="query-node-label">{label}</div>
          {kind !== 'entity' && (
            <div className="query-node-meta">
              {terms?.length ?? 0} semantic terms
            </div>
          )}
        </div>
      </div>
      <Handle type="source" position={sourcePosition} className="graph-handle" />
    </motion.div>
  );
}

const nodeTypes = { custom: QueryNode };

export function QueryGraphView({ graph }: { graph: QueryGraph }) {
  const { nodes, edges } = useMemo(() => transformQueryGraph(graph), [graph]);

  return (
    <div className="graph-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.22 }}
        minZoom={0.18}
        maxZoom={1.35}
        nodesConnectable={false}
        nodesDraggable
        elevateEdgesOnSelect
        onlyRenderVisibleElements
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(148, 163, 184, 0.14)" gap={22} size={1} />
        <Panel position="top-left" className="graph-panel">
          <span>{graph.nodes.length}</span> nodes
          <span className="graph-panel-separator" />
          <span>{graph.edges.length}</span> links
        </Panel>
        <AutoFitGraph signature={`${graph.root_id}-${graph.nodes.length}-${graph.edges.length}`} />
        <Controls className="graph-controls" showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

function AutoFitGraph({ signature }: { signature: string }) {
  const { fitView } = useReactFlow();

  useEffect(() => {
    const first = window.setTimeout(() => fitView({ padding: 0.24, duration: 220 }), 80);
    const second = window.setTimeout(() => fitView({ padding: 0.24, duration: 220 }), 420);
    return () => {
      window.clearTimeout(first);
      window.clearTimeout(second);
    };
  }, [fitView, signature]);

  return null;
}
