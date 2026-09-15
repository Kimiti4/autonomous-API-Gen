"use client";

import { useState } from "react";

import { workspacesApi, type WorkspaceQuery } from "@/lib/workspaces";

export function ServerWorkspacePanel({
  currentQuery
}: {
  currentQuery: WorkspaceQuery;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<"private" | "shared" | "public">(
    "private"
  );
  const [sharedWith, setSharedWith] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    setMessage(null);

    try {
      const workspace = await workspacesApi.create({
        name,
        description,
        query: currentQuery,
        visibility,
        shared_with: sharedWith
          .split(",")
          .map(item => item.trim())
          .filter(Boolean)
      });

      setMessage(`Saved workspace ${workspace.id}`);
      setName("");
      setDescription("");
      setSharedWith("");
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid">
      <div className="notice">
        Server workspaces are persistent operator artifacts. Do not store
        secrets in workspace names, descriptions, tags, or search queries.
      </div>

      <label className="grid">
        <span className="muted">Workspace name</span>
        <input
          value={name}
          onChange={event => setName(event.target.value)}
          placeholder="Priority investigation trace"
        />
      </label>

      <label className="grid">
        <span className="muted">Description</span>
        <input
          value={description}
          onChange={event => setDescription(event.target.value)}
          placeholder="Trace for VS1 priority evidence review"
        />
      </label>

      <label className="grid">
        <span className="muted">Visibility</span>
        <select
          value={visibility}
          onChange={event =>
            setVisibility(event.target.value as "private" | "shared" | "public")
          }
        >
          <option value="private">private</option>
          <option value="shared">shared</option>
          <option value="public">public</option>
        </select>
      </label>

      {visibility === "shared" ? (
        <label className="grid">
          <span className="muted">Shared with, comma-separated operator IDs</span>
          <input
            value={sharedWith}
            onChange={event => setSharedWith(event.target.value)}
            placeholder="operator-01, operator-02"
          />
        </label>
      ) : null}

      <button onClick={save} disabled={busy || name.trim().length === 0}>
        {busy ? "Saving…" : "Save server workspace"}
      </button>

      {message ? <div className="notice">{message}</div> : null}
    </div>
  );
}
