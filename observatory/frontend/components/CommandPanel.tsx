"use client";

import { useCallback, useEffect, useState } from "react";

import {
  allowedActionsForClearance,
  type CommandAction
} from "@/lib/commands";

interface AuthStatus {
  authenticated: boolean;
  operator_id: string | null;
  clearance: string | null;
  command_proxy_enabled: boolean;
}

export function CommandPanel() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [action, setAction] = useState<CommandAction | "">("");
  const [targetId, setTargetId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refreshStatus = useCallback(async () => {
    try {
      const response = await fetch("/api/auth/status", {
        cache: "no-store"
      });

      const body = await response.json();

      setStatus(body);

      const allowed = allowedActionsForClearance(body.clearance ?? "observer");

      setAction(previous => {
        if (previous && allowed.includes(previous)) {
          return previous;
        }

        return allowed[0] ?? "";
      });
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  async function logout() {
    await fetch("/api/auth/logout", {
      method: "POST"
    });

    setStatus(null);
    setMessage(null);
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!action) {
      setMessage("Select a command.");
      return;
    }

    setBusy(true);
    setMessage(null);

    try {
      const response = await fetch("/api/observatory/command", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          action,
          params: targetId
            ? {
                target_id: targetId
              }
            : {}
        })
      });

      const body = await response.json().catch(() => ({}));

      if (!response.ok) {
        setMessage(body.error ?? "command_rejected");
        return;
      }

      setMessage(`Command request accepted: ${body.request_id ?? "pending"}`);
      setTargetId("");
    } catch {
      setMessage("command_submission_failed");
    } finally {
      setBusy(false);
    }
  }

  if (!status) {
    return <div className="muted">Checking operator session…</div>;
  }

  if (!status.command_proxy_enabled) {
    return (
      <div className="notice">
        Command proxy is disabled. Set OBSERVATORY_COMMAND_PROXY_ENABLED=true
        on the frontend server to enable governed command submission.
      </div>
    );
  }

  if (!status.authenticated) {
    return (
      <div className="notice">
        Command submission requires an operator session.{" "}
        <a href="/login">Sign in</a>.
      </div>
    );
  }

  const allowedActions = allowedActionsForClearance(status.clearance ?? "");

  if (allowedActions.length === 0) {
    return (
      <div className="notice">
        This operator session has no command authority.
      </div>
    );
  }

  return (
    <div className="grid">
      <div className="notice">
        Signed in as {status.operator_id} with clearance {status.clearance}.
        Commands are forwarded to the Observatory governance boundary and may
        still be rejected.
      </div>

      <form onSubmit={submit} className="grid">
        <label className="grid">
          <span className="muted">Command</span>
          <select
            value={action}
            onChange={event =>
              setAction(event.target.value as CommandAction | "")
            }
          >
            {allowedActions.map(allowedAction => (
              <option key={allowedAction} value={allowedAction}>
                {allowedAction}
              </option>
            ))}
          </select>
        </label>

        <label className="grid">
          <span className="muted">Target ID, optional</span>
          <input
            value={targetId}
            onChange={event => setTargetId(event.target.value)}
            placeholder="EV-002"
          />
        </label>

        <button disabled={busy} type="submit">
          {busy ? "Submitting…" : "Submit command request"}
        </button>
      </form>

      {message ? <div className="notice">{message}</div> : null}

      <button onClick={logout} type="button">
        Sign out
      </button>
    </div>
  );
}
