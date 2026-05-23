import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { QueryAnalysis } from '../../types/api';
import { BrainCircuit, GitMerge, Route, Target, Waves } from 'lucide-react';
import { displayLabel, percent } from '../../utils/format';

export function QueryRadarChart({ analysis }: { analysis: QueryAnalysis }) {
  const data = [
    { subject: 'Ambiguity', value: analysis.ambiguity_score * 100, fullMark: 100 },
    { subject: 'Complexity', value: analysis.complexity_score * 100, fullMark: 100 },
    { subject: 'Entity Density', value: Math.min((Number(analysis.signals.entity_pressure) || 0) * 20, 100), fullMark: 100 },
    { subject: 'Hop Depth', value: (analysis.required_hops / 4) * 100, fullMark: 100 },
    { subject: 'Comparative Signal', value: Math.min((Number(analysis.signals.comparative) || 0) * 100, 100), fullMark: 100 },
  ];

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[1.15fr_0.85fr]">
      <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Query Intelligence Vector</h3>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              Dimensional breakdown of routing and retrieval difficulty.
            </p>
          </div>
          <div className="rounded-md border border-[var(--color-accent-violet)] bg-[rgba(139,92,246,0.08)] px-3 py-1.5 text-xs font-semibold text-[var(--color-accent-violet)]">
            {displayLabel(analysis.query_type)}
          </div>
        </div>

        <div className="h-[440px]">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="72%" data={data}>
              <PolarGrid stroke="var(--color-border-subtle)" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: 'transparent' }} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--color-bg-panel)',
                  borderColor: 'var(--color-border-subtle)',
                  color: 'var(--color-text-primary)',
                  borderRadius: '8px',
                }}
                formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Score']}
              />
              <Radar name="Query" dataKey="value" stroke="var(--color-accent-cyan)" fill="var(--color-accent-violet)" fillOpacity={0.28} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="space-y-4">
        <InsightCard icon={<BrainCircuit size={16} />} label="Query Type" value={displayLabel(analysis.query_type)} />
        <InsightCard icon={<Route size={16} />} label="Retrieval Mode" value={displayLabel(analysis.retrieval_mode)} />
        <InsightCard icon={<Target size={16} />} label="Reranking Policy" value={displayLabel(analysis.reranking_policy)} />
        <InsightCard icon={<GitMerge size={16} />} label="Required Hops" value={analysis.required_hops} />
        <InsightCard icon={<Waves size={16} />} label="Complexity" value={percent(analysis.complexity_score)} accent />
        <InsightCard icon={<Waves size={16} />} label="Ambiguity" value={percent(analysis.ambiguity_score)} />
      </div>
    </div>
  );
}

function InsightCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] p-4">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
        <span className={accent ? 'text-[var(--color-accent-cyan)]' : 'text-[var(--color-accent-violet)]'}>{icon}</span>
        {label}
      </div>
      <div className={`mt-2 text-lg font-semibold ${accent ? 'text-[var(--color-accent-cyan)]' : 'text-[var(--color-text-primary)]'}`}>
        {value}
      </div>
    </div>
  );
}
