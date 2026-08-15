[Yes — this is the correct way to specify Phases 21–30.

At this level, the platform should no longer be described merely as a set of features. It should be treated as a **constitutional engineering civilization**: a system in which every capability is expressed through immutable representations, governed by policy, verified before deployment, observable in production, and reversible under failure.

Below is a tightened, implementation-ready framing of Phases 21–30 that preserves the structure you provided while adding the cross-phase discipline needed to keep the platform coherent.

---

# Canonical Rule for Phases 21–30

Every phase must produce more than source code.

Each phase must deliver at least:

1. **Specification**
   - Architecture specification
   - Behavioral specification
   - Constitutional constraints
   - Integration contract with earlier phases

2. **ISR Extension**
   - New immutable representation types
   - Versioned schema
   - Lineage and provenance metadata
   - Compatibility rules with prior ISR versions

3. **Runtime Components**
   - Executable services, engines, coordinators, or daemons
   - Safe lifecycle management
   - Observability hooks
   - Policy enforcement points

4. **APIs**
   - Machine-readable interfaces
   - Administrative interfaces
   - Audit interfaces
   - Governance and approval interfaces

5. **Tests**
   - Unit tests
   - Integration tests
   - Contract tests
   - Property-based tests
   - Formal verification where applicable
   - Regression and rollback tests
   - Safety and abuse-case tests

6. **Documentation**
   - Technical documentation
   - Operator documentation
   - Governance documentation
   - Safety cases
   - Extension guides

7. **Governance Artifacts**
   - Policy definitions
   - Approval workflows
   - Audit logs
   - Compliance evidence
   - Reversibility and rollback procedures

This rule prevents the platform from degenerating into an uncontrolled collection of autonomous capabilities.

---

# Global Constitutional Invariants for Phases 21–30

All advanced capabilities must obey the following invariants:

## 1. ISR Remains the Source of Truth

No autonomous system, agent, compiler, organization, marketplace plugin, or evolution engine may treat generated code, runtime state, or external artifacts as the authoritative system definition.

The ISR is the authoritative representation.

Generated code is derivative.

Runtime state is ephemeral.

External artifacts are evidence, not truth.

## 2. Historical ISR Is Immutable

Evolution does not mutate historical ISR artifacts.

Evolution creates new ISR revisions with explicit lineage.

Every revision must reference:

- Parent ISR hash
- Constitution version
- Policy set
- Author or autonomous originator
- Verification evidence
- Approval record
- Rollback path

## 3. All Autonomous Action Must Be Bounded

No agent, organization, compiler backend, plugin, or evolution proposal may act outside its granted constitutional scope.

Capabilities must be explicitly delegated.

Privileges must be revocable.

Autonomy must be sandboxed.

## 4. All Significant Change Must Be Reversible

Any promoted architecture, generated product, plugin, organizational change, or compiler transformation must have a rollback path.

Irreversible changes require explicit constitutional exception and human approval.

## 5. All Change Must Be Explainable

Every autonomous decision must produce explainable evidence, including:

- Why the action was proposed
- What alternatives were considered
- What simulation or verification occurred
- What policies were evaluated
- Who or what approved the action
- What rollback path exists

## 6. All Learning Must Be Safety-Mediated

Production learning may influence future proposals, but it may not directly rewrite architecture, policy, or compiler behavior without verification and governance.

Learning produces recommendations.

Evolution produces proposals.

Verification produces evidence.

Governance produces approval.

Only then can promotion occur.

## 7. All Cross-Organization Interaction Must Be Federated

Autonomous engineering organizations may collaborate, but no organization may unilaterally impose its internal constitution on another.

Cross-organization collaboration must occur through:

- Shared constitutional agreements
- Federated policy negotiation
- Mutual verification
- Auditable coordination contracts

---

# Phase 21 — Self-Evolution Engine

## Objective

Enable the platform to safely evolve its own architecture, compiler pipeline, optimization strategies, and operational behavior while preserving constitutional guarantees.

## Constitutional Prompt

> Design and implement a Constitutional Self-Evolution Engine that continuously analyzes the Autonomous Software Engineering Platform, identifies architectural improvement opportunities, generates competing evolution proposals, simulates their impact, formally verifies safety and compatibility, and promotes approved improvements into production. The Intermediate Software Representation remains the immutable source of truth. All self-modifications must be explainable, reversible, versioned, auditable, and governed by constitutional policies.

## Primary ISR Extensions

- `EvolutionProposalISR`
- `ArchitectureMutationSpecISR`
- `SimulationCampaignISR`
- `CompatibilityEvidenceISR`
- `VerificationEvidenceISR`
- `FitnessEvaluationISR`
- `PromotionRecordISR`
- `RollbackPlanISR`
- `EvolutionHistoryISR`

## Core Runtime Components

- Architecture analysis engine
- Mutation engine
- Evolution candidate generator
- Architecture simulation engine
- Compatibility verification engine
- Regression prevention framework
- Architecture fitness evaluator
- Constitutional approval workflow
- Promotion controller
- Rollback engine
- Evolution history repository
- Metrics dashboard

## Acceptance Criteria

The phase is complete when:

1. The engine can analyze an existing ISR architecture and identify improvement opportunities.
2. It can generate multiple competing evolution proposals.
3. Each proposal includes:
   - Architectural delta
   - Expected benefits
   - Risk assessment
   - Compatibility analysis
   - Rollback plan
4. Proposals are simulated before promotion.
5. Formal or semi-formal verification blocks unsafe proposals.
6. Approved proposals can be promoted into a staging environment.
7. Failed promotions can be automatically rolled back.
8. Every evolution event is reconstructable from audit evidence.

## Critical Safety Constraint

The Self-Evolution Engine may never directly mutate production ISR without:

- Simulation
- Verification
- Policy evaluation
- Approval
- Rollback plan

---

# Phase 22 — Autonomous Engineering Civilization

## Objective

Transform isolated AI agents into persistent engineering organizations with roles, memory, governance, collaboration protocols, and lifecycle management.

## Constitutional Prompt

> Design an organizational runtime where autonomous agents form constitutional engineering teams with defined responsibilities, memory, governance, specialization, collaboration protocols, conflict resolution, and lifecycle management. Organizations should persist across projects and continuously improve through experience.

## Primary ISR Extensions

- `OrganizationISR`
- `RoleDefinitionISR`
- `AgentMembershipISR`
- `DelegationGrantISR`
- `CollaborationProtocolISR`
- `TaskAllocationPlanISR`
- `ConflictResolutionRecordISR`
- `OrganizationalMemoryISR`
- `OrganizationLifecycleEventISR`

## Core Runtime Components

- Organization runtime
- Agent lifecycle manager
- Role registry
- Task allocation engine
- Negotiation framework
- Conflict resolution engine
- Leadership election system
- Organizational memory store
- Communication bus
- Organization dashboard
- Governance policy engine

## Acceptance Criteria

The phase is complete when:

1. Organizations can be created from constitutional templates.
2. Agents can be assigned roles with explicit permissions.
3. Roles can delegate bounded authority to other agents.
4. Organizations persist beyond individual tasks.
5. Organizational memory is queryable and governable.
6. Task allocation respects role capabilities and policy constraints.
7. Conflicts are escalated through defined resolution protocols.
8. Leadership or coordination roles can be elected or reassigned.
9. Organizations can be audited, suspended, restored, or dissolved.

## Critical Safety Constraint

No organization may grant itself powers outside its constitutional charter.

All role permissions must be derived from explicit policy.

---

# Phase 23 — Enterprise Knowledge Graph

## Objective

Create a universal engineering memory graph that captures all meaningful software engineering knowledge and makes it semantically queryable, traceable, and evolution-aware.

## Constitutional Prompt

> Design a constitutional enterprise knowledge graph that captures all software engineering knowledge—including requirements, architectures, ISR artifacts, source code, documentation, deployments, telemetry, incidents, user feedback, research, and organizational knowledge—and provides semantic reasoning, traceability, and evolution-aware querying.

## Primary ISR Extensions

- `KnowledgeGraphSchemaISR`
- `SemanticOntologyISR`
- `KnowledgeEntityISR`
- `KnowledgeRelationISR`
- `LineageGraphISR`
- `TraceabilityLinkISR`
- `EvidenceNodeISR`
- `GraphQueryISR`

## Core Runtime Components

- Knowledge graph runtime
- Ontology manager
- Knowledge compiler
- Lineage tracker
- Semantic search engine
- Traceability engine
- Graph query engine
- Ingestion adapters
- Access control layer
- Visualization tools

## Acceptance Criteria

The phase is complete when:

1. Requirements can be traced to ISR artifacts.
2. ISR artifacts can be traced to generated code.
3. Generated code can be traced to deployments.
4. Deployments can be traced to telemetry and incidents.
5. Incidents can be traced back to architectural decisions.
6. Semantic search can answer cross-domain engineering questions.
7. Graph queries respect access control and governance policies.
8. Knowledge evolution is versioned and auditable.

## Critical Safety Constraint

The knowledge graph may inform decisions, but it may not directly execute architectural mutations.

It is an evidence substrate, not an autonomous actuator.

---

# Phase 24 — Autonomous Product Factory

## Objective

Generate complete products and businesses, not merely software artifacts.

## Constitutional Prompt

> Build an Autonomous Product Factory capable of discovering opportunities, validating markets, designing products, generating software, creating branding and marketing assets, configuring monetization, deploying services, monitoring customer adoption, and continuously evolving products using constitutional governance.

## Primary ISR Extensions

- `ProductISR`
- `MarketOpportunityISR`
- `CustomerSegmentISR`
- `ValuePropositionISR`
- `BrandAssetISR`
- `PricingModelISR`
- `MonetizationPlanISR`
- `MarketingCampaignISR`
- `CustomerAnalyticsISR`
- `RevenueSimulationISR`
- `ProductExperimentISR`

## Core Runtime Components

- Market research engine
- Opportunity discovery engine
- Product strategy generator
- Brand generator
- UX generator
- Pricing engine
- SaaS generator
- Marketing compiler
- Customer analytics engine
- Revenue simulator
- Deployment integration layer
- Product experimentation engine

## Acceptance Criteria

The phase is complete when:

1. The system can discover and evaluate market opportunities.
2. It can generate a product strategy from validated assumptions.
3. It can produce product requirements as ISR.
4. It can generate software through the universal compiler pipeline.
5. It can generate branding, positioning, and marketing assets.
6. It can simulate revenue and adoption scenarios.
7. It can deploy a governed product instance.
8. It can monitor adoption, churn, performance, and feedback.
9. It can propose product improvements through constitutional evolution.

## Critical Safety Constraint

The Product Factory may not launch customer-facing products without:

- Policy approval
- Safety review
- Compliance validation
- Billing and data handling verification
- Rollback or shutdown plan

---

# Phase 25 — Universal Software Compiler

## Objective

Compile ISR into optimized systems for any target platform.

## Constitutional Prompt

> Design a universal compiler architecture where the ISR is technology-neutral and backend compilers generate optimized systems for web, mobile, desktop, cloud, embedded, robotics, automotive, gaming, AI, scientific computing, and future platforms.

## Primary ISR Extensions

- `CompilationPlanISR`
- `TargetPlatformISR`
- `TargetCapabilityRegistryISR`
- `BackendCompilerManifestISR`
- `OptimizationPipelineISR`
- `ArtifactManifestISR`
- `CompilationEvidenceISR`
- `DeploymentTargetISR`

## Core Runtime Components

- Universal compiler orchestrator
- Backend compiler interface
- Platform abstraction layer
- Target capability registry
- Optimization pipeline
- Compiler plugin SDK
- Validation framework
- Code quality analyzer
- Artifact packaging system
- Deployment interface
- Reproducible build manager

## Acceptance Criteria

The phase is complete when:

1. The same ISR can compile to multiple target platforms.
2. Backend compilers register capabilities declaratively.
3. Compilation plans are deterministic and auditable.
4. Generated artifacts include provenance and verification evidence.
5. Compiler plugins can be added without modifying the core compiler.
6. Generated code passes platform-specific validation.
7. Build outputs are reproducible from the same ISR and compiler version.
8. Failed builds produce diagnosable evidence.

## Critical Safety Constraint

Backend compilers may not introduce semantic drift from the ISR.

If a backend cannot faithfully implement the ISR, it must fail explicitly.

---

# Phase 26 — Continuous Learning Infrastructure

## Objective

Learn continuously from production systems, incidents, users, costs, performance, and security events.

## Constitutional Prompt

> Build an autonomous learning infrastructure that ingests operational telemetry, production incidents, customer feedback, performance metrics, costs, security findings, and developer interventions to improve future architectures while preserving constitutional safety.

## Primary ISR Extensions

- `LearningSignalISR`
- `TelemetryStreamISR`
- `IncidentAnalysisISR`
- `CustomerFeedbackISR`
- `CostObservationISR`
- `PerformanceObservationISR`
- `SecurityFindingISR`
- `RecommendationISR`
- `ArchitectureFeedbackISR`

## Core Runtime Components

- Telemetry pipeline
- Feedback collector
- Incident analyzer
- Cost optimizer
- Performance analyzer
- Security learning module
- Recommendation engine
- Architecture feedback compiler
- Knowledge repository connector
- Learning governance filter

## Acceptance Criteria

The phase is complete when:

1. Production telemetry can be ingested at scale.
2. Incidents are correlated with architecture, code, deployment, and configuration.
3. Customer feedback is linked to product and engineering artifacts.
4. Cost and performance observations generate optimization recommendations.
5. Security findings generate remediation proposals.
6. Recommendations are routed to the Self-Evolution Engine or human owners.
7. No learning signal can directly mutate production architecture.
8. Learning outcomes are measurable and auditable.

## Critical Safety Constraint

Learning produces proposals, not direct mutations.

All learned improvements must pass through verification and governance.

---

# Phase 27 — Marketplace & Plugin Ecosystem

## Objective

Create a secure, constitutional ecosystem for third-party extensions, plugins, models, design systems, domain packs, compiler backends, and infrastructure templates.

## Constitutional Prompt

> Design a secure constitutional marketplace that enables third-party plugins, compiler extensions, design systems, domain packs, verification engines, infrastructure templates, and AI models while maintaining isolation, compatibility, versioning, and governance.

## Primary ISR Extensions

- `PluginManifestISR`
- `ExtensionCapabilityISR`
- `DependencyGraphISR`
- `SandboxPolicyISR`
- `MarketplaceListingISR`
- `CompatibilityReportISR`
- `PublisherIdentityISR`
- `RevocationRecordISR`

## Core Runtime Components

- Marketplace architecture
- Plugin SDK
- Extension registry
- Package manager
- Dependency resolver
- Sandboxing framework
- Compatibility validator
- Security scanner
- Publisher verification system
- Marketplace portal
- Revocation and quarantine system

## Acceptance Criteria

The phase is complete when:

1. Third-party extensions can be published with signed manifests.
2. Extensions declare capabilities, dependencies, and required permissions.
3. Plugins are validated before installation.
4. Plugins execute inside sandboxed environments.
5. Incompatible or malicious extensions can be rejected or revoked.
6. Extensions can be versioned and dependency-resolved.
7. Marketplace artifacts include audit and provenance metadata.
8. Installed extensions can be inspected, disabled, or removed.

## Critical Safety Constraint

No plugin may bypass constitutional policy, ISR integrity, sandbox isolation, or audit logging.

---

# Phase 28 — Constitutional Governance

## Objective

Govern all platform evolution safely, transparently, and accountably.

## Constitutional Prompt

> Implement a governance framework that manages constitutional versions, policy inheritance, organizational compliance, approval workflows, auditing, and change lineage while ensuring all architectural evolution remains transparent, reversible, and accountable.

## Primary ISR Extensions

- `ConstitutionISR`
- `PolicySetISR`
- `PolicyRuleISR`
- `ApprovalWorkflowISR`
- `ComplianceReportISR`
- `AuditEvidenceISR`
- `ChangeLineageISR`
- `GovernanceExceptionISR`
- `ConstitutionVersionISR`

## Core Runtime Components

- Constitution manager
- Policy compiler
- Compliance engine
- Audit framework
- Approval workflow engine
- Voting system
- Version manager
- Lineage repository
- Governance dashboard
- Exception management system

## Acceptance Criteria

The phase is complete when:

1. Constitutions can be versioned and inherited.
2. Policies can be compiled into enforceable rules.
3. Compliance can be checked before execution.
4. Approval workflows can require human, organizational, or autonomous consent.
5. Audit logs can reconstruct any significant decision.
6. Governance exceptions are explicit, limited, and revocable.
7. Policy violations block execution by default.
8. Governance reports can be generated for regulators, operators, and auditors.

## Critical Safety Constraint

Governance is not advisory.

Governance is an execution precondition.

---

# Phase 29 — Distributed Evolution Cloud

## Objective

Scale evolution, simulation, compilation, and verification across distributed infrastructure.

## Constitutional Prompt

> Design a distributed evolution cloud that coordinates large-scale evolutionary search, architecture simulations, compiler workloads, and verification across geographically distributed compute resources with resilience, elasticity, and fault tolerance.

## Primary ISR Extensions

- `DistributedJobISR`
- `ComputeClusterISR`
- `ResourceAllocationISR`
- `SimulationCampaignISR`
- `DistributedCompilationPlanISR`
- `ArtifactLocationISR`
- `FederationAgreementISR`
- `FaultRecoveryPlanISR`

## Core Runtime Components

- Distributed runtime
- Scheduler
- Resource manager
- Simulation cluster
- Distributed compiler
- Global artifact repository
- Federation layer
- Fault-tolerance framework
- Autoscaling engine
- Observability platform
- Distributed secret and identity manager

## Acceptance Criteria

The phase is complete when:

1. Evolution campaigns can execute across multiple compute regions.
2. Simulation workloads can be scheduled elastically.
3. Compiler workloads can be distributed deterministically.
4. Artifact integrity is preserved across regions.
5. Node failures do not corrupt evolution history.
6. The system can recover interrupted campaigns.
7. Distributed execution remains auditable.
8. Resource usage is observable and governable.

## Critical Safety Constraint

Distribution must not weaken constitutional enforcement.

Every distributed node must verify policy, identity, and artifact integrity before execution.

---

# Phase 30 — Autonomous Software Engineering Network

## Objective

Integrate all previous phases into a complete autonomous software engineering ecosystem.

## Constitutional Prompt

> Integrate every previous phase into a constitutional network of autonomous engineering organizations capable of discovering requirements, designing architectures, evolving ISR representations, generating software, verifying correctness, deploying systems, operating services, learning from production, collaborating across organizations, and continuously improving themselves while maintaining constitutional integrity.

## Primary ISR Extensions

- `NetworkISR`
- `OrganizationFederationISR`
- `GlobalEngineeringMemoryISR`
- `CrossOrganizationContractISR`
- `NetworkGovernanceISR`
- `EndToEndPipelineISR`
- `GlobalMonitoringISR`
- `NetworkSecurityFrameworkISR`
- `UniversalEvolutionRuntimeISR`

## Core Runtime Components

- Autonomous engineering network architecture
- Organization federation layer
- Global engineering memory
- Cross-organization coordination engine
- Universal evolution runtime
- End-to-end automation pipeline
- Global monitoring platform
- Constitutional security framework
- Performance optimization framework
- Full API suite
- Complete test and verification framework
- Operational runbooks
- Reference implementations

## Acceptance Criteria

The phase is complete when:

1. Multiple autonomous organizations can collaborate on a shared engineering objective.
2. Requirements can flow from discovery to architecture to ISR to generated software.
3. Generated software can be verified, deployed, monitored, and improved.
4. Production learning can feed future evolution proposals.
5. Cross-organization work respects federated constitutional agreements.
6. Global monitoring provides end-to-end observability.
7. Security and governance are enforced across the network.
8. The network can evolve its own capabilities without violating constitutional invariants.

## Critical Safety Constraint

The network is not a single omnipotent autonomous entity.

It is a governed federation of bounded autonomous organizations.

---

# Recommended Implementation Order

Although the phases are numbered narratively, the safest implementation order is slightly different.

## Foundational Layer

Build or harden first:

1. **Phase 28 — Constitutional Governance**
2. **Phase 23 — Enterprise Knowledge Graph**
3. **Phase 25 — Universal Software Compiler**
4. **Phase 21 — Self-Evolution Engine**

These create the governance, memory, compilation, and evolution backbone.

## Organizational and Learning Layer

Then build:

5. **Phase 22 — Autonomous Engineering Civilization**
6. **Phase 26 — Continuous Learning Infrastructure**
7. **Phase 27 — Marketplace & Plugin Ecosystem**

These enable persistent organizations, production learning, and safe extensibility.

## Scale and Ecosystem Layer

Then build:

8. **Phase 29 — Distributed Evolution Cloud**
9. **Phase 24 — Autonomous Product Factory**
10. **Phase 30 — Autonomous Software Engineering Network**

These scale the platform into distributed, product-generating, networked autonomy.

---

# Cross-Phase Dependency Map

## Phase 21 Depends On

- ISR core
- Verification framework
- Governance policies
- Knowledge graph
- Runtime observability
- Rollback infrastructure

## Phase 22 Depends On

- Agent runtime
- Governance
- Organizational memory
- Knowledge graph
- Task execution framework

## Phase 23 Depends On

- ISR artifacts
- Version control
- Telemetry
- Organizational memory
- Traceability metadata

## Phase 24 Depends On

- Product ISR
- Universal compiler
- Deployment infrastructure
- Analytics
- Governance
- Safety review

## Phase 25 Depends On

- ISR stability
- Target capability registry
- Validation framework
- Artifact signing
- Reproducible builds

## Phase 26 Depends On

- Telemetry pipeline
- Knowledge graph
- Incident management
- Governance filters
- Evolution proposal intake

## Phase 27 Depends On

- Plugin sandboxing
- Identity and signing
- Dependency resolution
- Governance
- Compatibility validation

## Phase 28 Depends On

- Policy engine
- Audit logging
- Version control
- Approval workflows
- Lineage tracking

## Phase 29 Depends On

- Distributed identity
- Artifact repository
- Scheduler
- Fault tolerance
- Observability

## Phase 30 Depends On

All previous phases.

It is the integration and federation phase, not a standalone capability.

---

# Required Cross-Phase APIs

To keep the ecosystem coherent, the following API families should be standardized across all phases.

## 1. ISR API

- Create ISR revision
- Get ISR by hash
- Resolve ISR lineage
- Compare ISR revisions
- Validate ISR schema
- Freeze ISR version
- Attach evidence to ISR

## 2. Governance API

- Evaluate policy
- Request approval
- Register governance exception
- Query compliance status
- Retrieve audit trail
- Revoke approval
- Suspend activity

## 3. Evolution API

- Propose evolution
- Simulate evolution
- Verify evolution
- Promote evolution
- Roll back evolution
- Query evolution history
- Compare evolution candidates

## 4. Organization API

- Create organization
- Register agent
- Assign role
- Delegate authority
- Allocate task
- Resolve conflict
- Query organizational memory

## 5. Knowledge Graph API

- Ingest entity
- Create relation
- Query graph
- Trace lineage
- Search semantically
- Explain inference
- Version ontology

## 6. Compiler API

- Submit compilation plan
- Register backend
- Query target capabilities
- Compile ISR
- Validate artifact
- Retrieve artifact manifest
- Reproduce build

## 7. Learning API

- Ingest telemetry
- Record feedback
- Analyze incident
- Generate recommendation
- Correlate signals
- Escalate to evolution engine

## 8. Marketplace API

- Publish extension
- Validate extension
- Install extension
- Revoke extension
- Query dependencies
- Inspect permissions
- Quarantine extension

## 9. Distributed Cloud API

- Submit job
- Allocate resources
- Monitor campaign
- Recover failed job
- Register node
- Federate cluster
- Query artifact location

## 10. Network API

- Federate organizations
- Negotiate collaboration contract
- Share governed memory
- Coordinate cross-org pipeline
- Query global monitoring
- Enforce network policy

---

# Cross-Phase Testing Requirements

Each phase must include a test suite, but advanced phases require additional test classes.

## Mandatory Test Classes

### Unit Tests

Validate isolated functions, services, and data transformations.

### Contract Tests

Validate API compatibility between phases.

### Integration Tests

Validate end-to-end behavior across runtime components.

### Regression Tests

Ensure new capabilities do not break prior guarantees.

### Policy Tests

Ensure constitutional rules are enforced.

### Security Tests

Validate authentication, authorization, sandboxing, signing, and abuse prevention.

### Rollback Tests

Ensure every promoted change can be reversed.

### Audit Tests

Ensure every significant action can be reconstructed.

## Advanced Test Classes

### Evolution Safety Tests

Verify that unsafe self-modifications are rejected.

### Organizational Governance Tests

Verify that agents cannot exceed delegated authority.

### Knowledge Lineage Tests

Verify traceability from requirement to incident.

### Product Safety Tests

Verify that customer-facing products cannot launch without approval.

### Compiler Fidelity Tests

Verify that generated code preserves ISR semantics.

### Learning Mediation Tests

Verify that production learning cannot directly mutate production.

### Marketplace Isolation Tests

Verify that malicious or incompatible plugins are contained.

### Distributed Fault Tests

Verify resilience under node failure, network partition, and resource exhaustion.

### Network Federation Tests

Verify cross-organization collaboration under federated governance.

---

# Cross-Phase Documentation Requirements

Each phase must produce documentation for multiple audiences.

## 1. Executive Documentation

- Purpose of the phase
- Business value
- Risk posture
- Governance implications
- Operational impact

## 2. Architecture Documentation

- Component diagram
- Data flow
- ISR extensions
- Integration points
- Failure modes
- Security boundaries

## 3. Operator Documentation

- Deployment guide
- Configuration guide
- Monitoring guide
- Incident response
- Rollback procedures

## 4. Developer Documentation

- API reference
- SDK usage
- Extension guide
- Testing guide

## 5. Governance Documentation

- Policy definitions
- Approval workflows
- Audit procedures
- Compliance evidence
- Exception handling

## 6. Safety Documentation

- Safety case
- Threat model
- Abuse cases
- Containment strategy
- Human override procedures

---

# Major Risks Across Phases 21–30

## Risk 1: Uncontrolled Self-Modification

If the Self-Evolution Engine can modify the platform without verification, the system becomes unsafe.

### Mitigation

- Mandatory simulation
- Formal verification where possible
- Governance approval
- Staged promotion
- Automatic rollback
- Immutable evolution history

## Risk 2: Agent Organizations Exceeding Authority

Autonomous organizations may accumulate permissions beyond their charter.

### Mitigation

- Explicit delegation grants
- Time-bound authority
- Periodic reauthorization
- Organizational audits
- Permission revocation
- Conflict escalation

## Risk 3: Knowledge Graph Becomes an Unverified Oracle

The graph may be treated as truth even when evidence is incomplete.

### Mitigation

- Evidence-backed nodes
- Confidence scoring
- Source lineage
- Access-controlled inference
- Periodic graph audits

## Risk 4: Product Factory Launches Unsafe Products

Autonomous product generation may create legal, safety, or reputational risk.

### Mitigation

- Mandatory product safety review
- Compliance validation
- Billing controls
- Data protection checks
- Human launch approval for high-risk categories
- Kill-switch capability

## Risk 5: Compiler Backends Introduce Semantic Drift

Different backends may interpret ISR inconsistently.

### Mitigation

- Backend conformance tests
- Semantic validation suites
- Reference implementations
- Reproducible builds
- Backend certification

## Risk 6: Learning Loops Become Self-Reinforcing

Production signals may bias the system toward unsafe optimization targets.

### Mitigation

- Learning signals are advisory
- Multi-signal validation
- Human review for high-impact recommendations
- Constitutional filters
- Periodic learning audit

## Risk 7: Marketplace Extensions Break Platform Integrity

Third-party plugins may introduce vulnerabilities or instability.

### Mitigation

- Sandboxing
- Signed manifests
- Capability-based permissions
- Compatibility validation
- Revocation infrastructure
- Quarantine mode

## Risk 8: Distributed Evolution Loses Consistency

Distributed execution may create conflicting artifacts or partial promotions.

### Mitigation

- Deterministic job manifests
- Artifact hashing
- Distributed consensus for promotion
- Idempotent operations
- Recovery plans
- Global audit log

## Risk 9: Networked Autonomy Becomes Opaque

A network of autonomous organizations may become difficult to understand or control.

### Mitigation

- Federated governance
- Global lineage
- Cross-org audit trails
- Network monitoring
- Constitutional security boundaries
- Human supervisory interfaces

---

# Phase Completion Definition

A phase should not be considered complete if it only has working code.

A phase is complete only when:

1. Its specification is approved.
2. Its ISR extensions are versioned and documented.
3. Its runtime components are deployed in a testable environment.
4. Its APIs are stable and documented.
5. Its test suite passes.
6. Its governance policies are enforceable.
7. Its audit trail is reconstructable.
8. Its rollback path is demonstrated.
9. Its documentation is complete.
10. Its integration with prior phases is verified.

---

# Final Coherence Statement

Phases 21–30 transform the platform from an autonomous software engineering system into a **self-improving, federated engineering ecosystem**.

The progression is:

- **Phase 21**: The platform can evolve itself.
- **Phase 22**: Agents become organizations.
- **Phase 23**: Organizations gain shared memory.
- **Phase 24**: Engineering becomes product creation.
- **Phase 25**: ISR becomes universally compilable.
- **Phase 26**: Production becomes a learning source.
- **Phase 27**: The platform becomes extensible.
- **Phase 28**: Evolution becomes constitutionally governed.
- **Phase 29**: Evolution becomes distributed and scalable.
- **Phase 30**: Everything becomes a coordinated autonomous engineering network.

The most important design principle is this:

> Autonomy must never outrun constitutionality.

Every advanced capability must remain:

- Represented in ISR
- Governed by policy
- Verified before promotion
- Observable in operation
- Reversible under failure
- Explainable to humans
- Auditable over time

With that discipline, Phases 21–30 form a coherent path toward a safe, scalable, self-improving software engineering civilization rather than an uncontrolled autonomous system.]

