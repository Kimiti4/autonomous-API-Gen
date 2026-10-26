# Technical Proposal

## Design, implementation and support of a payroll system

**Submitted to:** World Concern Development Organization, Nairobi, Kenya  
**Bidder:** Amos Kimiti Kariuki, independent individual bidder  
**Bidder eligibility:** The bidder reports that World Concern confirmed, through direct clarification, that an individual/sole-proprietor applicant may apply. This is eligibility to submit only, not a guarantee of award.  
**TOR deadline:** 28 October 2026  
**Date:** 26 October 2026  
**Status:** Submission draft for bidder review. See the separate financial proposal, TOR compliance matrix, implementation and acceptance plan, and evidence/risk register.

---

## 1. Executive summary

Amos Kimiti Kariuki proposes to design, implement, test and support a secure, web-based payroll system for World Concern's stated profile of approximately 50 employees across five offices in Kenya. The proposed system will address employee and employment records; payroll preparation, calculation and approval; statutory deductions and returns; payslips and employee self-service; cost-centre allocation; reporting; agreed HR/accounting data exchange; migration; training; and support.

This is a proposal to deliver a payroll system, not a claim that the complete system already exists. Tiannara ESAP is the proposed software-engineering platform. Verified evidence is limited to a bounded declared payroll HTTP contract exercised in CI for generated Python FastAPI, Elixir OTP and Rust Axum services. It does not establish complete payroll calculations, statutory compliance, production hosting/security, complete TOR coverage, a browser-to-live-API journey, or HR/accounting integration. Proposed functionality will be treated as delivered only when its agreed acceptance tests pass.

The provisional delivery plan is 18 weeks from contract start, dependent on World Concern's timely approvals, data, statutory review, integration access and payroll calendar. Two consecutive parallel payroll runs, independent calculation checks, statutory-source approval and management sign-off are required before production use. If those gates need more time, the schedule will move rather than waive them.

The separate financial proposal gives an indicative first-year planning estimate of **KES 1,670,000**: **KES 1,310,000** implementation plus **KES 360,000** combined annual recurring maintenance/support and indicative hosting, backups and monitoring. The hosting allowance is subject to provider quotation and technical/data-protection requirements; no provider is selected or contracted. This is not a supplier-backed fixed quote or spending ceiling; final price and tax treatment require approval and confirmation.

## 2. Bidder and evidence statement

The bidder is **Amos Kimiti Kariuki**, applying as an independent individual. No registered company, company number, VAT PIN, certification, prior payroll deployment, client reference or existing World Concern engagement is claimed. The bidder reports receiving direct clarification from World Concern that an individual applicant is eligible to apply. Procurement requirements and any additional tender documents remain controlling.

The relevant engineering evidence is [GitHub Actions run 40305413032](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/40305413032), on tested commit `254a540a12a909c068ee871a54e2f8d469090cab`. It executed a shared, bounded declared-payroll HTTP contract against generated Python, Elixir and Rust services. Its assertions cover the API slice only. It is not a complete payroll certification, production deployment, penetration test, statutory compliance opinion, database-backed persistence proof, or browser end-to-end test.

The platform's payroll readiness gate remains `NOT_CERTIFIED` when required source mappings, statutory authority evidence, independent calculation vectors, frontend evidence or backend-runtime evidence are absent. The remediation register continues to track W07 as in progress; Ruby and C# parity remain outstanding, while W12 executable-effects work and W13 frontend/live-API evidence are separate. This proposal does not claim Campaign A 78-trial certification or production readiness for any compiler backend.

## 3. Understanding of World Concern's requirement

The supplied TOR describes approximately 50 staff in five offices, including contract employees, short-term contract employees and interns. The requested outcome is reduced payroll effort and error, secure employee payroll information, reliable reports and payslips, statutory compliance, integration with existing HR/accounting systems, audit trails and salary/benefit allocation across multiple cost centres.

The TOR requests employee records and history; payroll components and adjustments; monthly, bi-weekly and weekly pay frequencies; statutory calculations and returns; payslips and ESS; reports and bank schedules; web and mobile access; role controls; backup/recovery; audit records; common data formats; training; support; upgrades; SLA and performance reviews.

