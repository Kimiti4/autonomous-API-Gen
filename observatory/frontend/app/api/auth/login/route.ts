import crypto from "crypto";
import { NextResponse } from "next/server";

import {
  SESSION_COOKIE_NAME,
  createSessionToken,
  sessionTtlSeconds
} from "@/lib/auth";
import { rateLimit } from "@/lib/rate-limit";

export const runtime = "nodejs";

function safeEqual(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);

  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }

  return crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function sanitizeOperatorId(value: unknown): string {
  const raw = String(value ?? "").trim().slice(0, 100);
  const normalized = raw.replace(/[^\w.-]/g, "-");

  return normalized || "operator";
}

export async function POST(request: Request) {
  if (!rateLimit("login:global", 5, 60_000)) {
    return NextResponse.json(
      { error: "too_many_login_attempts" },
      { status: 429 }
    );
  }

  const expectedPassphrase = process.env.OBSERVATORY_OPERATOR_PASSPHRASE;
  const sessionSecret = process.env.OBSERVATORY_SESSION_SECRET;

  if (!expectedPassphrase || !sessionSecret) {
    return NextResponse.json(
      { error: "operator_login_disabled" },
      { status: 403 }
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
  const passphrase = String(record.passphrase ?? "");

  if (!passphrase) {
    return NextResponse.json(
      { error: "passphrase_required" },
      { status: 400 }
    );
  }

  if (!safeEqual(passphrase, expectedPassphrase)) {
    return NextResponse.json(
      { error: "invalid_credentials" },
      { status: 401 }
    );
  }

  const rawClearance =
    process.env.OBSERVATORY_OPERATOR_CLEARANCE ?? "operator";

  const clearance = ["operator", "architect", "admin"].includes(rawClearance)
    ? rawClearance
    : "operator";

  const operatorId = sanitizeOperatorId(record.operator_id);
  const token = createSessionToken(operatorId, clearance);

  const response = NextResponse.json({
    ok: true,
    operator_id: operatorId,
    clearance
  });

  response.cookies.set(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: sessionTtlSeconds()
  });

  return response;
}
