# ESAP-APP-001 — Android Field Inventory

**Status:** Proposed benchmark specification; awaiting independent review and hash freeze.
**Version:** 1.0.0
**Platform:** Native Android application (Kotlin, Jetpack Compose).
**Purpose:** A small, deterministic, source-backed end-to-end compiler benchmark. This specification is newly defined because repository searches did not identify an approved Android-specific ESAP-APP-001 problem statement or acceptance contract. It is not represented as a previously approved organizational requirement.

## Problem
Build a native Android application that lets a field worker maintain a local inventory of items on a device, without requiring a network connection. The benchmark evaluates whether a compiler can generate a functional app from a technology-neutral specification while preserving data, validation, navigation, and interaction semantics.

## User workflows
1. Open the app and view the inventory list.
2. Add an item with a name, quantity, and optional notes.
3. View an item's details.
4. Edit an existing item.
5. Delete an item after explicit confirmation.
6. Search items by case-insensitive name substring.
7. Close and relaunch the app; saved items remain.
8. Complete primary workflows while offline.
9. Receive clear validation feedback for invalid input and empty-state feedback when no items exist or a search has no matches.

## Data and validation
- id: generated stable unique identifier, not user-editable.
- name: required, trimmed, 1–80 characters.
- quantity: required integer, 0–100000 inclusive.
- notes: optional, trimmed, at most 500 characters.
- created_at: generated timestamp.
- updated_at: updated on successful edits.
Reject blank names, names over 80 characters, non-integer quantities, quantities outside the inclusive range, and notes over 500 characters. Invalid submissions must not mutate stored data.

## Constraints
- Native Android app; no web wrapper.
- Must function without network access; no network permission or network dependency is required.
- Local durable persistence is required. In-memory-only storage does not satisfy the benchmark.
- User-visible interactions must be real, not static mock controls.
- UI must expose loading, empty, validation-error, and operation-success/failure states as applicable.
- Data operations must survive activity recreation and process termination/relaunch.
- No account, cloud synchronization, role-based authorization, backend API, barcode scanning, camera, or multi-device sync is in scope.
- Database library is not prescribed; durability and correctness must be proven.
- Do not claim accessibility, security, performance, or production readiness beyond executed acceptance checks.

## Out of scope
Authentication, multi-user tenancy, cloud services, remote synchronization, analytics, advertising, payments, barcode/camera features, and release-store publication.

## Benchmark integrity
The problem statement, acceptance criteria, and manifest are the benchmark authority. Any semantic change requires a new version and new content hashes. Generated code, screenshots, fixtures, and backend implementation details are not authoritative inputs. No compiler may receive hidden acceptance logic unavailable to competing compiler paths.