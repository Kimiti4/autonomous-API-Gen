# TOR Compliance and Evidence Matrix

**Bidder:** Amos Kimiti Kariuki, independent individual bidder  
**Purpose:** Map the supplied World Concern payroll TOR to proposed response, evidence status, dependencies and acceptance evidence.  
**Status key:** **Demonstrated** = limited to named existing evidence; **Proposed** = future delivery, not currently proven; **Clarification required** = TOR or buyer information is incomplete; **Excluded** = not offered unless separately agreed.

| TOR clause / requirement | Proposed response | Status | Evidence / acceptance / dependency |
|---|---|---|---|
| Objectives: automated calculation and processing | Payroll run with validation, calculation, exception review and approval | Proposed | Independent approved test vectors and two consecutive parallel payroll reconciliations |
| Reduce time and human error | Input checks, exception handling, maker-checker approval and reconciliation | Proposed | Agreed baseline and measurable UAT results; target reduction to be agreed |
| Employee master records | Employee identity, contacts and effective-dated employment data | Proposed | Field-level test and migration/control-total reconciliation |
| Employment history | Effective-dated history and change records | Proposed | Scenario and audit-history tests |
| Department and position | Department/position assignment and history | Proposed | User acceptance and report tests |
| Bank details | Restricted bank/payment-instruction records | Proposed | Role-negative tests, audit, export controls and data-protection approval |
| Employee documents | Document references/download access; storage method subject to security design | Proposed / Clarification required | Confirm file types, retention, storage and access rules |
| Salary computation | Approved pay components, frequency and calculation policies | Proposed | Reviewer-signed independent vectors and parallel runs |
| Overtime, allowances, benefits, bonus/incentives | Configurable/effective-dated rules | Proposed | Written HR policy, taxable treatment and component-specific tests |
| Loans and advances | Approved schedules, deductions and balance controls | Proposed | Policy, edge cases and reconciliation |
| Leave deductions | Agreed payroll inputs and approved leave treatment | Proposed / Clarification required | Confirm leave system/source and policy; full HR leave replacement excluded |
| Arrears and back pay | Controlled retroactive adjustment workflow | Proposed | Period/effective-date test vectors and approval/audit evidence |
| Monthly, bi-weekly and weekly | Separate approved pay groups/calendars | Proposed | Test payroll for each required frequency |
| Cost allocation | Allocate salary/eligible benefits among multiple cost centres | Proposed | Percent/amount vectors, reconciliation and block on unresolved remainder/over-allocation |
| Income tax / PAYE | Effective-dated rule implementation only after authoritative source review | Proposed | KRA/source register, independent vectors for each period, reviewer approval |
| Social security / NSSF | Effective-dated applicable contribution logic | Proposed | Current official NSSF notice, employee/employer treatment and independent cases |
| Pension deductions | Support approved pension scheme(s) and rules | Proposed / Clarification required | Identify scheme, rules, employer contributions and tax treatment |
| Health insurance / SHIF | Effective-dated applicable employee/employer rules | Proposed | Current official SHA/legal sources and independently verified cases |
| Other statutory deductions | Include only confirmed obligations and approved rules | Proposed / Clarification required | World Concern/payroll reviewer identifies schemes and authoritative source |
| Affordable Housing Levy | Model employee deduction separately from employer contribution/employer cost where applicable | Proposed | Confirm applicability and current legal/source interpretation, effective dates, independent vectors and reviewer approval |
| Statutory returns/reports | Produce agreed calculations and output formats | Proposed / Clarification required | Obtain current return layouts, filing channel and employer responsibilities |
| Payslips / historical retrieval | Period payslip generation and authorized retrieval | Proposed | Content, access, retention and historical-migration tests |
| Email payslip distribution | Secure delivery through approved provider | Proposed / Clarification required | Confirm channel, provider, privacy/consent and recurring charges |
| ESS: view payslips and documents | Responsive employee access to authorized own records | Proposed | Browser/device, identity, access-isolation and document tests |
| ESS: personal data update subject to approval | Submit/update-request workflow with approver | Proposed | Positive/negative role and audit test |
| ESS: leave balance/application | Agreed limited workflow or integration with HR source | Proposed / Clarification required | Identify system of record and confirm scope |
| Payroll and departmental summaries | Agreed reports tied to approved payroll run | Proposed | Reconcile reports to run ledger and cost-centre data |
| Tax and deduction reports | Period reports based on approved statutory configuration | Proposed | Statutory vectors and report reconciliation |
| Bank transfer schedules | Export schedule for review and payment outside the system | Proposed | Format and beneficiary validation; direct payment initiation excluded |
| Audit/custom reports | Agreed audit extracts and configurable report requirements | Proposed / Clarification required | Specify fields, filters, retention and approval |
| HR and accounting integration | One agreed HR and one accounting interface or approved structured-file exchange | Proposed / Clarification required | System names, field maps, sandbox/API access, vendor permissions and reconciliation rules |
| Web/cloud and mobile/browser support | Responsive web target; provider/region chosen after review | Proposed | Agreed browser/device matrix, privacy/security approval and provider quote |
| Role-based, multi-user access | Least privilege and separated payroll roles | Proposed | Map to TOR sections 9–10; role matrix, password policy, MFA, secure authentication, encryption, audit-log coverage and negative authorization tests |
| Backups and recovery | Protected backups and witnessed restore test | Proposed | Provider selection; RPO/RTO and recovery objectives to be agreed |
| Audit trail | Record agreed sensitive user and payroll events | Proposed | Event coverage, access and retention tests |
| Security requirements (TOR §10) | Implement the agreed controls: applicable data-protection compliance, encryption of sensitive payroll data, secure authentication, password policies and MFA, detailed audit logs, and secure backup/disaster recovery | Proposed / Clarification required | Design and test each control; confirm data-protection roles, threat model, retention, incident handling and recovery objectives with buyer; no security certification claimed |
| Common import/export formats | Agreed CSV/Excel/PDF input/output | Proposed | Format, encoding, totals and malformed-data tests |
| Helpdesk, updates, upgrades, SLA, reviews | Provisional annual support, agreed-hours helpdesk and review | Proposed / Clarification required | Support window, severity, response targets, exclusions and fees agreed in contract; no existing SLA claimed |
| Acceptance: testing, accuracy, statutory compliance, integration, training, sign-off | Evidence-bound acceptance plan and release gates | Proposed | Separate Implementation and Acceptance Plan; authorized management sign-off required |
| Software licence / implementation / training / annual maintenance / recurring charges | Itemized provisional estimate | Proposed / Clarification required | Separate Financial Proposal; prices are not final, provider/tax costs unverified |
| Existing three-backend parity | Bounded declared payroll HTTP contract exercised in CI | Demonstrated, limited | [Workflow run 40305413032](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/40305413032), tested SHA `254a540a12a909c068ee871a54e2f8d469090cab`; does not prove complete payroll behavior |
| Full payroll certification / production readiness | Not claimed | Not demonstrated | Payroll readiness remains `NOT_CERTIFIED`; statutory, frontend, source mapping and broad runtime evidence are project deliverables |
| Ruby/C# parity, W12 executable effects, W13 browser-to-live-API journey | Not part of evidence already demonstrated | Not demonstrated | Separate engineering workstreams; not prerequisites for a scoped project bid, but no evidence claim is made |
| Deliverables (TOR §11) | Provide configured/customized software, agreed migration, UAT, user/admin training, documentation, go-live and post-implementation support | Proposed | Deliverable-by-deliverable evidence and buyer sign-off; licensing/subscription model and scope confirmed in contract |
| Vendor qualifications (TOR §12) | Demonstrate relevant implementation experience, similar-organization references, Kenyan payroll/tax knowledge, local technical support, reliability/security and maintenance capacity | Clarification required | Individual bidder must provide truthful CV/project evidence and references if available; no unverified client references, certifications or prior payroll deployments claimed |
| Acceptance criteria (TOR §13) | Testing, accurate payroll, statutory compliance, successful integrations, documentation/training and authorized management sign-off | Proposed | Acceptance gates in Implementation and Acceptance Plan; no go-live before evidence and sign-off |\n| Direct bank payment execution / custody | Not offered | Excluded | Requires separately scoped banking/security/legal integration |

## Evidence boundary

The sole completed implementation evidence cited here is a successful CI execution of a particular declared HTTP contract across generated Python FastAPI, Elixir OTP and Rust Axum services. The test does not establish the payroll calculations, statutory tables, employee self-service browser flows, production security/hosting, integration with World Concern, or a certified payroll product. All such requirements are marked proposed or clarification-required until delivery evidence and buyer acceptance exist.
