/**
 * The predictive model's view of the same application (POST /api/v1/predict): its decision with
 * the 90% conformal set, default probability, the four dimension scores, reasons each way, missing
 * evidence, evidence freshness and what would change the answer. Shown beside the rule-based
 * assessment, never blended into it. Probabilities arrive as JSON numbers and are only formatted.
 */
import Decimal from 'decimal.js';
import type { PredictResponse } from '@/api/backend';
import { Card, CardHead } from '@/components/ui/Card';
import { Badge, type Tone } from '@/components/ui/StatusBadge';
import { SourceBadge } from '@/components/ui/SourceBadge';
import { Explain } from '@/features/explain/Explain';
import { rupees } from './parts';

const DECISION: Record<string, { tone: Tone; label: string }> = {
  ELIGIBLE: { tone: 'active', label: 'Eligible' },
  REVIEW: { tone: 'restricted', label: 'Review' },
  DECLINE_CANDIDATE: { tone: 'defaulted', label: 'Decline candidate' },
};

const DIMENSIONS = [
  { key: 'financial_capacity_score', label: 'Financial capacity' },
  { key: 'evidence_reliability_score', label: 'Evidence reliability' },
  { key: 'graph_reputation_score', label: 'Graph reputation' },
  { key: 'stress_resilience_score', label: 'Stress resilience' },
] as const;

const pctOf = (p: number, dp = 1) => `${new Decimal(String(p)).mul(100).toFixed(dp, Decimal.ROUND_HALF_EVEN)}%`;
const fixed = (v: number, dp = 1) => new Decimal(String(v)).toFixed(dp, Decimal.ROUND_HALF_EVEN);

function Factors({ title, items, tone }: { title: string; items: PredictResponse['explanation']['positive_factors']; tone: 'good' | 'bad' }) {
  return (
    <div>
      <p className={`eyebrow ${tone === 'good' ? '!text-active' : '!text-defaulted'}`}>{title}</p>
      {items.length ? (
        <ul className="mt-2 space-y-2">
          {items.map((f) => (
            <li key={f.code} className="flex items-start justify-between gap-3 text-[13px]">
              <span className="text-ink-2">{f.text}</span>
              <span className={`num shrink-0 font-mono text-[11.5px] ${tone === 'good' ? 'text-active' : 'text-defaulted'}`}>
                {f.log_odds > 0 ? '+' : '−'}
                {fixed(Math.abs(f.log_odds), 2)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-[13px] text-ink-3">None.</p>
      )}
    </div>
  );
}

export function ModelView({ m, live }: { m: PredictResponse; live: boolean }) {
  const p = m.prediction;
  const d = DECISION[p.decision] ?? { tone: 'plain' as Tone, label: p.decision.toLowerCase().replaceAll('_', ' ') };
  const r = m.counterfactual_remedy;
  const fresh = m.temporal_freshness;
  return (
    <Card className="p-6">
      <CardHead
        eyebrow="Predictive model · experimental"
        title="What the model expects"
        aside={
          <span className="flex items-center gap-2">
            <SourceBadge live={live} />
            <Badge tone={d.tone} className="text-[12.5px]">
              {d.label}
            </Badge>
          </span>
        }
      />
      <p className="mt-2 max-w-[80ch] text-[13.5px] text-ink-2">{m.explanation.summary}</p>

      <div className="mt-5 grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        <div>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
            <div>
              <dt className="eyebrow">
                <Explain id="defaultProbability">Default probability</Explain>
              </dt>
              <dd className="display num mt-1 text-[32px] leading-none">{pctOf(p.default_probability, 2)}</dd>
            </div>
            <div>
              <dt className="eyebrow">
                <Explain id="conformal">{pctOf(p.confidence_level, 0)} conformal set</Explain>
              </dt>
              <dd className="mt-1.5 flex flex-wrap gap-1">
                {p.conformal_set.map((x) => (
                  <Badge key={x} tone="plain" dot={false} className="font-mono">
                    {x}
                  </Badge>
                ))}
              </dd>
            </div>
            <div>
              <dt className="eyebrow">
                <Explain id="modelUncertainty">Model uncertainty</Explain>
              </dt>
              <dd className="num mt-1 font-mono text-[15px]">{fixed(p.epistemic_uncertainty, 2)}</dd>
            </div>
            <div>
              <dt className="eyebrow">
                <Explain id="modelScale">Model scale</Explain>
              </dt>
              <dd className="num mt-1 font-mono text-[15px]">
                {p.credit_score} <span className="text-[11px] text-ink-3">of 300-900, not a bureau score</span>
              </dd>
            </div>
          </dl>

          <div className="mt-6 space-y-2.5">
            {DIMENSIONS.map((x) => {
              const v = m.multidimensional_scores[x.key];
              return (
                <div key={x.key}>
                  <div className="flex justify-between text-[12.5px]">
                    <span className="text-ink-2">{x.label}</span>
                    <span className="num font-mono">{fixed(v)}</span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-paper-2">
                    <div className="h-full rounded-full bg-neel-700" style={{ width: `${Math.min(100, Math.max(0, v))}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="space-y-5">
          <div className="grid gap-5 sm:grid-cols-2">
            <Factors title="Lowers risk" items={m.explanation.positive_factors} tone="good" />
            <Factors title="Raises risk" items={m.explanation.risk_factors} tone="bad" />
          </div>
          {m.explanation.missing_information.length ? (
            <div>
              <p className="eyebrow">Missing evidence, disclosed</p>
              <ul className="mt-2 space-y-1.5">
                {m.explanation.missing_information.map((x) => (
                  <li key={x.code} className="flex items-start gap-2 text-[13px] text-ink-2">
                    <span className="hatch mt-1 size-3 shrink-0 rounded-[3px] border border-neel-200" />
                    {x.text}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="rounded-[10px] bg-paper-2/70 p-4 text-[13px]">
            <p className="eyebrow">What would change it</p>
            <p className="mt-2 text-ink-2">
              Up to <span className="num font-medium text-ink">{rupees(r.max_recommended_principal)}</span> over{' '}
              <span className="num font-medium text-ink">{r.recommended_tenure_months} months</span> at about{' '}
              <span className="num font-medium text-ink">{rupees(r.sustainable_emi)}</span> a month
              {r.required_additional_monthly_income ? (
                <>
                  , or <span className="num font-medium text-ink">{rupees(r.required_additional_monthly_income)}</span> more income a month
                </>
              ) : null}
              .
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-ink-2">
              {r.actionable_recommendations.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </div>
          <p className="text-[12px] text-ink-3">
            Evidence {fixed(fresh.evidence_age_months, 0)} months old · confidence {pctOf(fresh.composite_confidence, 0)}
            {fresh.staleness_warning ? <span className="text-restricted-ink"> · {fresh.staleness_warning}</span> : null}
          </p>
        </div>
      </div>
    </Card>
  );
}
