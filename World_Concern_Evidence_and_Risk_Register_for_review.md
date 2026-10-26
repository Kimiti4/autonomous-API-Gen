# Evidence and Risk Register

**Purpose:** Keep proposal claims separate from proof, dependencies and unresolved risks. Status reflects evidence available for this submission draft, not a commitment that planned work is already complete.

## 1. Evidence register

| ID | Claim / area | Status | Evidence and boundary | Next proof required |
|---|---|---|---|---|
| E-01 | Generated Python FastAPI declared payroll HTTP contract | Demonstrated, bounded | Shared CI contract test in [run 40305413032](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/40305413032); only the tested routes/assertions | Full payroll tests, approved statutory vectors, production security and buyer UAT |
| E-02 | Generated Elixir OTP declared payroll HTTP contract | Demonstrated, bounded | Same run and shared contract; does not establish payroll compliance | Same additional evidence as E-01 |
| E-03 | Generated Rust Axum declared payroll HTTP contract | Demonstrated, bounded | Same run and shared contract; CI execution addresses Windows local linker limitation only for that run | Same additional evidence as E-01 |
| E-04 | Current tested CI revision | Demonstrated for API test | Tested SHA: `254a540a12a909c068ee871a54e2f8d469090cab`; workflow URL is retained above | Preserve downloaded artifact and workflow retention through buyer submission/record policy |
| E-05 | Complete World Concern payroll calculations | Not demonstrated | Payroll readiness gate is `NOT_CERTIFIED`; no full payroll candidate is certified | Build candidate, independent vectors, two parallel runs and management sign-off |
| E-06 | Current Kenyan statutory logic | Not demonstrated | No numerical statutory rates are asserted in this proposal | Source/version/effective date register, independent tests and designated reviewer approval for each scheme/period |
| E-07 | Full TOR traceability | In progress / proposed | Supplied TOR copy omits security controls and sections 11–13 | Obtain full TOR, approved mapping and signed scope |
| E-08 | World Concern HR/accounting integration | Not demonstrated | Products/interfaces are unidentified | Inventory systems, access, specifications, integration tests and finance sign-off |
| E-09 | Production security, privacy, hosting and backup recovery | Not demonstrated | No production deployment, provider contract, security certification or restore evidence claimed | Buyer-approved design, provider quote, security tests, restore test and written acceptance |
| E-10 | Frontend-to-live-API browser journey | Not demonstrated | Separate W13 workstream; parity API test is not browser E2E | Candidate-bound browser test and archived logs/artifacts |
| E-11 | Ruby/C# parity, W12 effects, Campaign A | Not demonstrated by cited API run | W07 remains in progress; W12 and Campaign A are separate; no 78/78 result inferred | Separate workstream-specific evidence and release gates |

## 2. Risk register

| ID | Risk | Likelihood / impact | Mitigation and gate | Owner |
|---|---|---|---|---|
| R-01 | Full security controls and TOR sections are missing from the supplied copy | High / High | Request complete TOR immediately; record each omission as a clarification; do not finalize scope/price without impact review | Bidder + World Concern procurement |
| R-02 | Individual-bidder eligibility is misunderstood or formal requirements differ | Medium / Critical | Bidder reports direct confirmation that individuals may apply; retain written confirmation if available and satisfy all application-document requirements; eligibility is not award | Bidder |
| R-03 | Provisional estimate differs from actual delivery/provider costs | High / High | Keep estimate non-binding until discovery and written approval; obtain provider/vendor quotes; change control before additional spend | Bidder + buyer |
| R-04 | VAT/tax status is unknown | Medium / High | Verify bidder's tax status and applicable treatment; show any tax separately; no invented PIN or tax claim | Bidder/accountant |
| R-05 | Statutory rates, legal interpretations or effective dates are incomplete/changed | High / Critical | Official versioned source register; separate employee deductions and employer costs; independent period-specific vectors; reviewer approval; block payroll production until passed | World Concern payroll reviewer + bidder |
| R-06 | Wrong payroll calculation causes under/over-payment or filing error | Medium / Critical | Approved independent expected cases, maker-checker control, two consecutive parallel runs, variance resolution and go-live hold | Payroll owner |
| R-07 | HR/accounting interfaces unavailable or more complex than assumed | High / High | Identify products and vendors in discovery; test environment/access; scope one interface each; approved file exchange only as an explicit fallback | Buyer system owners + bidder |
| R-08 | Employee bank/identity/payroll data is exposed | Medium / Critical | Least privilege, encrypted data paths, restricted exports, audit, agreed hosting/retention, security testing and no real data before approval | Security/privacy contact |
| R-09 | Cross-border hosting conflicts with privacy or transfer requirements | Medium / High | Data-flow and region review, transfer safeguards and written approval before production data; no residency guarantee asserted | Buyer privacy contact |
| R-10 | Provider cannot meet required recovery/availability | Medium / High | Agree RPO/RTO and SLA, compare provider quote/capability, conduct restore test, contingency and rollback plan | Buyer + bidder |
| R-11 | Two parallel payroll periods do not fit the provisional 18-week schedule | Medium / High | Schedule against real payroll calendar; extend timeline rather than skip a cycle or weaken acceptance | Project owner |
| R-12 | Single-person delivery/support creates continuity risk | Medium / High | Contract source-code/data export/handover, documentation, credential custody, named buyer counterpart, escalation/termination assistance; identify any subcontracting only with approval | Bidder + buyer |
| R-13 | Email/SMS, bank or vendor charges exceed estimate | Medium / Medium | Identify and price all third-party services before approval; exclude unquoted usage charges and get buyer authorization | Bidder |
| R-14 | Proposal overstates existing product maturity | Low / Critical | Maintain demonstrated/proposed/clarification/excluded labels; attach only exact API evidence; never claim certification or production readiness | Bidder |

## 3. Official-source verification plan

No rates or bands are supplied here. At implementation, confirm and retain official-source records for the rules applicable to each payroll period. Starting authorities include:

- [Kenya Revenue Authority (KRA)](https://www.kra.go.ke/) for PAYE guidance and applicable deductions.
- [NSSF Kenya employer information](https://www.nssf.or.ke/employers) and the current applicable contribution-rate notice, including the relevant 2026 Year 4 notice if effective for the period.
- [Social Health Authority (SHA)](https://sha.go.ke/) and applicable legal instruments for SHIF.
- [Kenya Law](https://new.kenyalaw.org/) for enacted legislation, amendments and regulations, including applicable Affordable Housing Levy instruments.

For each source capture the exact title, issuer, publication/version, retrieval date, source file or stable URL, SHA-256 where a retained copy is available, effective date range, applicability decision, interpretation notes, reviewer and independently checked examples. For Affordable Housing Levy, explicitly verify the employee deduction and employer contribution/employer cost separately. Confirm source values and legal interpretation with World Concern's designated qualified reviewer; this register is a validation plan, not legal advice or evidence that a current statutory table has already been certified.
