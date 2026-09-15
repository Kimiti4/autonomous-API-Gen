"use client";

import { useState } from "react";

export default function LoginPage() {
  const [operatorId, setOperatorId] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setBusy(true);
    setMessage(null);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          operator_id: operatorId,
          passphrase
        })
      });

      const body = await response.json().catch(() => ({}));

      if (!response.ok) {
        setMessage(body.error ?? "login_failed");
        return;
      }

      window.location.href = "/governance";
    } catch {
      setMessage("login_failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid">
      <section className="section">
        <div className="section-header">
          <h2>Operator Login</h2>
        </div>

        <div className="section-body">
          <form onSubmit={submit} className="grid">
            <label className="grid">
              <span className="muted">Operator ID</span>
              <input
                value={operatorId}
                onChange={event => setOperatorId(event.target.value)}
                placeholder="operator-01"
              />
            </label>

            <label className="grid">
              <span className="muted">Passphrase</span>
              <input
                type="password"
                value={passphrase}
                onChange={event => setPassphrase(event.target.value)}
              />
            </label>

            <button disabled={busy} type="submit">
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>

          {message ? <div className="error">{message}</div> : null}
        </div>
      </section>
    </div>
  );
}
