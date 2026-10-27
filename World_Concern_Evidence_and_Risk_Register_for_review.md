Evidence and Risk Register
Bidder: Amos Kimiti Kariuki, independent individual bidder
Purpose: Distinguish claims made in the proposal from evidence currently available, planned verification, dependencies and unresolved risks.
Status interpretation: The statuses below reflect evidence available for this submission draft. They do not imply that the complete payroll application has been implemented, certified or accepted for production.
1. Evidence Register
ID
Claim / area
Status
Evidence and boundary
Next proof required
E-01
Generated Python FastAPI declared payroll HTTP contract
Demonstrated — bounded
Shared CI contract test in workflow run 40305413032. Evidence is limited to the routes, assertions and conditions exercised by that run.
Full payroll functional tests, independently approved statutory vectors, production security tests and buyer UAT.
E-02
Generated Elixir OTP declared payroll HTTP contract
Demonstrated — bounded
Same workflow run and shared contract. Does not establish complete payroll functionality or statutory compliance.
Full payroll functional tests, independently approved statutory vectors, production security tests and buyer UAT.
E-03
Generated Rust Axum declared payroll HTTP contract
Demonstrated — bounded
Same workflow run and shared contract. CI execution addressed the Windows local-linker limitation for that run only.
Full payroll functional tests, independently approved statutory vectors, production security tests and buyer UAT.
E-04
Tested revision for the cited API-contract evidence
Demonstrated — specific revision
Tested SHA: 254a540a12a909c068ee871a54e2f8d469090cab. The workflow URL is retained in E-01.
Preserve the relevant workflow logs and available artifacts in accordance with the applicable retention policy; record the tested revision in the evidence archive.
E-05
Complete World Concern payroll calculations
Not demonstrated
No complete payroll application is represented as implemented, independently verified or accepted for production.
Implement the agreed candidate, execute independent calculation vectors and two consecutive parallel payroll cycles, resolve material differences and obtain management acceptance.
E-06
Current Kenyan statutory calculation logic
Not demonstrated
No numerical statutory rates or thresholds are asserted as already verified by this register.
Create a source/version/effective-date register, complete independent tests for each applicable scheme and period, and obtain designated reviewer approval.
E-07
Full TOR traceability
Source received; matrix updated; buyer clarification and sign-off pending
The original five-page TOR has been received. Sections 10–13 include security controls, deliverables, vendor qualifications and acceptance criteria. The compliance matrix has been updated against the source.
Resolve remaining scope, security, qualification and acceptance ambiguities; obtain the buyer-approved scope and retain written approval.
E-08
World Concern HR/accounting integration
Not demonstrated
The actual HR and accounting products, interfaces and access arrangements have not been established.
Inventory the systems, confirm interface specifications and access, execute agreed integration tests and obtain finance/system-owner sign-off.
E-09
Production security, privacy, hosting and backup recovery
Not demonstrated
No production deployment, selected hosting-provider contract, security certification or successful production-equivalent restoration test is claimed.
Approve the design and data flows, obtain a provider quotation, execute security and restoration tests, and record written acceptance.
E-10
Payroll browser, employee self-service and acceptance workflows
Not demonstrated
The cited API-contract test does not verify payroll browser workflows, employee access isolation or buyer acceptance.
Run candidate-bound browser and authorization tests; retain results for payslips, employee self-service and agreed workflows against the tested release.

