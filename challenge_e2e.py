"""
E2E Challenge: Evolve a monolithic e-commerce shop through all 7 phases.
"""

import time, pprint, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─── Phase 0: Build Initial ISR ─────────────────────────────────────────────
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Service, Operation, OperationType
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldType, FieldCardinality
from constitutional_architecture.isr.model.interface import Interface, InterfaceType, Endpoint, HttpMethod
from constitutional_architecture.isr.model.isr import ISR

M = HttpMethod

monolith = ISR(
    system=System(
        id='shop-1', name='MonolithShop',
        description='A monolithic e-commerce platform',
        modules=(
            Module(
                id='mod-monolith', name='Monolith',
                entities=(
                    Entity(id='ent-user', name='User', fields=(
                        Field(name='id', field_type=FieldType.UUID, is_primary_key=True),
                        Field(name='email', field_type=FieldType.EMAIL, cardinality=FieldCardinality.REQUIRED),
                        Field(name='name', field_type=FieldType.STRING),
                    )),
                    Entity(id='ent-product', name='Product', fields=(
                        Field(name='id', field_type=FieldType.UUID, is_primary_key=True),
                        Field(name='name', field_type=FieldType.STRING), Field(name='price', field_type=FieldType.FLOAT),
                        Field(name='stock', field_type=FieldType.INTEGER),
                    )),
                    Entity(id='ent-order', name='Order', fields=(
                        Field(name='id', field_type=FieldType.UUID, is_primary_key=True),
                        Field(name='user_id', field_type=FieldType.UUID), Field(name='total', field_type=FieldType.FLOAT),
                        Field(name='status', field_type=FieldType.STRING),
                    )),
                ),
                services=(
                    Service(id='svc-api', name='APIGateway',
                        operations=(
                            Operation(id='op-login', name='login'),
                            Operation(id='op-list-products', name='listProducts', operation_type=OperationType.QUERY),
                            Operation(id='op-create-order', name='createOrder'),
                            Operation(id='op-pay', name='processPayment'),
                            Operation(id='op-ship', name='shipOrder'),
                        ), is_stateless=True,
                    ),
                ),
                interfaces=(
                    Interface(id='iface-public', name='PublicAPI', interface_type=InterfaceType.REST,
                        endpoints=(
                            Endpoint(id='ep-login', name='login', path='/api/login', method=M.POST),
                            Endpoint(id='ep-products', name='listProducts', path='/api/products', method=M.GET),
                            Endpoint(id='ep-orders', name='createOrder', path='/api/orders', method=M.POST),
                            Endpoint(id='ep-pay', name='pay', path='/api/payments', method=M.POST),
                        ),
                    ),
                ),
            ),
        ),
    ),
)

print("=" * 60)
print("PHASE 0: Initial Monolith ISR")
print(f"  Name: {monolith.system.name}")
print(f"  Modules: {len(monolith.system.modules)}")
print(f"  Entities: {sum(len(m.entities) for m in monolith.system.modules)}")
print(f"  Services: {sum(len(m.services) for m in monolith.system.modules)}")
print(f"  Hash: {monolith.content_hash[:16]}")
print()

# ─── Phase 1-2: Evolution Engine ────────────────────────────────────────────
print("=" * 60)
print("PHASE 1-2: Evolution Engine")

from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.engine.bridges.autonomous_pipeline import AutonomousPipeline
from constitutional_architecture.engine.mutation_registry import MutationRegistry
from constitutional_architecture.engine.mutation_operators import register_all_operators
from constitutional_architecture.verification.verification_result import VerificationLevel

config = EvolutionConfig(
    population_size=10, elite_count=2, max_generations=3, seed=42,
    mutation_rate=0.4, crossover_rate=0.2,
)

pipeline = AutonomousPipeline(config=config)

print(f"  Registry: {len(pipeline.registry.all_identifiers)} operators")
print(f"  Operators: {pipeline.registry.all_identifiers}")
print()

# Run evolution
t0 = time.perf_counter()
evolved = pipeline.run(monolith)
elapsed = time.perf_counter() - t0

