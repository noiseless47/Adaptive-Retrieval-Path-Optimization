import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { EvaluationReport } from '../../types/api';

export function MetricsBarChart({ report }: { report: EvaluationReport }) {
  const data = [
    {
      name: 'Run Aggregate',
      Precision: report.precision_at_k,
      Recall: report.recall_at_k,
      NDCG: report.ndcg_at_k,
      MRR: report.mrr,
    }
  ];

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
          barSize={40}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" vertical={false} />
          <XAxis dataKey="name" stroke="var(--color-text-muted)" tick={{ fontSize: 11 }} />
          <YAxis stroke="var(--color-text-muted)" domain={[0, 1]} tick={{ fontSize: 11 }} />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'var(--color-bg-panel)', 
              borderColor: 'var(--color-border-subtle)',
              color: 'var(--color-text-primary)',
              borderRadius: '8px'
            }} 
            cursor={{ fill: 'var(--color-border-subtle)', opacity: 0.2 }}
          />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          <Bar dataKey="Precision" fill="var(--color-accent-cyan)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Recall" fill="var(--color-accent-violet)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="NDCG" fill="var(--color-success)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="MRR" fill="var(--color-warning)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
