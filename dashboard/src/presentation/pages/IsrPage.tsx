import { Header } from '@/presentation/components/Layout';
import { IsrPanel } from '@/presentation/components/IsrPanel';

export function IsrPage(): JSX.Element {
  return (
    <>
      <Header title="Intent Structure Registry" />
      <div className="p-6">
        <IsrPanel />
      </div>
    </>
  );
}
