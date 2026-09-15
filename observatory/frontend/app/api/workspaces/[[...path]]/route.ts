import { NextRequest, NextResponse } from "next/server";

import { getSession } from "@/lib/auth";

export const runtime = "nodejs";

type RouteContext = {
  params: {
    path?: string[];
  };
};

function proxyEnabled(): boolean {
  return process.env.OBSERVATORY_WORKSPACES_PROXY_ENABLED === "true";
}

async function proxyRequest(request: NextRequest, context: RouteContext) {
  if (!proxyEnabled()) {
    return NextResponse.json(
      { error: "workspace_proxy_disabled" },
      { status: 403 }
    );
  }

  const session = getSession();

  if (!session) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const backendUrl =
    process.env.OBSERVATORY_BACKEND_URL ||
    process.env.NEXT_PUBLIC_OBSERVATORY_API_URL ||
    "http://127.0.0.1:8000";

  const subPath = context.params.path?.join("/") ?? "";
  const search = request.nextUrl.search || "";

  const target = `${backendUrl}/observatory/workspaces${
    subPath ? `/${subPath}` : ""
  }${search}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Operator-Id": session.sub,
    "X-Operator-Role": session.role,
    "X-Operator-Clearance": session.clearance,
    "X-Operator-Roles": session.clearance === "admin"
      ? "global_workspace_admin,workspace_creator"
      : session.clearance === "auditor"
        ? "global_auditor"
        : "workspace_creator"
  };

  const backendToken = process.env.OBSERVATORY_BACKEND_TOKEN;

  if (backendToken) {
    headers["X-Observatory-Token"] = backendToken;
  }

  const init: RequestInit = {
    method: request.method,
    headers
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  let upstream: Response;

  try {
    upstream = await fetch(target, init);
  } catch {
    return NextResponse.json(
      { error: "workspace_backend_unavailable" },
      { status: 502 }
    );
  }

  const body = await upstream.text();

  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("content-type") || "application/json"
    }
  });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
