import React, { useEffect, useMemo } from 'react';
import { ReactFlow, Controls, Background, NodeProps, Handle, Position, Panel, useReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { EvidenceGraph } from '../../types/api';
import { transformEvidenceGraph } from '../../utils/graph-layout';
import { motion } from 'framer-motion';
import { FileText, ShieldCheck, TriangleAlert } from 'lucide-react';
import { documentLabel } from '../../utils/format';

function EvidenceNode({ data }: NodeProps) {
  const { title, confidence, score, document_id } = data as { title: string, confidence: number, score: number, document_id: string };
  
  const isPruned = confidence < 0.45;
  const isHighConfidence = confidence > 0.8;
  const baseColor = isHighConfidence ? 'var(--color-success)' : isPruned ? 'var(--color-danger)' : 'var(--color-warning)';
  const confidencePercent = Math.round(confidence * 100);
  
  return (
    <motion.div 
      initial={{ scale: 0.94, opacity: 0 }}
      animate={{ scale: 1, opacity: isPruned ? 0.4 : 1 }}
      className={`evidence-node ${isPruned ? 'evidence-node-pruned' : ''}`}
      style={{
        boxShadow: !isPruned ? `0 14px 36px -24px ${baseColor}` : 'none',
        borderLeftColor: baseColor,
      }}
      title={title}
    >
      <Handle type="target" position={Position.Left} className="graph-handle" />
      <div className="flex items-start gap-3">
        <div className="evidence-node-icon">
          <FileText size={15} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="evidence-node-kicker">{documentLabel(document_id)}</div>
          <div className="evidence-node-title">{title}</div>
        </div>
      </div>
      <div className="evidence-node-meter">
        <div className="h-full rounded-full" style={{ width: `${confidencePercent}%`, backgroundColor: baseColor }} />
      </div>
      <div className="evidence-node-footer">
        <span className={isHighConfidence ? 'text-[var(--color-success)]' : isPruned ? 'text-[var(--color-danger)]' : 'text-[var(--color-warning)]'}>
          {isPruned ? <TriangleAlert size={12} /> : <ShieldCheck size={12} />}
          {confidencePercent}% confidence
        </span>
        <span>score {score.toFixed(2)}</span>
      </div>
      <Handle type="source" position={Position.Right} className="graph-handle" />
    </motion.div>
  );
}

const nodeTypes = { evidence: EvidenceNode };

export function EvidenceGraphView({ graph }: { graph: EvidenceGraph }) {
  const { nodes, edges } = useMemo(() => transformEvidenceGraph(graph), [graph]);

  return (
    <div className="graph-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.18 }}
        minZoom={0.16}
        maxZoom={1.25}
        nodesConnectable={false}
        nodesDraggable
        elevateEdgesOnSelect
        onlyRenderVisibleElements
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(148, 163, 184, 0.14)" gap={22} size={1} />
        <Panel position="top-left" className="graph-panel">
          <span>{graph.nodes.length}</span> evidence
          <span className="graph-panel-separator" />
          <span>{graph.edges.length}</span> relations
        </Panel>
        <AutoFitGraph signature={`${graph.nodes.length}-${graph.edges.length}`} />
        <Controls className="graph-controls" showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

function AutoFitGraph({ signature }: { signature: string }) {
  const { fitView } = useReactFlow();

  useEffect(() => {
    const first = window.setTimeout(() => fitView({ padding: 0.18, duration: 220 }), 80);
    const second = window.setTimeout(() => fitView({ padding: 0.18, duration: 220 }), 420);
    return () => {
      window.clearTimeout(first);
      window.clearTimeout(second);
    };
  }, [fitView, signature]);

  return null;
}
