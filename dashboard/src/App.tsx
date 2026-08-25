import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from '@/presentation/components/Layout';
import { DashboardPage } from '@/presentation/pages/DashboardPage';
import { IsrPage } from '@/presentation/pages/IsrPage';
import { EvolutionPage } from '@/presentation/pages/EvolutionPage';
import { FitnessPage } from '@/presentation/pages/FitnessPage';
import { GovernancePage } from '@/presentation/pages/GovernancePage';
import { LineagePage } from '@/presentation/pages/LineagePage';

export default function App(): JSX.Element {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/isr" element={<IsrPage />} />
        <Route path="/evolution" element={<EvolutionPage />} />
        <Route path="/fitness" element={<FitnessPage />} />
        <Route path="/governance" element={<GovernancePage />} />
        <Route path="/lineage" element={<LineagePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
