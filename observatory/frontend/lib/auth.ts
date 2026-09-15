import crypto from "crypto";
import { cookies } from "next/headers";

export interface OperatorSession {
  sub: string;
  role: string;
  clearance: string;
  iat: number;
  exp: number;
}

export const SESSION_COOKIE_NAME = "observatory_operator_session";

const SESSION_TTL_MS = 8 * 60 * 60 * 1000;

function base64url(input: string | Buffer): string {
  return Buffer.from(input).toString("base64url");
}

function getSessionSecret(): string | null {
  return process.env.OBSERVATORY_SESSION_SECRET || null;
}

export function encodeSession(session: OperatorSession): string {
  const secret = getSessionSecret();

  if (!secret) {
    throw new Error("OBSERVATORY_SESSION_SECRET is not configured");
  }

  const body = base64url(JSON.stringify(session));

  const signature = crypto
    .createHmac("sha256", secret)
    .update(body)
    .digest("base64url");

  return `${body}.${signature}`;
}

export function decodeSession(token: string): OperatorSession | null {
  const secret = getSessionSecret();

  if (!secret) {
    return null;
  }

  const [body, signature] = token.split(".");

  if (!body || !signature) {
    return null;
  }

  const expected = crypto
    .createHmac("sha256", secret)
    .update(body)
    .digest("base64url");

  const providedBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expected);

  if (providedBuffer.length !== expectedBuffer.length) {
    return null;
  }

  if (!crypto.timingSafeEqual(providedBuffer, expectedBuffer)) {
    return null;
  }

  try {
    const parsed = JSON.parse(
      Buffer.from(body, "base64url").toString("utf-8")
    ) as OperatorSession;

    if (typeof parsed.exp !== "number") {
      return null;
    }

    if (Date.now() > parsed.exp) {
      return null;
    }

    if (typeof parsed.sub !== "string") {
      return null;
    }

    if (typeof parsed.clearance !== "string") {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}

export function getSession(): OperatorSession | null {
  const token = cookies().get(SESSION_COOKIE_NAME)?.value;

  if (!token) {
    return null;
  }

  return decodeSession(token);
}

export function createSessionToken(
  operatorId: string,
  clearance: string
): string {
  const now = Date.now();

  return encodeSession({
    sub: operatorId,
    role: clearance,
    clearance,
    iat: now,
    exp: now + SESSION_TTL_MS
  });
}

export function sessionTtlSeconds(): number {
  return SESSION_TTL_MS / 1000;
}
