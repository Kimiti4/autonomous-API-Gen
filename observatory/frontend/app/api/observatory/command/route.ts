import { NextResponse } from "next/server";

import { getSession } from "@/lib/auth";
import { allowedActionsForClearance } from "@/lib/commands";
import { rateLimit } from "@/lib/rate-limit";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (process.env.OBSERVATORY_COMMAND_PROXY_ENABLED !== "true") {
    return NextResponse.json(
      { error: "command_proxy_disabled" },
      { status: 403 }
    );
  }

  const session = getSession();

  if (!session) {
    return NextResponse.json(
      { error: "unauthorized" },
      { status: 401 }
    );
  }

  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "invalid_request" },
      { status: 400 }
    );
  }

  const record = body as Record<string, unknown>;

  const action = String(record.action ?? "");
  const params =
    typeof record.params === "object" && record.params !== null
      ? (record.params as Record<string, unknown>)
      : {};

  const allowedActions = allowedActionsForClearance(session.clearance);

  if (!allowedActions.includes(action as never)) {
    return NextResponse.json(
      { error: "unsupported_action" },
      { status: 403 }
    );
  }

  if (!rateLimit(`command:${session.sub}`, 10, 60_000)) {
    return NextResponse.json(
      { error: "too_many_requests" },
      { status: 429 }
    );
  }

  const backendUrl =
    process.env.OBSERVATORY_BACKEND_URL ||
    process.env.NEXT_PUBLIC_OBSERVATORY_API_URL ||
    "http://127.0.0.1:8000";

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Actor-Id": session.sub,
    "X-Actor-Role": session.role,
    "X-Actor-Clearance": session.clearance
  };

  const backendToken = process.env.OBSERVATORY_BACKEND_TOKEN;

  if (backendToken) {
    headers["X-Observatory-Token"] = backendToken;
  }

  let upstream: Response;

  try {
    upstream = await fetch(`${backendUrl}/observatory/commands`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        action,
        params
      }),
      cache: "no-store"
    });
  } catch {
    return NextResponse.json(
      { error: "observatory_backend_unavailable" },
      { status: 502 }
    );
  }

  const payload = await upstream.json().catch(() => ({}));

  return NextResponse.json(payload, {
    status: upstream.status
  });
}