The supplied TOR text has a Security Requirements heading without enumerated controls and omits sections 11–13. It does not identify the existing HR/accounting products, statutory rule versions, pay calendars, calculation tolerances or approved budget. The full TOR and these details must be confirmed before scope and fixed price are finalized.

## 4. Proposed solution and functional scope

The proposed target is a responsive web application for agreed current desktop and mobile browsers. Hosting provider/region, database, identity integration and technical topology will be selected after review of security, privacy, recovery, integration and cost requirements.

### 4.1 Employee and employment records

Maintain approved employee identity/contact and employment data, employment type and history, department, position, bank/payment instructions and document references. Use effective dates and restricted access for sensitive fields. Import and migration will use approved templates, validation, duplicate detection and signed control totals.

### 4.2 Payroll processing

Configure pay groups for the approved monthly, bi-weekly and weekly calendars. Support approved salary and earnings components; overtime; allowances and benefits; bonuses/incentives; loans and advances; leave deductions; arrears and back pay. Provide period opening, input validation, calculation preview, exception handling, maker-checker review, approval, locked results, and controlled correction/reversal.

Pay rules are not assumed by this proposal. World Concern must approve component definitions, eligibility, taxable treatment, prorating, rounding, effective dates and calculation examples before implementation.

### 4.3 Statutory calculations and returns

Implement only statutory schemes confirmed as applicable and approved by World Concern. Candidate schemes include PAYE, NSSF, SHIF, Affordable Housing Levy, pension arrangements and other applicable deductions/benefits. Effective-dated employee deductions and employer contributions/costs will be represented separately, including separate employee and employer treatment for the Affordable Housing Levy where applicable.

No numerical rates or tax bands are asserted here. Each scheme must have a dated authoritative source record, approved interpretation, independently reviewed test vectors and period coverage before the calculation is enabled for production. Filing/payment remains the employer's responsibility unless a separate authorized service is agreed.

### 4.4 Cost centres, payslips, ESS and reporting

Allocate salary and eligible benefits among approved cost centres by percentages or amounts. Enforce reconciliation to the full amount and block unresolved under- or over-allocation before approval.

Generate and retrieve period payslips, provide agreed employee document access, and route profile-change requests for approval. Leave-balance and leave-application functionality is limited to the workflow agreed at discovery and is not a claim to replace a complete HRIS.

Produce the agreed payroll and departmental summaries, statutory/tax and deduction reports, bank-transfer schedule, audit extracts and custom management outputs. Provide agreed CSV/Excel/PDF exports and import templates. The bank schedule is for review/export; direct payment initiation and custody of funds are excluded unless separately designed and contracted.

### 4.5 Integration

The estimate assumes one HR and one accounting data exchange using documented APIs or agreed structured files. The systems, data dictionaries, vendors, sandboxes, permissions, reconciliation rules and schedule are unknown and must be established at discovery. A file exchange is a fallback only if World Concern approves it; it is not represented as a live integration.

## 5. Security, privacy and operations

At discovery, agree the complete security requirements and data-flow design, then implement and test the accepted control set. Proposed controls include named accounts, least-privilege role-based access, separation of payroll preparation and approval, approval of employee changes, encrypted network access, protection of bank/identity data, restricted exports, audit records for sensitive actions, secrets management, dependency review and release-blocking vulnerability remediation.

Agree audit retention/access, backup frequency and protection, restore tests, incident contacts, breach handling, data retention/deletion, lawful processing roles, any data-processing agreement, and cross-border-transfer safeguards before real employee data is loaded. The hosting region may be Kenya or an appropriate East African region if a suitable provider satisfies the agreed requirements; otherwise an alternative region requires privacy and transfer review.

No data-residency guarantee, security certification, existing hosting contract, tested production deployment, fixed uptime or 24/7 helpdesk is claimed. Hosting provider, region, RPO/RTO, SLA and applicable service charges remain subject to confirmation and quote.

## 6. Delivery approach

The indicative schedule is 18 weeks from contract start, assuming timely decisions, source data, reviewer availability and system access. The detailed phases, owners, dependencies and acceptance evidence are in the separate Implementation and Acceptance Plan.

