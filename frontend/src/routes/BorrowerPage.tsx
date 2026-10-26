import { useSnapshot } from '@/state/DemoProvider';
import { Card, CardHead } from '@/components/ui/Card';
import { ButtonLink } from '@/components/ui/Button';
import { IconArrowRight, IconShield } from '@/components/icons';
import { ScoreGauge } from '@/features/score/ScoreGauge';
import { UncertaintyPlot } from '@/features/score/UncertaintyPlot';
import { VouchesPanel } from '@/features/borrower/VouchesPanel';
import { LoanPanel } from '@/features/borrower/LoanPanel';
import { StrengthenPanel } from '@/features/borrower/StrengthenPanel';
import { PathList } from '@/features/graph/PathList';
import { PersonHeader } from '@/features/shared/PersonHeader';
import { fmt } from '@/lib/format';

export function BorrowerPage() {
  const s = useSnapshot();
  const node = s.nodes[s.borrowerId]!;
  const a = s.assessments[s.borrowerId];

  if (!a || !node.nullifier) return <NotSignedIn name={node.name} />;

  return (
    <div className="space-y-6">
      <PersonHeader node={node} seat="Borrower" />

      <div className="grid gap-5 lg:grid-cols-12">
        <Card className="p-7 lg:col-span-8">
          <ScoreGauge a={a} node={node} />
        </Card>
        <Card className="flex flex-col p-6 lg:col-span-4">
          <CardHead eyebrow="Two axes, never one number" title="Where you stand" />
          <div className="mt-3 flex-1">
            <UncertaintyPlot a={a} />
          </div>
          <p className="text-[12.5px] text-ink-3">
            {Number(a.sigma2) >= 0.99
              ? 'Top of the chart: we have no data on you yet. That is uncertainty, not risk.'
              : `Uncertainty is down to ${fmt(a.sigma2)}. Each verified source moves you lower.`}
          </p>
        </Card>

        <div className="lg:col-span-7">
          <VouchesPanel s={s} />
        </div>
        <div className="lg:col-span-5">
          <LoanPanel s={s} />
        </div>

        {a.paths.length > 0 ? (
          <Card className="p-6 lg:col-span-12">
            <CardHead eyebrow="Fully traceable" title="Why your score is what it is" />
            <div className="mt-4">
              <PathList a={a} s={s} self />
            </div>
          </Card>
        ) : null}

        <div className="lg:col-span-12">
          <StrengthenPanel s={s} />
        </div>
      </div>
    </div>
  );
}

function NotSignedIn({ name }: { name: string }) {
  return (
    <div className="mx-auto flex max-w-[520px] flex-col items-center py-24 text-center">
      <span className="grid size-14 place-items-center rounded-[14px] bg-neel-50 text-neel-700">
        <IconShield size={28} />
      </span>
      <h1 className="display mt-6 text-[34px] leading-tight">{name} hasn’t anchored an identity yet</h1>
      <p className="mt-3 text-ink-2">The borrower view opens once she signs in with her demo Aadhaar and becomes a node on the graph.</p>
      <ButtonLink to="/login" size="lg" className="mt-8" trailingIcon={<IconArrowRight size={17} />}>
        Go to sign-in
      </ButtonLink>
    </div>
  );
}
