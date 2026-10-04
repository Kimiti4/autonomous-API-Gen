# ESAP Software Marketplace — Design Boundary

The ESAP repository currently contains compiler/evolution/verification infrastructure and an interactive control surface; it does **not** currently contain a production commerce marketplace.

The intended marketplace is a separate commerce boundary for software that ESAP designs, generates, verifies, packages, and offers for sale.

## Required product lifecycle

`DESIGNED → GENERATED → VERIFIED → CERTIFIED → LISTED → PURCHASED → FULFILLED`

A product must never become sellable merely because code was generated.

## Required marketplace capabilities

- product/listing metadata and versioning
- verified artifact/package identity
- evidence and certification linkage
- pricing and currency
- license terms
- checkout/payment-provider boundary
- entitlement/order records
- secure artifact delivery
- update/version entitlement
- refunds/cancellations
- seller/creator identity
- abuse/fraud controls
- taxes/compliance boundary
- marketplace audit trail

## Boundary rule

Payment providers, tax engines, identity providers, storage/CDN, email, and payout systems are external adapters. They must not be embedded into the ESAP architectural source of truth.

The initial ESAP implementation therefore establishes **marketplace contracts and certification gates**, not a fake payment processor or fabricated live commerce capability.

## Gumroad-like target

The intended experience is creator-style publishing and direct digital delivery, but with a stronger evidence model:

**ESAP product → verified artifact → evidence/certification → listing → checkout → entitlement → secure delivery → updates/refunds**

A marketplace listing should expose what was actually verified, the exact product version, license, price, and limitations rather than making unsupported quality claims.
