import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { useRuntimeConfig } from '@/presentation/contexts/ConfigContext';

/**
 * Generic observation fetcher — cookie-auth, enveloped-error aware.
 * The dashboard never invents data: query errors render as "unavailable".
 */
export function useObservationFetch<T>(
  path: string | null,
): UseQueryResult<T, Error> {
  const config = useRuntimeConfig();
  return useQuery<T, Error>({
    queryKey: ['observation', path],
    enabled: path !== null,
    refetchOnWindowFocus: false,
    retry: 1,
    staleTime: 30_000,
    queryFn: async () => {
      const res = await fetch(`${config.observationApiPath}${path ?? ''}`, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) {
        let detail = `${res.status}`;
        try {
          const body = (await res.json()) as { error?: { message?: string } };
          detail = body.error?.message ?? detail;
        } catch {
          // non-JSON error body
        }
        throw new Error(detail);
      }
      return (await res.json()) as T;
    },
  });
}
