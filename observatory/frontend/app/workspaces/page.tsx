"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Section, StatusPill } from "@/components";
import {
  workspacesApi,
  type Workspace,
  type WorkspaceAuditRecord
} from "@/lib/workspaces";

export default function WorkspacesPage() {
  const [items, setItems] = useState<Workspace[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [auditOpenId, setAuditOpenId] = useState<string | null>(null);
  const [auditItems, setAuditItems] = useState<WorkspaceAuditRecord[]>([]);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [auditBusy, setAuditBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const nextItems = await workspacesApi.list();
      setItems(nextItems);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function remove(workspaceId: string) {
    if (!window.confirm("Delete this workspace?")) {
      return;
    }

    setBusy(true);
    setError(null);

    try {
      await workspacesApi.remove(workspaceId);
      if (auditOpenId === workspaceId) {
        setAuditOpenId(null);
      }
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleAudit(workspaceId: string) {
    if (auditOpenId === workspaceId) {
      setAuditOpenId(null);
      return;
    }

    setAuditBusy(true);
    setAuditError(null);

    try {
      const records = await workspacesApi.audit(workspaceId);
      setAuditItems(records);
      setAuditOpenId(workspaceId);
    } catch (cause) {
      setAuditError(
        cause instanceof Error ? cause.message : "Audit unavailable");
      setAuditOpenId(null);
    } finally {
      setAuditBusy(false);
    }
  }

  if (error && !items) {
    return <div className="error">Workspaces unavailable: {error}</div>;
  }

  if (!items) {
    return <div className="muted">Loading workspaces…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section title="Server Workspaces">
        {items.length === 0 ? (
          <div className="empty">
            No server workspaces visible. Save a workspace from the Console.
          </div>
        ) : (
          <ul className="timeline">
            {items.map(workspace => (
              <li key={workspace.id} className="timeline-item">
                <div className="timeline-top">
                  <span>{workspace.name}</span>
                  <StatusPill status={workspace.visibility} />
                </div>

                <div className="timeline-summary">{workspace.description}</div>

                <div className="timeline-meta">
                  <span>owner {workspace.owner_id}</span>
                  <span>version {workspace.version}</span>
                  <span>
                    updated {new Date(workspace.updated_at).toLocaleString()}
                  </span>
                  <span>tags {workspace.tags.join(", ") || "none"}</span>
                  <span>
                    shared with {workspace.shared_with.join(", ") || "none"}
                  </span>
                </div>

                <div style={{ height: 8 }} />

                <div className="grid grid-3">
                  <Link href={`/console?workspace=${workspace.id}`}>
                    Apply in Console
                  </Link>

                  <a
                    href={workspacesApi.exportUrl(workspace.id)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Export
                  </a>

                  <button
                    onClick={() => remove(workspace.id)}
                    disabled={busy}
                    type="button"
                  >
                    Delete
                  </button>

                  <button
                    onClick={() => toggleAudit(workspace.id)}
                    disabled={auditBusy}
                    type="button"
                  >
                    {auditOpenId === workspace.id
                      ? "Hide audit"
                      : "Audit"}
                  </button>
                </div>

                {auditOpenId === workspace.id ? (
                  <div style={{ height: 8 }} />
                ) : null}

                {auditOpenId === workspace.id ? (
                  auditError ? (
                    <div className="error">{auditError}</div>
                  ) : auditItems.length === 0 ? (
                    <div className="empty">No audit records</div>
                  ) : (
                    <ul className="timeline">
                      {auditItems.map(record => (
                        <li key={record.id} className="timeline-item">
                          <div className="timeline-top">
                            <span className="timeline-time">
                              {new Date(
                                record.timestamp).toLocaleString()}
                            </span>
                            <span>{record.action}</span>
                          </div>

                          <div className="timeline-meta">
                            <span>actor {record.actor_id}</span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
