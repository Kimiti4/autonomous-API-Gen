import { useProjection } from '@/presentation/hooks/useProjection';
import { FacetsPanel } from '@/presentation/components/FacetsPanel';
import { EvolutionOverview } from '@/presentation/components/EvolutionOverview';
import { Header } from '@/presentation/components/Layout';

export function DashboardPage(): JSX.Element {
  const { state } = useProjection();
  return (
    <>
      <Header title="Dashboard" />
      <div className="space-y-6 p-6">
        <FacetsPanel state={state} />
        <EvolutionOverview state={state} />
      </div>
    </>
  );
}
