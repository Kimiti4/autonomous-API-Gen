import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { loadRuntimeConfig, type DashboardRuntimeConfig } from '@/application/configLoader';

const ConfigContext = createContext<DashboardRuntimeConfig | null>(null);

export function ConfigProvider({ children }: { children: ReactNode }): JSX.Element {
  const [config, setConfig] = useState<DashboardRuntimeConfig | null>(null);

  useEffect(() => {
    let cancelled = false;
    void loadRuntimeConfig().then((cfg) => {
      if (!cancelled) setConfig(cfg);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (config === null) return <div className="p-8 text-slate-500">Loading configuration…</div>;
  return <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>;
}

export function useRuntimeConfig(): DashboardRuntimeConfig {
  const cfg = useContext(ConfigContext);
  if (cfg === null) throw new Error('useRuntimeConfig must be used within ConfigProvider');
  return cfg;
}