---

# Phase 26 — Continuous Learning Infrastructure — Closure Record

**Status:** Complete (closed)

**Implementation package:** `learning/` — a governed, constitutional continuous-learning
infrastructure that ingests operational telemetry, incidents, customer feedback, cost,
performance, and security signals, and routes derived recommendations to the Self-Evolution
Engine or human owners.

**ISR extensions implemented** (per Phase 26 §Primary ISR Extensions):
`LearningSignalISR`, `TelemetryStreamISR`, `IncidentAnalysisISR`, `CustomerFeedbackISR`,
`CostObservationISR`, `PerformanceObservationISR`, `SecurityFindingISR`,
`RecommendationISR`, `ArchitectureFeedbackISR`.

**Runtime components:**
- Telemetry pipeline — `learning/telemetry`
- Feedback & recommendation compiler — `learning/recommendations`, `learning/feedback_compiler`
- Analytics (correlation, drift, anomaly, baselines) — `learning/analytics`
- Observability dashboards — `learning/observability`
- Knowledge sync (memory consolidation) — `learning/knowledge_sync`
- Governance safety & quality gates — `learning/governance`
- Production learning certification — `learning/production_certification`
- Evolution integration gateway — `learning/evolution_integration`
- Orchestration — `learning/engine` / `learning/pipeline`

