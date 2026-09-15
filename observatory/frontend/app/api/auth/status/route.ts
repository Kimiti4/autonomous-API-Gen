import { NextResponse } from "next/server";

import { getSession } from "@/lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const session = getSession();

  return NextResponse.json({
    authenticated: Boolean(session),
    operator_id: session?.sub ?? null,
    clearance: session?.clearance ?? null,
    command_proxy_enabled:
      process.env.OBSERVATORY_COMMAND_PROXY_ENABLED === "true"
  });
}
