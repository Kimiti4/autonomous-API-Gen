"""CLI entry point for the Stratified Calibration Harness (Phase 31)."""
import argparse
import asyncio
import logging
import shutil

from tiannara.application.harness.manifest import StratifiedManifest
from tiannara.application.compiler.composition import build_project_compiler
from tiannara.application.compiler.project_compiler import ProjectCompilationError
from tiannara.application.compiler.verification import BundleVerifier
from tiannara.application.factory import (
    RematerializationRepairProvider,
    SoftwareFactory,
    SoftwareFactoryError,
)
from tiannara.application.factory.evidence_sink import make_factory_evidence_sink
from tiannara.application.materializer.materializer import RepositoryMaterializer
from tiannara.bootstrap import build_harness
from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger
from tiannara.infrastructure.sandbox.local_environment import LocalExecutionEnvironment
from tiannara.infrastructure.source_control.local_git import LocalGitBackend


def _default_verifier_factory(compilation_result) -> BundleVerifier:
    package = getattr(compilation_result, "system_name", "bundle")
    required = sorted(getattr(compilation_result, "files", {}).keys())
    return BundleVerifier(package=package, required_files=required)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(prog="tiannara", description="Phase 31 Stratified Calibration Harness")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run-calibration", help="Run the stratified calibration matrix")
    run.add_argument("--manifest", required=True)

    verify = sub.add_parser("verify-ledger", help="Verify the evidence hash chain")
    verify.add_argument("--ledger", required=True)

    create = sub.add_parser(
        "create", help="Compile an intent statement into a verified backend service bundle"
    )
    create.add_argument("statement", help="Natural-language intent statement")
    create.add_argument("--system-id", default=None, help="System identifier override")
    create.add_argument(
        "--provider", choices=["recorded", "live"], default="recorded",
        help="LLM provider mode (default: recorded, hermetic)",
    )
    create.add_argument(
        "--transcript", default=None,
        help="Path to a recorded transcript (required for recorded mode)",
    )
    create.add_argument("--out", default="out", help="Output directory for artifacts")
    create.add_argument(
        "--force", action="store_true",
        help="Bypass verification refusal (override is recorded in the manifest)",
    )
    create.add_argument("--branch", default="main", help="Git branch to commit to (default: main)")

    factory = sub.add_parser(
        "factory", help="Compile, verify, and repair an intent into a materialized repo"
    )
    factory.add_argument("statement", help="Natural-language intent statement")
    factory.add_argument("--transcript", required=True, help="Path to a recorded transcript")
    factory.add_argument("--out", required=True, help="Output directory (becomes the repo root)")
    factory.add_argument(
        "--provider", choices=["recorded", "live"], default="recorded",
        help="LLM provider mode (default: recorded, hermetic)",
    )
    factory.add_argument("--max-repair-attempts", type=int, default=2)
    factory.add_argument(
        "--force", action="store_true",
        help="Bypass verification refusal (recorded in manifest + evidence)",
    )
    factory.add_argument(
        "--ledger", default="evidence/factory.jsonl",
        help="Durable JSONL evidence ledger for factory outcomes (appended, hash-chained)",
    )

    cal = sub.add_parser(
        "calibrate", help="Phase-31: calibrate every backend against an ISR corpus"
    )
    cal.add_argument("--corpus", default=None, help="JSON corpus of SystemModels (default: built-in)")
    cal.add_argument(
        "--generate", type=int, default=None,
        help="Generate N stratified SystemModels seeded deterministically (default: 0 -> none)",
    )
    cal.add_argument(
        "--seed", type=int, default=0,
        help="Seed for --generate (reused for corpus reproducibility)",
    )
    cal.add_argument(
        "--field-order",
        default="required_first",
        choices=["required_first", "unrestricted", "optional_first"],
        help="Field ordering for --generate; optional_first exercises "
        "optional-before-required ISRs the backend must (and now does) handle",
    )
    cal.add_argument("--out", default="calibration-out", help="Output root for per-backend bundles")
    cal.add_argument("--ledger", default="evidence/calibration.jsonl", help="Durable evidence ledger path")

    gen = sub.add_parser(
        "generate-corpus", help="Generate a stratified, technology-free SystemModel corpus (no calibration)"
    )
    gen.add_argument("--size", type=int, required=True, help="Number of SystemModels to generate")
    gen.add_argument("--seed", type=int, default=0, help="Deterministic seed (default: 0)")
    gen.add_argument(
        "--field-order",
        default="required_first",
        choices=["required_first", "unrestricted", "optional_first"],
        help="Field ordering strategy (default: required_first)",
    )
    gen.add_argument("--out", required=True, help="Output JSON path for the corpus")

    args = parser.parse_args(argv)

    if args.command == "run-calibration":
        harness, _settings = build_harness()
        manifest = StratifiedManifest.load(args.manifest)
        results = asyncio.run(harness.run(manifest, auth=None))
        passed = sum(1 for e in results if e.verdict.value == "pass")
        total = len(results)
        print(f"Calibration complete: {passed}/{total} projects passed exit gates.")
        return 0 if passed == total else 1

    if args.command == "verify-ledger":
        ledger = JsonlEvidenceLedger(args.ledger)
        ok = ledger.verify_chain()
        print(f"ledger integrity: {'OK' if ok else 'BROKEN'}")
        return 0 if ok else 1

    if args.command == "create":
        hints = {"system_id": args.system_id} if args.system_id else {}
        try:
            compiler = build_project_compiler(args.provider, transcript_path=args.transcript)
            report = compiler.compile_intent(args.statement, hints)
        except ProjectCompilationError as exc:
            print(f"error: compilation failed: {exc}")
            return 1
        sc_backend = LocalGitBackend() if shutil.which("git") else None
        if sc_backend is None:
            print("note: git not found on PATH; materializing artifact tree without VCS")
        materializer = RepositoryMaterializer(sc_backend)
        try:
            result = materializer.materialize(
                report,
                args.out,
                force=args.force,
                branch=args.branch,
            )
        except ProjectCompilationError as exc:
            print(f"error: {exc}")
            return 1
        commit_preview = (
            result.commit.commit_id[:12] if result.commit is not None else "none"
        )
        print(
            f"materialized {len(report.outcomes)} bundle(s) for '{args.statement}' "
            f"into {result.out_root} (manifest={result.manifest_path}, "
            f"commit={commit_preview})"
        )
        print(f"  isr hash: {report.isr_hash}")
        return 0 if report.ok else 1

    if args.command == "factory":
        compiler = build_project_compiler(args.provider, transcript_path=args.transcript)
        sc_backend = LocalGitBackend() if shutil.which("git") else None
        if sc_backend is None:
            print("note: git not found on PATH; materializing artifact tree without VCS")
        materializer = RepositoryMaterializer(sc_backend)
        from tiannara.application.materializer.materializer import MaterializationError

        ledger = JsonlEvidenceLedger(args.ledger)
        factory = SoftwareFactory(
            project_compiler=compiler,
            materializer=materializer,
            execution_environment=LocalExecutionEnvironment(),
            repair_provider=RematerializationRepairProvider(),
            verifier_factory=_default_verifier_factory,
            max_repair_attempts=args.max_repair_attempts,
            evidence_sink=make_factory_evidence_sink(ledger),
        )
        try:
            report = factory.run(args.statement, out_root=args.out, force=args.force)
        except ProjectCompilationError as exc:
            print(f"error: compilation failed: {exc}")
            return 1
        except SoftwareFactoryError as exc:
            print(f"error: factory failed: {exc}")
            return 1
        except MaterializationError as exc:
            print(f"error: {exc}")
            return 1
        fitness_metrics = getattr(getattr(report, "fitness", None), "metrics", None)
        print(
            f"factory: ok={report.ok} isr={report.isr_hash[:12]} "
            f"repair_attempts={sum(o.repair_attempts for o in report.verification_outcomes)} "
            f"fitness={fitness_metrics}"
        )
        chain_ok = ledger.verify_chain()
        print(
            f"evidence: wrote {len(ledger.all())} record(s) to {args.ledger} "
            f"(chain integrity: {'OK' if chain_ok else 'BROKEN'})"
        )
        return 0 if report.ok else 1

    if args.command == "calibrate":
        from tiannara.application.harness.calibration.corpus import (
            DEFAULT_CORPUS,
            dump_corpus,
            load_corpus,
        )
        from tiannara.application.harness.calibration.generator import (
            DEFAULT_GENERATED_CORPUS_SIZE,
            FieldOrder,
            SystemModelCorpusGenerator,
        )
        from tiannara.application.harness.calibration.harness import (
            BackendCalibrationHarness,
            build_calibration_registry,
        )

        if args.generate is not None:
            n = args.generate if args.generate > 0 else DEFAULT_GENERATED_CORPUS_SIZE
            corpus_models = SystemModelCorpusGenerator(
                seed=args.seed, size=n, field_order=FieldOrder(args.field_order)
            ).generate()
            if args.corpus:
                dump_corpus(corpus_models, args.corpus)
        else:
            corpus_models = (
                load_corpus(args.corpus) if args.corpus else list(DEFAULT_CORPUS)
            )
        harness = BackendCalibrationHarness(
            build_calibration_registry(), JsonlEvidenceLedger(args.ledger)
        )
        report = harness.calibrate(corpus=corpus_models, out_root=args.out)
        print(
            f"calibration: corpus={report.corpus_size} backends={report.backends_tested} "
            f"pass={report.passed}/{report.total} "
            f"success_rate={report.success_rate:.0%} "
            f"runtime_coverage={report.runtime_coverage:.0%}"
        )
        print(f"  seed={getattr(args, 'seed', 0)} generate={getattr(args, 'generate', None)}")
        print(f"  gate: {report.gate_semantics}")
        chain_ok = JsonlEvidenceLedger(args.ledger).verify_chain()
        print(
            f"  evidence: {len(JsonlEvidenceLedger(args.ledger).all())} record(s) "
            f"to {args.ledger} (chain integrity: {'OK' if chain_ok else 'BROKEN'})"
        )
        return 0 if report.success_rate == 1.0 else 1

    if args.command == "generate-corpus":
        from tiannara.application.harness.calibration.corpus import dump_corpus
        from tiannara.application.harness.calibration.generator import (
            FieldOrder,
            SystemModelCorpusGenerator,
        )

        models = SystemModelCorpusGenerator(
            seed=args.seed, size=args.size, field_order=FieldOrder(args.field_order)
        ).generate()
        dump_corpus(models, args.out)
        print(f"generated {len(models)} SystemModels -> {args.out}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