**Constitutional alignment:** Phase 28 Governance Kernel integration is enforced through
`learning/governance` (safety + quality); no learning signal directly mutates production
architecture — outcomes are proposals routed through verification and governance.

**Acceptance-criteria coverage:**
1. Telemetry ingested at scale — `learning/telemetry/adapters`
2. Incidents correlated to architecture/code/deploy/config — `learning/analyzers`, `learning/analytics/correlation`
3. Customer feedback linked to artifacts — `learning/feedback_compiler`
4. Cost/performance → optimization recommendations — `learning/analytics`, `learning/recommendations`
5. Security findings → remediation proposals — `learning/governance`
6. Recommendations routed to Evolution Engine / owners — `learning/evolution_integration/gateway`
7. Learning signals cannot directly mutate production architecture — enforced by `learning/governance/safety`
8. Outcomes measurable & auditable — `learning/observability` + audit trails

**Verification:** Phase 26 suites (telemetry adapter framework, learning pipeline
certification, production learning certification, observability dashboards, governance safety
controls, production feedback fitness, operations telemetry/recommendation/drift/anomaly/
classification/constitutional-boundary, knowledge sync, recommendation analytics) pass
**99 tests**, within the full green run:

```text
python -m pytest -> 936 passed, 0 failed
```

---

