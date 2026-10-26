# Implementation and Acceptance Plan

**Bidder:** Amos Kimiti Kariuki, independent individual bidder  
**Planning duration:** 18 weeks from contract start, conditional on timely inputs, reviews, access and the payroll calendar.  
**Release principle:** No production payroll until statutory, security, parallel-run, operational and management acceptance gates pass.

## 1. Governance and responsibilities

| Role | Proposed responsibility |
|---|---|
| World Concern project owner | Scope decisions, schedule, change approval and escalation |
| World Concern payroll reviewer | Payroll policies, statutory applicability and calculation-vector review |
| World Concern finance/accounting reviewer | Cost centres, accounting interface, bank schedule and reconciliation |
| World Concern HR/data owner | Employee data, employment policies, migration approval and ESS |
| World Concern security/privacy contact | Security requirements, hosting/data flows, access, retention and incident controls |
| Authorized management signatory | UAT, statutory, parallel-run and final go-live acceptance |
| Bidder/project implementer | Design/build, tests, evidence, issue reporting, training and handover within contracted scope |

Nominees and decision rights are confirmed at kickoff. Reviews are assumed within five business days; missed or delayed approvals re-baseline the schedule.

## 2. Phases, outputs and gates

| Phase | Indicative timing | Outputs | Exit criteria |
|---|---:|---|---|
| 1. Discovery and scope baseline | Weeks 1–2 | Complete TOR review; requirement traceability; employee/pay components; pay calendars; leave, loan and arrears policies; role and cost-centre inventory; statutory scheme/source register; security questions; integration and migration discovery; acceptance plan | Signed scope baseline, assumptions/exclusions, requirement matrix, source-validation plan and test/acceptance plan |
| 2. Architecture and data foundation | Weeks 3–5 | Logical/system architecture; hosting and data-flow options; employee/employment/department/position/bank/document records; roles; import templates; audit and backup/recovery design | Written design/security/privacy approval before sensitive real data |
| 3. Payroll and statutory rules | Weeks 6–9 | Frequency and component configuration; calculation/adjustment workflows; approved effective-dated statutory rules; test vectors and reviewer traceability | Each statutory rule has authoritative source/effective dates, independent expected results and named reviewer sign-off; no guessed values |
| 4. Costing, ESS and reports | Weeks 10–12 | Multi-cost-centre calculation/reconciliation; agreed employee/approver journeys; payslips; reports and CSV/Excel/PDF outputs | Component and role tests pass; report totals reconcile to test payroll; no cross-employee access |
| 5. Migration and integration | Weeks 13–14 | Test migration; data-quality/rejection report; HR/accounting API or approved file exchange; export mapping and reconciliation | Signed migration control totals, interface tests, rejected-record handling and finance reviewer approval |
| 6. Verification and parallel runs | Weeks 15–17 or as payroll calendar requires | Functional/security/privacy tests; browser/device tests; restore test; independent payroll cases; two consecutive parallel cycles; defect log | No unresolved material payroll difference; no unaccepted critical/high security finding; statutory reviewer and payroll owner sign-off |
| 7. Production release and handover | Indicative week 18, after gates | Approved deployment; admin/payroll training; user guidance; runbook; support contacts/SLA; data/configuration handover | Written management go-live acceptance and completed handover checklist |

The schedule is a planning baseline, not a reason to compress payroll cycles. If two complete payroll periods cannot be run by week 17, deployment and final acceptance move.

## 3. Proposed acceptance tests

### 3.1 Traceability and release identity

- Every mandatory TOR requirement maps to a testable deliverable or is explicitly excluded/deferred by written buyer approval.
- Test reports, statutory source records, parallel-run outputs and sign-offs identify the tested release/candidate version.
- No statement of completion is based solely on code generation, structural checks, or tests for a different release.

### 3.2 Payroll calculation

- World Concern approves employee populations, pay components, pay frequencies, dates, policy interpretation, rounding precision and tolerances before vectors are finalized.
- Independently authored test cases cover normal, boundary and exception cases for salary, overtime, allowances/benefits, bonuses, loans/advances, leave deductions, arrears and back pay.
- Expected results are documented separately from the application and reviewed by the designated payroll/accounting representative.
- Employee gross pay, each component, each deduction, net pay, employer contribution/cost and cost-centre totals reconcile to the approved expected values at the agreed precision.

### 3.3 Statutory rules

- For each applicable scheme, record authority, instrument/guidance title, version or source copy, source hash, publication and effective dates, applicability and reviewer.
- Include employee deductions and employer contributions/costs as separate values where the law/policy distinguishes them; explicitly test the Affordable Housing Levy split where applicable.
- Test thresholds, reliefs, taxable benefits, rounding, caps/floors, period boundaries and transitions as applicable, using reviewer-approved official interpretations.
- Do not enable a scheme for production unless tests cover every relevant payroll period and World Concern's nominated reviewer signs the source/rule record and results.
- Statutory filing and remittance remain World Concern's responsibility unless separately authorized.

### 3.4 Parallel payroll and approvals

- Execute two consecutive full payroll periods against the approved baseline/current process.
- Reconcile employee count, gross, each earning/deduction, employer cost, net, bank schedule and cost-centre totals.
- Explain and resolve every material variance; retain a signed variance log and corrected rerun evidence.
- Demonstrate preparer/approver separation, locked approved results, controlled adjustments and audit events. No unresolved material difference passes acceptance.

### 3.5 Access, records, reports and privacy

- Verify each agreed role's allowed and denied operations, including attempts to access another employee's data or unauthorized bank/document exports.
- Verify employee changes require the appropriate approval; verify sensitive payroll actions and exports create the agreed audit records.
- Confirm audit retention, access, export restriction and privacy notices/consents as decided by World Concern.
- Reconcile payslips, statutory/deduction reports, bank schedules, departmental reports and CSV/Excel/PDF exports to the accepted payroll run.
- Confirm external email provider setup and test delivery only after privacy/security approval.

### 3.6 Integration, migration, recovery and browser use

- Validate import schema, malformed/duplicate records, rejected-row reporting and signed opening control totals.
- Verify the agreed HR and accounting interface or approved structured-file exchange in an authorized test environment; reconcile both directions where applicable.
- Exercise current agreed browsers and target mobile viewports; run role-based user journeys and check usability/accessibility criteria agreed at discovery.
- Restore from a protected backup and record measured recovery time/data point against buyer-approved RPO/RTO; targets remain subject to provider capability and quote.
- Verify monitoring, escalation contacts, access revocation and release/rollback runbook.

### 3.7 Final acceptance and no-go-live criteria

World Concern's authorized representative signs: traceability/scope; statutory source and calculation evidence; two parallel-run reconciliations; UAT and role/security results; migration/interface reconciliation; restore/browser results; training and handover; and known limitations.

**No go-live** if statutory sources are unapproved, an applicable scheme lacks tested coverage, material payroll variances remain, a critical/high security issue lacks written risk acceptance, payroll approval separation fails, data migration is unreconciled, backups cannot be restored, or management sign-off is absent.

## 4. Change control and schedule dependencies

New entities, employees beyond the planning assumption, extra integrations, materially different statutory interpretations, additional reports, changes to source systems, or expanded security/hosting requirements require written change assessment. The assessment records scope, price, risk, acceptance effects and schedule before work starts. Third-party costs are not incurred without approval.