print(f"  Evolved in {elapsed:.2f}s")
print(f"  Seed hash:   {monolith.content_hash[:16]}")
print(f"  Evolved hash: {evolved.content_hash[:16]}")
print(f"  Modules: {len(evolved.system.modules)}")
print(f"  Entities: {sum(len(m.entities) for m in evolved.system.modules)}")
print(f"  Services: {sum(len(m.services) for m in evolved.system.modules)}")
print(f"  History entries: {len(pipeline.history)}")
for h in pipeline.history:
    print(f"    gen={h['generations']} evolved={h['evolved_hash']} "
          f"ver={h['verification_passed']} eirs={h['eir_count']}")
print()

# ─── Phase 3: Compiler Pipeline ────────────────────────────────────────────
print("=" * 60)
print("PHASE 3: Compiler Pipeline")

from constitutional_architecture.compiler.pipeline import CompilerPipeline, CompilationConfig
from constitutional_architecture.compiler.compilation_config import OptimizationLevel

cconfig = CompilationConfig(
    project_name=evolved.system.name,
    target_backends=("fastapi",),
    output_dir="./generated",
    optimization_level=OptimizationLevel.STANDARD,
)
compiler = CompilerPipeline()
t0 = time.perf_counter()
cresult = compiler.compile(evolved, config=cconfig)
elapsed = time.perf_counter() - t0

print(f"  Compiled in {elapsed:.2f}s")
print(f"  Success: {cresult.success}")
print(f"  Artifacts: {cresult.artifact_count}")
print(f"  Targets: {cresult.targets_compiled}")
print(f"  Errors: {cresult.error_count}, Warnings: {cresult.warning_count}")
for d in cresult.diagnostics[:3]:
    print(f"    [{d.severity}] {d.message[:80]}")
print()

# ─── Phase 4: Verification Engine ───────────────────────────────────────────
print("=" * 60)
print("PHASE 4: Verification Engine")

from constitutional_architecture.verification.verification_engine import VerificationEngine
from constitutional_architecture.verification.verification_result import VerificationLevel

vengine = VerificationEngine()
t0 = time.perf_counter()
vreport = vengine.verify(evolved, max_level=VerificationLevel.L3_SECURITY)
elapsed = time.perf_counter() - t0

print(f"  Verified in {elapsed:.2f}s")
print(f"  Level achieved: {vreport.verification_level_achieved.name}")
print(f"  Approved: {vreport.approved_for_deployment}")
print(f"  Passed: {vreport.passed_checks}/{vreport.total_checks}")
print(f"  Failed: {vreport.failed_checks}, Warnings: {vreport.warning_checks}")
print(f"  Fitness: {pprint.pformat(vreport.fitness_contribution)}")
if vreport.blocking_failures:
    for bf in vreport.blocking_failures[:3]:
        print(f"    BLOCKER: {bf.name}: {bf.message[:80]}")
print()

# ─── Phase 5: Deployment (simulated via Deployment model) ───────────────────
print("=" * 60)
print("PHASE 5: Deployment Readiness")

from constitutional_architecture.isr.model.deployment import (
    Deployment, ScalingConfig, NetworkingConfig, MonitoringConfig, StorageConfig, SecretsConfig
)
from constitutional_architecture.isr.model.system import SystemMetadata

deploy = Deployment(
    id='deploy-shop-1', name='ShopProduction',
    scaling=ScalingConfig(min_instances=2, max_instances=20),
    networking=NetworkingConfig(expose_publicly=True, port=443),
    monitoring=MonitoringConfig(metrics_enabled=True, tracing_enabled=True),
    secrets=SecretsConfig(secrets=('DB_PASSWORD', 'JWT_SECRET', 'API_KEY')),
)

system_v2 = System(
    id=evolved.system.id, name=evolved.system.name,
    description=evolved.system.description,
    modules=evolved.system.modules,
    deployment=deploy,
    metadata=SystemMetadata(version='2.0', description='Evolved e-commerce platform'),
)