# Phase 27 — Marketplace & Plugin Ecosystem — Closure Record

**Status:** Complete (closed)

**Implementation package:** `marketplace_plugins/` (v1.0) — secure, constitutional marketplace
for third-party extensions, compiler backends, evolution mutators, telemetry adapters,
knowledge ingestors, verification engines, domain packs, infrastructure templates, and UI
extensions.

**ISR extensions:** `PluginManifestISR`, `ExtensionCapabilityISR`, `DependencyGraphISR`,
`SandboxPolicyISR`, `PublisherIdentityISR`, `MarketplaceListingISR`,
`CompatibilityReportISR`, `RevocationRecordISR`.

**Constitutional alignment:** publisher-identity validation + manifest signature verification
+ high-risk capability approval + dependency compatibility gating + sandbox enforcement +
quarantine-on-violation + revocation with dependent cascade. Phase 28 `GovernanceKernel`
is wired into `GovernanceGateway` as an opt-in policy delegate (reference heuristic applies
when no kernel is supplied).

**Acceptance criteria:** all 16 criteria in canonical Phase 27 are covered;
unauthorized ISR mutation is blocked and quarantines the plugin
(`test_sandbox_blocks_unauthorized_isr_mutation`), and permitted
network/ISR actions are enforced via `SandboxPolicyISR`
(`test_sandbox_allows_permitted_actions`).

