interface Bucket {
  count: number;
  reset: number;
}

const buckets = new Map<string, Bucket>();

export function rateLimit(
  key: string,
  limit: number,
  windowMs: number
): boolean {
  const now = Date.now();
  const existing = buckets.get(key);

  if (!existing || now > existing.reset) {
    buckets.set(key, {
      count: 1,
      reset: now + windowMs
    });

    return true;
  }

  if (existing.count >= limit) {
    return false;
  }

  existing.count += 1;
  return true;
}