evolved_with_deploy = ISR(
    system=system_v2, version=evolved.version + 1,
)

print(f"  Deployment '{deploy.name}' configured")
print(f"  Scaling: {deploy.scaling.min_instances}-{deploy.scaling.max_instances} instances")
print(f"  Monitoring: metrics={deploy.monitoring.metrics_enabled}, tracing={deploy.monitoring.tracing_enabled}")
print(f"  ISR version: {evolved_with_deploy.version}")
print()

# ─── Phase 6: Operational Intelligence ──────────────────────────────────────
print("=" * 60)
print("PHASE 6: Operational Intelligence")

from constitutional_architecture.operations.telemetry_engine import TelemetryEngine
from constitutional_architecture.operations.metrics_collector import MetricPoint
from constitutional_architecture.operations.observation_model import (
    Observation, ObservationSeverity, ObservationSource, ObservationClassification
)
from constitutional_architecture.operations.drift_detector import RunningSystemSnapshot

telemetry = TelemetryEngine()

# Simulate metrics
for i in range(20):
    telemetry.ingest_metric(MetricPoint(
        name='cpu_usage', value=45 + (i * 2), service_name='APIGateway',
    ))
for i in range(10):
    telemetry.ingest_metric(MetricPoint(
        name='response_time_ms', value=200 + (i * 50), service_name='APIGateway',
    ))

telemetry.metrics_collector.set_threshold('cpu_usage', 80.0)
telemetry.metrics_collector.set_threshold('response_time_ms', 500.0)

# Simulate observations
telemetry.ingest_observation(Observation(
    id='obs-arch-1', source=ObservationSource.METRICS,
    severity=ObservationSeverity.WARNING,
    title='High coupling between services',
    description='Dependency cycle detected between APIGateway and downstream calls — architectural concern',
))
telemetry.ingest_observation(Observation(
    id='obs-bug-1', source=ObservationSource.LOGS,
    severity=ObservationSeverity.ERROR,
    title='Null pointer in order processing',
    description='Null pointer exception in createOrder — implementation bug in payment flow',
))

# Analyze
observations = telemetry.analyze()
print(f"  Metrics recorded: {telemetry.metrics_collector.total_points}")
print(f"  Observations produced: {len(observations)}")
for obs in observations:
    print(f"    [{obs.classification.value}] {obs.title[:60]}")
print()

# Fitness signals
signals = telemetry.produce_fitness_signals(
    deployment_id=deploy.id, isr_hash=evolved_with_deploy.content_hash,
)
print(f"  Fitness signals produced: {len(signals)}")
for sig in signals:
    print(f"    Classification: {sig.classification.value}")
    print(f"    Dimensions: {sig.dimensions}")

# Drift detection
snapshot = RunningSystemSnapshot(
    deployment_id='deploy-1',
    running_modules=('Monolith',),
    running_services=('APIGateway',),
    running_endpoints=('/api/login', '/api/products', '/api/orders'),
)
telemetry.ingest_snapshot(snapshot)
drift_obs = telemetry.analyze(evolved_with_deploy)
drift_had = telemetry.drift_detector.has_drift
print(f"  Drift detected: {drift_had}")
print()

# ─── Phase 7: Knowledge Engine ──────────────────────────────────────────────
print("=" * 60)
print("PHASE 7: Knowledge Engine")

from constitutional_architecture.knowledge.knowledge_engine import KnowledgeEngine
from constitutional_architecture.knowledge.pattern_repository import PatternEntry
from constitutional_architecture.knowledge.anti_pattern_repository import AntiPatternEntry
from constitutional_architecture.knowledge.mutation_repository import MutationRecordEntry
from constitutional_architecture.knowledge.knowledge_types import FitnessRecord, CompatibilityRecord

keng = KnowledgeEngine()