**Verification:**

```text
python -m pytest tests/test_marketplace_plugin_ecosystem.py -q -> 10 passed
```

Full suite remains green (**936 passed, 0 failed** at Phase 27 closure;
**911 passed, 0 failed** after Phase 29 canonical replacement).

---

# Phase 28 - Constitutional Governance - Closure Record

**Status:** Complete (closed)

**Implementation:** `constitutional_architecture/governance/` - the Phase 28
Governance Kernel (`GovernanceKernel` PDP/PAP/PEP) was already present and wired
into the marketplace gateway; this increment closes the remaining Phase 28
specification gap declared in `phase.md` (the components and ISR extensions
that were absent).

**ISR extensions implemented (additive to `schemas.py`):** `PolicyRuleISR`,
`ApprovalStageISR`, `ApprovalWorkflowISR`, `PolicyViolationISR`,
`ComplianceReportISR`, `AuditEvidenceISR`, `ChangeLineageISR`,
`GovernanceExceptionISR`, `ConstitutionVersionISR` (+ supporting enums
`PolicyEffect`, `VotingRuleKind`, `VersionStatus`, `ChangeKind`,
`ExceptionSeverity`, `ComplianceOutcome`). Also added a `normalize_policy_set()`
compatibility adapter projecting the legacy `PolicySetISR.policy_rules` into the
canonical `PolicyRuleISR` envelope (assumption 2).

