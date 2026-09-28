import { FormEvent, useEffect, useState } from 'react';

interface AuthGateProps {
  children: JSX.Element;
}

export function AuthGate({ children }: AuthGateProps): JSX.Element {
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetch('/auth/session', { credentials: 'same-origin', cache: 'no-store' })
      .then((response) => {
        if (active) setAuthenticated(response.ok);
      })
      .catch(() => {
        if (active) setAuthenticated(false);
      })
      .finally(() => {
        if (active) setChecking(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function login(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError('');
    const response = await fetch('/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey }),
    });
    setApiKey('');
    if (response.ok) {
      setAuthenticated(true);
      return;
    }
    setError('Authentication failed. Check the operator credential.');
  }

  if (checking) {
    return <main className="flex min-h-screen items-center justify-center bg-slate-50">Checking operator session…</main>;
  }

  if (!authenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
        <form onSubmit={login} className="w-full max-w-sm rounded border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-xl font-semibold text-slate-900">ESAP Operator Console</h1>
          <p className="mt-2 text-sm text-slate-600">
            Authenticate to access canonical read-only observations.
          </p>
          <label className="mt-5 block text-sm font-medium text-slate-700" htmlFor="operator-api-key">
            Operator credential
          </label>
          <input
            id="operator-api-key"
            type="password"
            autoComplete="current-password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            required
          />
          {error && <p role="alert" className="mt-2 text-sm text-red-700">{error}</p>}
          <button type="submit" className="mt-4 w-full rounded bg-brand-500 px-3 py-2 font-medium text-white">
            Sign in
          </button>
        </form>
      </main>
    );
  }

  return children;
}