# Register patterns
keng.register_pattern(PatternEntry(
    name='CQRS', description='Command Query Responsibility Segregation — separate read/write models',
    category='architectural', tags=('scalability', 'patterns', 'event-driven'), evidence_count=15,
))
keng.register_pattern(PatternEntry(
    name='Event Sourcing', description='Store state changes as event sequence',
    category='architectural', tags=('patterns', 'audit'), evidence_count=12,
))
keng.register_pattern(PatternEntry(
    name='Strangler Fig', description='Gradually replace legacy with new implementation',
    category='architectural', tags=('migration', 'legacy'), evidence_count=8,
))

# Register anti-patterns
keng.register_anti_pattern(AntiPatternEntry(
    name='Big Ball of Mud', description='No discernible architecture, tangled deps',
    symptoms=('no clear boundaries', 'circular deps', 'shared-everything'),
    severity='critical', recommended_fixes=('extract bounded contexts', 'apply dependency inversion'),
))
keng.register_anti_pattern(AntiPatternEntry(
    name='Distributed Monolith', description='Microservices that must deploy together',
    symptoms=('shared databases', 'synchronous calls everywhere', 'coordinated deploys'),
    severity='critical', recommended_fixes=('async boundaries', 'DB per service', 'independent deployment'),
))

# Record mutation outcomes from the evolution run
for i, op_name in enumerate(pipeline.registry.all_identifiers):
    if i % 2 == 0:
        keng.record_mutation(MutationRecordEntry(
            operator_name=op_name, target_context='MonolithShop',
            fitness_delta={'complexity': -0.05, 'coupling': -0.03},
            accepted=True, generation=1,
        ))

# Record fitness
keng.record_fitness(FitnessRecord(
    mutation_type='structural_split_module',
    dimensions={'complexity': -0.15, 'maintainability': 0.12},
    sample_size=8, context='MonolithShop',
    avg_fitness_delta={'complexity': -0.12, 'maintainability': 0.10},
))

print(f"  Patterns: {keng.patterns.count}")
print(f"  Anti-patterns: {keng.anti_patterns.count}")
print(f"  Mutation records: {keng.mutations.total_mutations}")

# Query knowledge
pats = keng.query_patterns(tags=['scalability'])
print(f"  Patterns tagged 'scalability': {len(pats)}")
for p in pats:
    print(f"    - {p.name}")

# Detect anti-patterns on the monolith
ap_results = keng.detect_anti_patterns(
    'MonolithShop has a single module with all entities and services — no clear boundaries, circular deps possible'
)
print(f"  Anti-patterns detected: {len(ap_results)}")
for r in ap_results:
    print(f"    - {r.description[:80]}...")

# Get recommendations
recs = keng.get_recommendations(
    'MonolithShop needs to split its monolith into bounded contexts',
    constraints=['Event Sourcing'],
)
print(f"  Knowledge recommendations: {len(recs)}")
for r in recs:
    print(f"    [{r.category}] {r.title[:60]} (conf={r.confidence.value})")

# Snapshot
snap = keng.metrics_snapshot
print(f"  Metrics: {snap.total_queries} queries, {snap.hit_rate:.0%} hit rate")
print()

# ─── Summary ────────────────────────────────────────────────────────────────
print("=" * 60)
print("FINAL SUMMARY — 7 PHASE CHALLENGE")
print("=" * 60)
print(f"  Phase 0: Monolith ISR built ({monolith.content_hash[:16]})")
print(f"  Phase 1-2: Evolution completed ({evolved.content_hash[:16]})")
print(f"  Phase 3: Compilation {'PASSED' if cresult.success else 'FAILED'} ({cresult.artifact_count} artifacts)")
print(f"  Phase 4: Verification {'APPROVED' if vreport.approved_for_deployment else 'REJECTED'} "
      f"({vreport.passed_checks}/{vreport.total_checks} checks)")
print(f"  Phase 5: Deployment configured ({deploy.name}, v{evolved_with_deploy.version})")
print(f"  Phase 6: Operational Intelligence ({len(signals)} fitness signals, {drift_had=})")
print(f"  Phase 7: Knowledge Engine ({keng.patterns.count} patterns, {len(recs)} recommendations)")
print()
print("Challenge complete!")