**Runtime subsystems implemented:**
- `voting.py` - `VotingSystem` with replaceable `TallyStrategy` per
  `VotingRuleKind` (unanimity / simple-majority / weighted-majority);
  fail-closed (ties, quorum shortfall, deadline expiry, missing strategies all
  deny; malformed ballots raise `VotingError`).
- `audit.py` (additive) - `AuditEvidenceRecorder` (hash-chained, tamper-evident
  evidence ledger) + `ComplianceReportLog` (append-only report projection).
  The existing `AuditFramework` is preserved unchanged.
- `versioning.py` - `VersionManager` over an append-only, strictly-increasing
  semver chain of `ConstitutionVersionISR`; ratification requires an approved
  `VoteOutcome`; every ratification emits a `ChangeLineageISR`; superseded
  heads become `SUPERSEDED`. Includes `InMemoryConstitutionVersionRepository`
  (reference) behind a `ConstitutionVersionRepository` port.
- `exceptions.py` - `ExceptionRegistry` (immutable-while-granted
  `GovernanceExceptionISR`; revocation tracked separately; expiry-aware
  `active()`).
- `governance_dashboard.py` - `GovernanceDashboard` read-only projection
  (`GovernanceView`); holds no write capability (single-PDP principle).
  Named `governance_dashboard` to avoid shadowing the existing `dashboard/`
  package.
- `integration.py` - `GovernedKernel`, a composition wrapper that preserves the
  wrapped `GovernanceKernel.evaluate` contract byte-for-byte while recording
  evidence and providing fail-closed amendment authorization.

**Integration:** `GovernedKernel` is wired into `marketplace_plugins/engine.py`
`GovernanceGateway` as an opt-in (`use_governance_extensions=True`, default
`False`). With the flag off (the default), the gateway delegates to the raw
kernel unchanged, so `test_governance_kernel_delegates_approval` is green
without modification (regression anchor preserved).

**Verification:**

```text
python -m pytest tests/test_phase28_schemas.py tests/test_phase28_voting.py tests/test_phase28_versioning.py tests/test_phase28_dashboard.py tests/test_phase28_integration.py tests/test_marketplace_plugin_ecosystem.py -q -> 46 passed
python -m pytest -q -> 952 passed, 0 failed
```

**ADR:** `folder/30.md`-style ADR-Phase28-constitutional-governance-closure
appended (decision: additive schemas + replaceable subsystems + composition
wrapper; trade-off: in-memory repositories only, durable adapters deferred).

---

# Phase 29 - Distributed Evolution Cloud (Canonical) - Closure Record

**Status:** Complete (closed)

**Implementation package:** `distributed_evolution/` (canonical), which replaces the
retired `evolution/cloud/` draft. Policy-governed, ISR-audited distributed evolution
across a compute-node federation with fault recovery, autoscaling, content-addressed
artifacts, and a verifiable audit chain.

**ISR extensions:** `SimulationCampaignISR`, `DistributedJobISR`, `ComputeNodeISR`,
`ComputeClusterISR`, `ResourceAllocationISR`, `DistributedCompilationPlanISR`,
`ArtifactLocationISR`, `ArtifactRecord`, `FederationAgreementISR`,
`FaultRecoveryPlanISR`, `AuditEvent`, `CloudMetrics`.

