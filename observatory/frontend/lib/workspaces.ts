export interface WorkspaceQuery {
  q?: string;
  categories?: string[];
  severities?: string[];
  epistemic_statuses?: string[];
  since?: string;
  until?: string;
  limit?: number;
}

export interface Workspace {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  visibility: "private" | "shared" | "public";
  shared_with: string[];
  tags: string[];
  query: WorkspaceQuery;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface WorkspaceAuditRecord {
  id: string;
  workspace_id: string;
  actor_id: string;
  action: string;
  timestamp: string;
  details: Record<string, unknown>;
}

async function workspaceRequest<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(`/api/workspaces${path}`, {
    cache: "no-store",
    ...init
  });

  if (!response.ok) {
    let detail: unknown = response.statusText;

    try {
      detail = await response.json();
    } catch {
      // Ignore non-JSON error bodies.
    }

    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail)
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const workspacesApi = {
  list(): Promise<Workspace[]> {
    return workspaceRequest<Workspace[]>("");
  },

  get(workspaceId: string): Promise<Workspace> {
    return workspaceRequest<Workspace>(`/${encodeURIComponent(workspaceId)}`);
  },

  create(payload: {
    name: string;
    description?: string;
    query: WorkspaceQuery;
    visibility?: "private" | "shared" | "public";
    shared_with?: string[];
    tags?: string[];
  }): Promise<Workspace> {
    return workspaceRequest<Workspace>("", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  },

  update(
    workspaceId: string,
    payload: {
      name?: string;
      description?: string;
      query?: WorkspaceQuery;
      visibility?: "private" | "shared" | "public";
      shared_with?: string[];
      tags?: string[];
    }
  ): Promise<Workspace> {
    return workspaceRequest<Workspace>(`/${encodeURIComponent(workspaceId)}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  },

  remove(workspaceId: string): Promise<{ status: string; workspace_id: string }> {
    return workspaceRequest<{ status: string; workspace_id: string }>(
      `/${encodeURIComponent(workspaceId)}`,
      {
        method: "DELETE"
      }
    );
  },

  audit(workspaceId: string): Promise<WorkspaceAuditRecord[]> {
    return workspaceRequest<WorkspaceAuditRecord[]>(
      `/${encodeURIComponent(workspaceId)}/audit`
    );
  },

  exportUrl(workspaceId: string): string {
    return `/api/workspaces/${encodeURIComponent(workspaceId)}/export`;
  }
};
