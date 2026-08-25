/**
 * Evidence record reference — TypeScript mirror of the platform's
 * app/core/contracts/evidence.py (minimal identity + integrity fields).
 */
export interface EvidenceRecord {
  readonly evidenceId: string;
  /** SHA-256 hex digest of the canonical evidence content. */
  readonly contentHash: string;
}