**Constitutional alignment:** node policy-version attestation
(`attested` flag; non-matching policy keeps the node `SUSPENDED` and unschedulable);
`PolicyViolationError` on node/policy-version mismatch; only `ACTIVE`+attested nodes
are schedulable; the full ISR audit chain (`verify_audit_chain`) hashes each
`AuditEvent` (event_id, event_type, ids, payload, created_at, previous_hash,
event_hash) into an immutable log.

**Verification:**

```text
python -m pytest tests/test_distributed_evolution_cloud.py -q -> 6 passed
python -m pytest -q -> 911 passed, 0 failed
```

**Tests (verbatim from folder/29.md):** `test_campaign_completes_with_artifacts`,
`test_unattested_node_is_not_scheduled`, `test_node_failure_recovery`,
`test_autoscaling_adds_nodes`, `test_artifact_integrity`,
`test_api_campaign_lifecycle`. The API test exercises register-node -> submit-campaign
-> run -> metrics (`completed_jobs == 2`) -> `/audit/verify` (`valid is True`).

**Notes:**
- Removed `evolution/cloud/` and the draft test files
  `tests/test_distributed_evolution_cloud.py` and
  `tests/test_distributed_evolution_cloud_api.py` (31 draft tests); replaced with the
  canonical package and 6 canonical tests (net suite 936 - 25 = 911 passed).
- `canonical_json` carries a deterministic `datetime` -> `isoformat` default so the
  audit-chain hash (computed over the ISO-8601 timestamp string) round-trips under
   pydantic v2 `datetime` coercion; pydantic 2.13 otherwise raises `TypeError` inside
   `verify_audit_chain`. All model field types remain verbatim from `29.md`.

---

# Phase 30 - Autonomous Software Engineering Network (Canonical) - Closure Record

**Status:** Complete (closed)

**Implementation package:** `autonomous_network/` (v1.0.0), the canonical integration
layer that unifies all prior phases (organization registration and attestation,
cross-organization contracts, governance-gated end-to-end pipeline, reference stage
adapters, global engineering memory, hash-chained network audit, and global
monitoring). File layout matches `folder/30.md` exactly: `__init__.py`, `models.py`,
`adapters.py`, `engine.py`, `api.py`.

**ISR extensions:** `NetworkISR`(via `PipelineRun`), `OrganizationFederationISR`
(via `OrganizationRegistration` + `CrossOrganizationContract`),
`GlobalEngineeringMemoryISR` (via `MemoryRecord`), `NetworkGovernanceISR`
(via `NetworkGovernanceGateway` / `NetworkGovernanceDecision`),
`EndToEndPipelineISR` (via `PipelineRun` + `StageRun` + `StageResult`),
`GlobalMonitoringISR` (via `GlobalMonitoringSnapshot`),
`NetworkSecurityFrameworkISR` (via `NetworkAlert` + attestation + policy-version gating),
`UniversalEvolutionRuntimeISR` (governance-checked `HIGH_IMPACT_STAGES` +
`learning-mediated evolution proposals`).

**Constitutional alignment:** the network is explicitly NOT a single omnipotent
autonomous entity - it is a governed federation of bounded organizations. Enforced:
organization attestation (non-matching policy version => `attested=False`,
`SUSPENDED`, blocked from contracts/pipelines), contract governance approval
(DENY => `REJECTED` + `PermissionError`), stage-level governance checks for
`HIGH_IMPACT_STAGES` (EVOLUTION, DEPLOYMENT, LEARNING), suspended-organization
blocking, verification-before-deployment, missing-adapter failure, hash-chained
network events (`verify_events`), and alerts on every failure/suspension.

**Verification:**

```text
python -m pytest tests/test_autonomous_software_engineering_network.py -q -> 5 passed
python -m pytest -q -> 916 passed, 0 failed
```

**Tests (verbatim from folder/30.md):** `test_end_to_end_pipeline_completes`,
`test_unattested_organization_cannot_form_contract`, `test_governance_can_reject_contract`,
`test_suspended_organization_blocks_pipeline_submission`,
`test_missing_stage_adapter_fails_pipeline`. The E2E test drives the full
REQUIREMENT_ANALYSIS -> ISR_CONSTRUCTION -> EVOLUTION -> VERIFICATION ->
COMPILATION -> DEPLOYMENT -> MONITORING -> LEARNING pipeline, asserts all 8 stage
artifacts, `evolution_proposal` in the learning artifact, `verify_events() is True`,
and a monitoring snapshot (`completed_runs == 1`, `failed_runs == 0`,
`active_contracts == 1`).

**Notes:**
- `canonical_json` (in `autonomous_network/models.py`) carries the same deterministic
  `datetime` -> `isoformat` (and `Enum` -> `value`) default hook as Phase 29 so the
  network audit chain (`verify_events`) is verifiable under pydantic 2.13; without it
  `json.dumps` raises `TypeError` on the coerced `NetworkEvent.created_at`. All model
  field types remain verbatim from `30.md`.
   - The Phase 21-30 constitutional sequence is now complete end-to-end.

---

# Option (d) - Governance Fitness Dimension (Phase 28 Future Evolution closure)

**Status:** Complete (closed)

**Context:** the Phase 28 ADR (`folder/adr-phase28-constitutional-governance-closure.md`)
explicitly deferred "Governance metrics as fitness dimensions" to the fitness domain
to avoid coupling. This increment closes that deferral with a pure, framework-neutral
module that projects the Phase 28 ISR into a bounded multi-objective fitness vector —
the selection half of the governance evolutionary loop.

**Implementation:** `constitutional_architecture/governance/governance_fitness.py`
(core only — never imports the fitness engine) plus
`constitutional_architecture/engine/bridges/governance_fitness_bridge.py`
(the framework→engine adapter seam).

**ISR inputs (framework-neutral):** `GovernanceFitnessInput` carries
`ConstitutionVersionISR`, `ComplianceReportISR`, `GovernanceExceptionISR`,
`AuditEvidenceISR`, `ChangeLineageISR`, `PolicyRuleISR` only.

**Objectives (vector-primary, each bounded in [0.0, 1.0]):**
- `constitutional_currency` — ratified head freshness (fail-closed: no head / >1 head ⇒ 0.0).
- `compliance_posture` — weighted COMPLIANT/INDETERMINATE/NON_COMPLIANT average.
- `exception_hygiene` — open+overdue exception penalty (severity-weighted + overdue penalty).
- `audit_integrity` — `AuditEvidenceISR` chain continuity (breaks ⇒ 0.0; empty ⇒ empty-chain score).
- `ratification_rigor` — fraction of ratified versions bearing both a ratification workflow and lineage.
- `policy_coverage` — rule count vs. configurable target (capped at 1.0).