1. **Weeks 1–2: Discovery and scope baseline.** Review complete TOR, map requirements, confirm policies, payroll calendar, roles, cost centres, statutory-source plan, integrations, data migration and acceptance tests.
2. **Weeks 3–5: Architecture and data foundation.** Approve design, privacy/security controls, record structures, import templates, roles and backup/recovery plan.
3. **Weeks 6–9: Payroll and statutory rules.** Implement approved pay components, frequencies, deductions and adjustment workflows; validate statutory interpretations and independent vectors.
4. **Weeks 10–12: Costing, ESS and reporting.** Implement allocation/reconciliation, agreed employee workflows, payslips, reports and exports.
5. **Weeks 13–14: Migration and integration.** Reconcile test migration and agreed HR/accounting interfaces or approved file exchanges.
6. **Weeks 15–17: Verification and parallel runs.** Execute functional, security, statutory, browser, recovery, integration and export tests; complete two consecutive parallel payroll cycles and close material defects.
7. **Week 18: Release and handover.** Production deployment only after written acceptance; complete training, manuals, runbooks and support handover.

The schedule moves if actual payroll frequency, legal review, system access or defects prevent two complete parallel runs. Testing and acceptance gates are not shortened to preserve the indicative date.

## 7. Go-live conditions and acceptance

Production use requires: (1) a requirement-to-test traceability matrix and signed scope baseline; (2) World Concern approval of all statutory sources, effective dates, employee/employer treatment and independent calculation cases; (3) approved security/privacy design and no unresolved critical/high security issue unless explicitly risk-accepted in writing; (4) two consecutive reconciled parallel payroll runs with no unresolved material difference; (5) positive/negative authorization, audit and approval-separation tests; (6) signed migration and integration reconciliation; (7) report/payslip and export validation; (8) witnessed backup restore and browser tests; and (9) training, documentation and authorized management sign-off.

Calculation tolerances, rounding, payroll input cut-offs, browser matrix, support service levels, RPO/RTO and materiality thresholds must be agreed at discovery. Acceptance evidence is bound to the tested release and is not inferred from source-code generation or the separate API parity result.

## 8. Support, maintenance and continuity

The separate financial proposal includes provisional annual maintenance/support of KES 240,000. Proposed scope is agreed-business-hours operational support, corrective maintenance, minor improvements and statutory table updates after source review. It does not include unlimited enhancements or 24/7 coverage. Major legal changes, new modules/integrations and third-party charges require approval and separate pricing.

The SLA must define support hours, channel, severity, response targets, escalation, maintenance windows and exclusions. Indicative acknowledgement targets for discussion are four business hours for payroll-blocking priority-one issues, one business day for priority two and three business days for priority three during agreed support hours. These are not a currently contracted service commitment.

Before contract signature, agree software ownership, permitted use, source-code access/handover, configuration and documentation rights, data export, credentials, backup access, termination assistance and continuity arrangements if the individual bidder cannot provide a contracted service.

## 9. Assumptions and exclusions

The initial estimate assumes approximately 50 employees, five offices, one Kenyan employing/payroll entity, one initial migration from validated spreadsheet/CSV data, and one HR plus one accounting exchange. World Concern provides lawful, complete source data, payroll policies and baseline control totals; nominates payroll, finance, HR, security and acceptance reviewers; provides interface/vendor access; and approves statutory and security decisions in the agreed review period.

Excluded unless agreed in a signed change: direct bank payment initiation; a complete HRIS or time-and-attendance replacement; multiple entities or migrations beyond the agreed scope; additional interfaces/custom reports; historical-document digitization; statutory filing/payment on the employer's behalf; legal/tax opinions; 24/7 support; independent certifications; third-party email/SMS, vendor API, bank, licensing or premium hosting charges. Changes are scoped, priced and approved before implementation.

## 10. Bidder declaration

I submit this technical proposal as Amos Kimiti Kariuki, an independent individual bidder. The bidder reports receiving direct clarification that World Concern accepts individual applicants; this is not a guarantee of contract award. The application does not claim a registered company or assert that the proposed payroll system is already built, certified or production-ready. Commercial estimates and service terms are in the separate financial proposal and remain subject to confirmation and written agreement.

**Bidder:** Amos Kimiti Kariuki  
**Signature:** ______________________________  
**Date:** ______________________________  
**Telephone / email:** To be completed before submission
