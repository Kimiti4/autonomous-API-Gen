TECHNICAL PROPOSAL
Design, Implementation and Support of a Payroll System
Submitted to: World Concern Development Organization, Nairobi, Kenya
Bidder: Amos Kimiti Kariuki — Independent Individual Bidder
Submission deadline: 28 October 2026
Proposal date: 27 October 2026
Document status: Final-review draft, subject to completion of the submission checklist

1. Executive Summary
Amos Kimiti Kariuki (the Bidder) proposes to design, implement, test and support a secure, web-based payroll system tailored to World Concern Development Organization’s stated requirements for approximately 50 employees across five offices in Kenya.
The proposed solution will cover employee and employment records; payroll calculation and approval; statutory deductions and reporting; electronic payslips and employee self-service; salary and benefit allocation across multiple cost centres; management reporting; agreed HR and accounting data exchange; migration; training; and ongoing maintenance and support.
The proposed system will be developed and validated against an agreed requirements baseline. This submission does not represent that the complete payroll system already exists or is production-ready. The Bidder will demonstrate delivery through documented requirements, independently checked payroll calculations, functional and security tests, reconciled parallel payroll runs, integration evidence and formal acceptance.
The proposed implementation period is 18 weeks from contract commencement, subject to timely access to data and systems, World Concern’s review and approval of payroll rules, statutory validation, integration dependencies and the payroll calendar. Two consecutive reconciled parallel payroll runs are required before production release. If the acceptance conditions cannot be met within the indicative schedule, the schedule will be revised rather than bypassing the required controls.
The separate financial proposal provides an indicative first-year estimate of KES 1,670,000, comprising KES 1,310,000 for implementation and KES 360,000 for annual maintenance/support and indicative hosting, backups and monitoring. The hosting allowance remains subject to provider quotations and confirmation of technical, security and data-protection requirements. These figures are planning estimates, not a buyer-approved budget ceiling or a binding, supplier-backed fixed quotation.
2. Bidder Profile and Evidence of Capability
2.1 Bidder information
The Bidder is Amos Kimiti Kariuki, applying as an independent individual. The Bidder reports receiving direct clarification from World Concern that individual applicants may apply. This clarification concerns eligibility to submit and does not guarantee an award. The applicable procurement requirements and any additional documentation requested by World Concern remain controlling.
No registered company, company registration number, VAT PIN, professional certification, previous payroll deployment, client reference or existing engagement with World Concern is claimed in this proposal.
2.2 Engineering approach and supporting evidence
The proposed payroll application will be developed using a software-generation and verification platform, with generated artifacts, dependencies, tests and relevant verification evidence transferred into a separate payroll project. The payroll project is maintained in its own source repository, with independent build/test and release controls; each received artifact is independently reviewed, built and tested, and the application does not require the generation platform at runtime. Existing engineering evidence is limited to a bounded HTTP contract test across Python FastAPI, Elixir OTP and Rust Axum services. This does not establish complete payroll functionality, Kenyan statutory compliance, production readiness or certification. Those areas will be verified against the agreed payroll requirements and acceptance criteria.
3. Understanding of World Concern’s Requirements
The Terms of Reference (TOR) describes an organization with approximately 50 employees across five offices, including contract employees, short-term contract employees and interns.
The required outcome is a reliable payroll solution that reduces processing effort and calculation errors while protecting employee information, supporting statutory compliance, generating accurate reports and payslips, maintaining audit trails, integrating with existing HR and accounting systems, and allocating salary and benefits across multiple cost centres.
The requested capabilities include:
Employee master records, employment history, departments, positions, bank details and document management.
Salary and earnings calculations, overtime, allowances, benefits, bonuses, loans, advances, leave deductions, arrears and back pay.
Monthly, bi-weekly and weekly payroll frequencies.
Statutory calculations, deductions, returns and reports.
Electronic payslips, employee self-service and historical document access.
Payroll summaries, departmental reports, deduction and tax reports, bank-transfer schedules and audit reports.
Role-based access, secure handling of payroll data, backup and recovery, audit trails, browser compatibility and mobile access where applicable.
Data import/export, agreed HR and accounting integration, documentation, training, maintenance and support.
The original TOR includes security requirements in §10 and deliverables, qualifications and acceptance provisions in §§11–13. System-specific details—including the existing HR and accounting products, approved payroll rules, statutory interpretations, calculation tolerances, service levels and acceptance thresholds—must be confirmed with World Concern before the scope and final price are contractually fixed.
4. Proposed Solution and Functional Scope
The proposed solution is a responsive web application for agreed desktop and mobile browsers. The final hosting arrangement, database, identity integration and technical architecture will be selected during discovery after assessment of security, privacy, recovery, integration and cost requirements.
4.1 Employee and employment information
The system will provide approved employee master records, contact and employment information, employment type and history, departments, positions, bank/payment details and references to employee documents.
Sensitive information will be access-restricted. Where applicable, records will use effective dates to preserve employment and payroll history.
Migration will use agreed import templates, validation rules, duplicate detection, exception reports and reconciled control totals. Source data will be loaded only after the parties agree on the migration scope, lawful handling and validation procedure.
4.2 Payroll processing
The proposed payroll engine will support approved monthly, bi-weekly and weekly pay groups and the agreed salary and earnings components, overtime, allowances, benefits, bonuses, incentives, loans, advances, leave deductions, arrears and back pay.
The workflow will include payroll-period setup, input validation, calculation previews, exception handling, separation of preparation and approval, controlled corrections, approval records and locked payroll results.
World Concern must approve the applicable pay rules before implementation. These include component definitions, eligibility, taxable treatment, prorating, rounding, effective dates, payroll cut-off dates and representative calculation examples.
4.3 Statutory calculations and returns
The system will implement statutory schemes confirmed as applicable to World Concern and approved for the relevant payroll periods. Schemes for assessment may include PAYE, NSSF, SHIF, the Affordable Housing Levy, pension arrangements and other applicable statutory deductions or employer contributions.
No statutory rate, band or treatment is assumed to be authoritative merely because it is included in an initial configuration. Each implemented scheme will require a dated authoritative source, an approved interpretation, independently reviewed calculation test cases and coverage of the relevant effective periods.
Employee deductions and employer contributions or costs will be represented separately, including their distinct treatment where required by law. Statutory reports and returns will be tested against approved examples before release.
Unless separately authorized and contracted, filing statutory returns and making statutory payments remain World Concern’s responsibility.
4.4 Cost-centre allocation
The system will allocate salary and eligible benefits across approved cost centres using agreed percentage-based or amount-based allocation rules.
The allocation process will reconcile to the full amount being allocated and flag incomplete, excessive or otherwise invalid allocations before payroll approval. Allocation rules, rounding and reconciliation tolerances will be agreed during discovery.
4.5 Payslips, employee self-service and reporting
The proposed system will generate and retain historical payslips and provide authorized employee access to agreed payroll-related documents.
Employee self-service will support agreed personal-information change requests, subject to approval. Leave balances and leave applications will be implemented only to the extent agreed during discovery; this proposal does not offer replacement of a complete HR information system.
The system will provide the agreed payroll summaries, departmental reports, statutory and tax reports, deduction reports, bank-transfer schedules, audit extracts and management reports. Agreed import and export formats will include CSV, Excel and PDF where applicable.
Bank-transfer schedules will be generated for review and export. Direct initiation of bank payments and custody or transfer of funds are excluded from the proposed scope unless separately designed, authorized and contracted.
4.6 HR and accounting integration
The initial estimate assumes one HR data exchange and one accounting data exchange using documented APIs or mutually approved structured files.
The systems involved, data dictionaries, interface access, vendor permissions, reconciliation rules and exchange schedules have not yet been established. These matters will be assessed during discovery.
File-based exchange may be used as an alternative only with World Concern’s approval. It will not be represented as a live API integration unless the interface is implemented and tested as such.
5. Security, Privacy and Operational Controls
Security and privacy requirements will be documented during discovery and implemented according to the approved design. Proposed controls include:
Named user accounts, role-based access and least-privilege permissions.
Separation of payroll preparation, review and approval.
Approval workflows for sensitive employee-record changes.
Encrypted network connections and protection of sensitive bank and identity information.
Restricted payroll exports and access to confidential reports.
Audit records for relevant payroll, approval, access and configuration actions.
Secure handling of credentials and application secrets.
Dependency review, security testing and remediation of release-blocking vulnerabilities.
Documented backup, restoration and operational recovery procedures.
Before production data is loaded, the parties will agree on audit retention and access, backup frequency and protection, restoration testing, incident contacts, breach handling, data retention and deletion, lawful processing responsibilities, any required data-processing agreement, and cross-border-transfer safeguards.
The hosting provider and region will be selected only after reviewing availability, security, privacy, recovery, performance and cost requirements. No hosting provider is currently claimed as selected or contracted. No data-residency guarantee, security certification, tested production deployment, fixed uptime commitment or existing 24/7 helpdesk is claimed.
Hosting costs, recovery objectives, service levels and any third-party commitments will be confirmed before contract execution.
6. Implementation Method and Indicative Schedule
The proposed implementation period is 18 weeks from contract commencement, subject to timely decisions, source data, reviewer availability, integration access and payroll-cycle requirements.
Phase
Indicative period
Principal activities
Discovery and scope baseline
Weeks 1–2
Confirm requirements, policies, payroll calendar, roles, cost centres, statutory sources, integrations, migration and acceptance criteria.
Architecture and data foundation
Weeks 3–5
Approve architecture, privacy/security design, records, permissions, import templates and backup/recovery approach.
Payroll and statutory rules
Weeks 6–9
Implement approved pay components, frequencies, deductions and adjustment workflows; validate independent calculation cases.
Costing, ESS and reporting
Weeks 10–12
Implement cost-centre reconciliation, agreed employee workflows, payslips, reports and exports.
Migration and integration
Weeks 13–14
Test data migration and implement the agreed HR/accounting interfaces or approved file exchanges.
Verification and parallel runs
Weeks 15–17
Complete functional, statutory, security, browser, recovery, integration and export tests; conduct two consecutive parallel payroll runs.
Release and handover
Week 18
Deploy only after written acceptance; complete training, documentation, runbooks and support handover.