Evidence-handling rules
Each item shall retain a clear distinction between demonstrated capability, planned implementation, unresolved dependency and excluded scope.
Evidence shall identify the relevant source, tested revision, test conditions, results and limitations where available.
A passing test shall support only the claims exercised by that test; it shall not be generalized into proof of complete payroll readiness, statutory certification or production security.
New evidence shall be added only after the relevant test or approval has actually occurred.
If a claim changes, the register and the related proposal statements shall be updated together.
2. Risk Register
Likelihood and impact ratings are preliminary planning assessments for this proposal. They shall be reviewed at project kickoff and updated when evidence, quotations, scope decisions or technical findings change.
ID
Risk
Likelihood / impact
Mitigation and acceptance gate
Owner
R-01
Proposal documents contain omissions or inconsistencies against the original TOR.
Medium / High
Reconcile the compliance matrix, evidence register, technical proposal, implementation and acceptance plan, and pricing assumptions against the original five-page TOR. Clarify remaining ambiguities and assess cost and schedule effects before the final offer.
Bidder and World Concern procurement
R-02
Individual-bidder eligibility or formal application requirements are misunderstood.
Medium / Critical
The bidder reports having received confirmation that individuals may apply. Retain written confirmation if available, verify the complete application requirements and provide only documents that genuinely exist and apply. Eligibility confirmation is not a guarantee of award.
Bidder
R-03
Provisional estimates differ from actual implementation or provider costs.
High / High
Identify estimates as provisional, confirm scope during discovery, obtain relevant provider quotations and secure written approval before additional expenditure. The KES 10,000/month hosting figure is an indicative allowance only; no provider is selected or contracted.
Bidder and buyer
R-04
Tax, VAT registration or eTIMS obligations are not confirmed.
Medium / High
Confirm the bidder's actual tax obligations, VAT registration status, applicable service treatment and eTIMS requirements before contracting. Charge and itemize tax only as legally applicable and authorized or required. Do not claim an unverified PIN or registration status.
Bidder, with qualified tax advice where required
R-05
Statutory rates, interpretations or effective dates are incomplete or change.
High / Critical
Maintain an authoritative, versioned source register; separate employee deductions from employer contributions and costs; use independently checked, period-specific calculation vectors; obtain reviewer approval. Block production payroll until required evidence is accepted.
World Concern payroll reviewer and bidder
R-06
Incorrect payroll calculations cause underpayment, overpayment or reporting errors.
Medium / Critical
Use independently prepared expected results, maker-checker controls, two consecutive parallel runs, documented variance resolution and a mandatory go-live hold until acceptance criteria are met.
World Concern payroll owner and bidder
R-07
HR or accounting interfaces are unavailable or more complex than estimated.
High / High
Identify systems and vendors during discovery, confirm test environments and access, define the interfaces included in scope, and test reconciliation. A structured-file exchange may be used only if expressly agreed as an acceptable alternative.
Buyer system owners and bidder
R-08
Employee identity, bank, payroll or other sensitive data is exposed.
Medium / Critical
Apply least privilege, appropriate encryption, restricted exports, audit logging, approved hosting and retention controls, security testing and controlled use of test data. Do not import sensitive production data before required design and security approvals.
World Concern security/privacy contact and bidder
R-09
Cross-border hosting or data transfers conflict with applicable privacy requirements.
Medium / High
Review data flows, hosting region, applicable transfer requirements and safeguards. Obtain required approvals before production data is transferred. Do not claim a residency guarantee before the provider and architecture are confirmed.
World Concern privacy contact and bidder
R-10
The selected provider cannot meet agreed availability or recovery requirements.
Medium / High
Agree RPO, RTO and service levels; evaluate provider capabilities and quotations; perform a restoration test; document contingency and rollback arrangements.
Buyer and bidder
R-11
Two parallel payroll cycles cannot be completed within the planned 18 weeks.
Medium / High
Schedule against World Concern's actual payroll calendar and approval dependencies. Extend the timeline rather than omit a cycle or weaken acceptance requirements.
Project owner and bidder
R-12
Single-person implementation or support creates continuity risk.
Medium / High
Agree documentation, source-code and data handover rights, credential custody, a buyer counterpart, escalation arrangements and termination assistance. Any subcontracting must be disclosed and approved as required by the contract.
Bidder and buyer
R-13
Email, SMS, banking or other third-party charges exceed the estimate.
Medium / Medium
Identify required third-party services and usage charges, obtain quotations where applicable and secure buyer approval before committing expenditure. Unquoted usage charges are not assumed to be included.
Bidder
R-14
Proposal language overstates existing product maturity or verification.
Low / Critical
Maintain explicit demonstrated, proposed, unverified and excluded labels. Reference only the exact API-contract evidence available. Do not claim complete payroll certification, production readiness or security certification without appropriate evidence.
Bidder

Risk review and escalation
The risk register shall be reviewed at kickoff, at each major phase exit and before production acceptance. New risks, material changes in likelihood or impact, mitigation owners and residual-risk decisions shall be recorded.
Risks affecting statutory compliance, payroll correctness, sensitive-data protection or mandatory acceptance requirements shall be escalated to the designated World Concern decision-maker. A commercial or schedule decision shall not override a legal obligation or mandatory release condition.
3. Official-Source Verification Plan
This register does not provide statutory rates or bands and does not certify that current statutory tables have already been verified. The following authorities are starting points for the implementation-stage review.
Area
Starting authority
Verification required
PAYE and applicable tax deductions
Kenya Revenue Authority (KRA)
Confirm the applicable official guidance, legislation, rates, reliefs, effective dates and calculation treatment for each relevant payroll period.
NSSF contributions
NSSF Kenya — Employers
Obtain the applicable contribution-rate notice and confirm the relevant contribution year and effective dates, including the 2026 Year 4 notice if applicable to the payroll period.
Social Health Insurance Fund (SHIF)
Social Health Authority (SHA)
Confirm the applicable legal instruments, contribution rules, calculation basis and effective dates.
Affordable Housing Levy
Kenya Law and applicable official guidance
Verify the applicable legislation, amendments and instruments. Separately confirm employee deductions and employer contributions or costs, including effective dates and calculation treatment.

For each statutory source, the implementation record shall capture:
Exact title and issuing authority.
Publication, version or other identifying details.
Retrieval date and stable URL, where available.
Retained source copy and SHA-256 hash, where a copy is retained and hashing is applicable.
Applicable effective-date range and payroll periods.
Applicability decision and documented interpretation.
Independently checked calculation examples and test results.
Name or role of the designated reviewer, approval date and outstanding questions.
Where sources conflict, effective dates are unclear or interpretation requires specialist judgment, the issue shall be escalated for qualified review and recorded before the affected rule is enabled in production.
World Concern's designated qualified reviewer shall confirm the source values and interpretation applicable to its employees and payroll periods. This verification plan is not legal advice and does not constitute evidence that any current statutory calculation table has already been certified.
4. Evidence and Risk Acceptance
The register supports transparent evaluation of the proposal and controlled progression toward implementation. It is not, by itself, proof of successful implementation or acceptance.
Before production release, World Concern shall receive the evidence required by the agreed acceptance plan, including approved statutory sources and calculation tests, two consecutive parallel-run reconciliations, access/security results, migration and interface reconciliations, recovery-test results, defect dispositions, training and handover records, and written management approval.
No production-readiness claim shall be made until the relevant evidence exists, has been reviewed and has satisfied the agreed acceptance criteria.
End of Evidence and Risk Register