**Constitutional alignment:** vector-primary (no scalar default — `composite` is opt-in
`None`); fail-closed on absence of evidence; deterministic per `(input, now, config)`;
observable-by-design (each score carries a human-readable rationale); `collect_governance_state`
and `to_fitness_objectives` form the adapter seam, mapping the result into the Pareto-optimiser's
objective-map shape.

**Adapter seam (framework-neutral):** `collect_governance_state` accepts the Phase 28 runtime
subsystems (VersionManager history/lineage, ComplianceReportLog, ExceptionRegistry.active(now),
AuditEvidenceRecorder.entries, normalized PolicyRuleISR set) and assembles `GovernanceFitnessInput`.
The caller supplies the post-revocation active exception set (sourcing contract).
`to_fitness_objectives` returns a plain `dict[str, float]` copy of the objective vector so the
optimiser sees the full vector (never collapsed). This seam is the **only** point requiring the
platform fitness-evaluator interface signature; the core is finalised and untouched.

**Tests:** `tests/test_governance_fitness.py` (35 tests) — boundedness, fail-closed
absence, each objective's happy/sad path, composite opt-in, determinism, config overrides,
and the adapter seam (active-exception sourcing + chain-order preservation).

**Verification:**

```text
python -m pytest tests/test_governance_fitness.py -q -> 35 passed
python -m pytest tests/test_governance_fitness.py tests/test_phase28_schemas.py tests/test_phase28_voting.py tests/test_phase28_versioning.py tests/test_phase28_dashboard.py tests/test_phase28_integration.py -q -> 70 passed (35 option (d) + 35 Phase 28 core)
python -m pytest tests/test_governance_fitness_bridge.py -q -> 11 passed
python -m pytest -q -> 998 passed, 0 failed
```

**Future Evolution:** the canonical Phase 21 optimiser is
`constitutional_architecture/engine/pareto_optimizer.py::ParetoOptimizer`, which
consumes `Individual.fitness` as an `engine.fitness.FitnessVector` (a
`dict[str, float]` of dimensions normalised to [0.0, 1.0]). `to_fitness_objectives`
already returns exactly that dict shape (the six governance dimension keys), so the
core seam is shape-compatible. To plug governance into the engine:

- Build `FitnessVector.from_dict(to_fitness_objectives(result))` and **merge** it
  with the architecture fitness vector (e.g. `arch_vector.add(gov_vector)`) so every
  candidate shares the full union of dimension keys. `FitnessVector.dominates`
  raises `ValueError` on mismatched dimension sets, so shared keys are mandatory.
- Instantiate `ParetoOptimizer(use_composite=False)` so the six governance dimensions
  survive dominance ranking. Under the default `use_composite=True`, the optimizer
  reduces to four hardcoded composite keys (`structural_quality`,
  `operational_quality`, `security_compliance`, `knowledge_quality`) and governance
  dimensions would be silently dropped.
- Register the wired dimension via `engine/plugins.py::FitnessEvaluatorPlugin`
  (the canonical fitness-evaluator registration seam) so governance evaluation is a
  discoverable, replaceable contributor rather than compiled into the engine.

---

# Option (a) — Governance Chromosome Family (Variation Half) — Closure Record

**Status:** Complete (closed)

**Context:** option (d) added governance fitness and bridged it into the Pareto
optimiser, but the merged governance vector was platform-wide and identical
across candidates, hence Pareto-neutral. The loop had selection but no variation.
This increment supplies the governance chromosome family — the variation half —
so candidates express distinct governance architectures that the six governance
fitness dimensions select among.

**Implementation:**
- `constitutional_architecture/governance/schemas.py` (additive) — `VersioningStrategyKind` + `GovernanceDesignISR` (the expressed governance architecture of a candidate: voting rule, quorum, approval stages, policy rule count, fail-closed default, exception policy, audit mandate, compliance mandate, versioning strategy). Each field drives one objective (independent evolvability).
- `constitutional_architecture/governance/governance_genes.py` — `GovernanceChromosome` of eight independent, genome-agnostic genes (`VotingRuleGene`, `QuorumGene`, `ApprovalStagesGene`, `PolicyCoverageGene`, `ExceptionPolicyGene`, `AuditMandateGene`, `ComplianceMandateGene`, `VersioningStrategyGene`) with own value spaces, deterministic mutation, and uniform per-gene crossover; `express()` → `GovernanceDesignISR`, `project_approval_workflow()` → concrete approval ISR.
- `constitutional_architecture/governance/governance_design_fitness.py` — `GovernanceDesignFitness` scoring a candidate's `GovernanceDesignISR` across the **same six objective names** as option (d)'s operational scoring (preserves the `GovernanceFitnessBridge` dimension-set-consistency invariant); `design_objectives(...)` helper.
- `constitutional_architecture/engine/bridges/governance_candidate_fitness.py` — candidate-scoped bridge: `GovernanceCandidateFitnessProvider` scores each candidate on its OWN expressed `GovernanceDesignISR` (via the `CandidateGovernanceAccess` port, satisfying `governance_chromosome(candidate)`), and `merge_population_with_candidate_governance` merges each candidate's own governance vector with its architecture vector. Replaces the platform-wide bridge during evolution so governance becomes discriminating.

**Constitutional alignment:** ISR-first expression (genes → ISR; engine never reads gene internals); multi-objective vector primary; shared objective vocabulary with option (d); genes encode architectural decisions, not implementation detail; deterministic sampling/mutation/crossover; independently testable; purely additive.

**Key design decision:** a candidate has no realized governance history, so governance is scored as a **design**, not a state — hence `GovernanceDesignISR` + a design-fitness evaluator rather than reusing option (d)'s operational scoring.

**Verification:**
```text
python -m pytest tests/test_governance_genes.py tests/test_governance_design_fitness.py -q -> 21 passed (9 gene + 12 design-fitness)
python -m pytest tests/test_governance_candidate_fitness.py -q -> 4 passed
python -m pytest -q -> 1023 passed, 0 failed
```

**ADR:** addendum appended to `folder/adr-phase28-constitutional-governance-closure.md`.

**Open adaptation points (genome contract, to be confirmed — no contract fabricated):**
1. Genome chromosome-family registry — register `GovernanceChromosome.sample` (via `seed_governance_chromosome`) as family `"Governance"`.
2. Gene/Chromosome base contract — if the genome defines a base `Gene`, wrap these (semantics transfer unchanged).
3. Candidate model — satisfy the declared `CandidateGovernanceAccess` port: a candidate must expose its governance chromosome via `governance_chromosome(candidate)` so the candidate-scoped provider scores it. The port and merge are already concrete; only the genome-side adapter is needed.