The schedule is indicative. Delays in policy approval, statutory interpretation, data quality, external system access, defect remediation or completion of parallel payroll runs may require a revised schedule. Acceptance controls will not be waived to preserve the target date.
7. Testing, Acceptance and Go-Live Conditions
Production release will require documented evidence that the agreed scope has been implemented and tested.
The proposed release gates are:
An approved scope baseline and requirement-to-test traceability matrix.
World Concern approval of statutory sources, effective dates, employee/employer treatment and independent calculation test cases.
An approved security and privacy design, with no unresolved critical or high-severity security issue unless explicitly risk-accepted in writing by authorized management.
Two consecutive reconciled parallel payroll runs with no unresolved material difference against the agreed reference calculations.
Successful authorization, negative-access, audit-trail and preparation/approval separation tests.
Signed migration and integration reconciliation results.
Validated payslips, reports, exports and cost-centre allocations.
Successful browser tests and a witnessed backup-restoration test.
Completion of agreed training, documentation and operational handover.
Formal sign-off by authorized World Concern management.
Calculation tolerances, rounding rules, input cut-offs, browser coverage, support service levels, recovery objectives and materiality thresholds will be agreed during discovery.
Acceptance evidence will be tied to the tested release. Successful source-code generation or the bounded API contract described in Section 2 will not substitute for complete system acceptance.
8. Maintenance, Support and Continuity
The separate financial proposal includes provisional annual maintenance and support of KES 240,000.
The proposed service scope is agreed-business-hours operational support, corrective maintenance, minor improvements and updates to statutory tables following authoritative-source review. Unlimited enhancements, major new modules, additional integrations, third-party charges and 24/7 support are excluded unless separately agreed.
The service-level agreement will define support hours and channels, issue severity, response targets, escalation, maintenance windows and exclusions. Indicative acknowledgement targets for discussion are four business hours for payroll-blocking priority-one issues, one business day for priority two and three business days for priority three, during agreed support hours. These are proposed targets, not an existing contracted service commitment.
Before contract signature, the parties should agree on software ownership and permitted use, source-code access and handover, configuration and documentation rights, data export, credential custody, backup access, termination assistance and service continuity arrangements appropriate to an individual bidder.
9. Assumptions, Dependencies and Exclusions
The indicative estimate assumes:
Approximately 50 employees across five offices.
One Kenyan employing/payroll entity.
One initial migration from validated spreadsheet or CSV data.
One HR data exchange and one accounting data exchange.
Timely provision of lawful and complete source data, payroll policies and baseline control totals.
Designated HR, finance, payroll, security and acceptance reviewers.
Timely access to relevant systems, vendors, interfaces and test environments.
Approval of statutory interpretations, security decisions and acceptance criteria within the agreed review periods.
The following are excluded unless expressly included in a signed change:
Direct bank-payment initiation, custody or transfer of funds.
Replacement of a complete HRIS, recruitment, time-attendance or leave-management system.
Additional legal entities, migrations beyond the agreed scope, interfaces or custom reports.
Historical-document digitization beyond the agreed migration scope.
Filing statutory returns or making statutory payments on the employer’s behalf.
Legal or tax opinions.
24/7 support.
Independent certifications.
Third-party email/SMS, vendor API, bank, licensing or premium hosting charges not expressly included in the agreed price.
Changes will be assessed, scoped, priced and approved in writing before implementation. The final scope, service levels, hosting arrangement, applicable taxes and contract terms remain subject to confirmation and written agreement.
10. Bidder Declaration
The Bidder submits this proposal as Amos Kimiti Kariuki, an independent individual applicant. The Bidder reports receiving clarification that World Concern accepts individual applicants, without implying a guarantee of award.
The Bidder acknowledges that the complete payroll system is proposed for development and implementation and is not represented as an already completed, certified or production-ready product. The financial estimates, assumptions, exclusions and proposed service terms are set out in the separate financial proposal and supporting documents and remain subject to confirmation and written agreement.
Bidder: Amos Kimiti Kariuki
Signature: __________________________________
Date: ______________________________________
Telephone: +254 774 656 373
Email: karamos473@gmail.com
