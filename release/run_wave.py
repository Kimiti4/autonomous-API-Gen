"""Run Campaign B wave — invoked by run-campaign-b.sh or directly."""
import os
import sys

from certification.campaign.campaign_b import run_wave
from certification.campaign.waves import WAVES


def main():
    wave_id = os.environ.get("CBC1_WAVE", "B1")
    scale_str = os.environ.get("CBC1_SCALE", "")
    scale = int(scale_str) if scale_str else None

    wave = WAVES.get(wave_id)
    if not wave:
        print(f"Unknown wave: {wave_id}", file=sys.stderr)
        sys.exit(1)

    print(f"Wave {wave_id}: {wave.purpose}")
    print(f"Required mode: {wave.required_mode.value}")
    print()

    resume = os.environ.get("CBC1_RESUME", "") == "1"
    supplement = os.environ.get("CBC1_SUPPLEMENT", "") == "1"
    if resume:
        print("Resume mode: continuing prior ledger on the same verified hash chain")
    if supplement:
        print("Supplement mode: re-measuring failed seed trials as new trials")

    verdict, summary = run_wave(
        wave_id, scale_override=scale, resume=resume, supplement=supplement,
    )
    print(f"Verdict: {verdict}")
    print(f"Reason:  {summary.get('verdict_reason', '')}")
    print(f"Expected:  {summary.get('expected_trials', 0)}")
    print(f"Planned:   {summary.get('planned_trials', 0)}   "
          f"Resumed: {summary.get('resumed_trials', 0)}   "
          f"Supplements: {summary.get('supplement_trials', 0)}")
    print(f"Executed:  {summary.get('executed_trials', 0)}   "
          f"Certified: {summary.get('certified_trials', 0)}   "
          f"Failed: {summary.get('failed_trials', 0)}   "
          f"Skipped: {summary.get('skipped_trials', 0)}")

    if summary.get("port_preflight", {}).get("enabled"):
        pf = summary["port_preflight"]
        print(f"Port preflight: {'OK' if pf.get('ok') else 'FAILED'} "
              f"window={pf.get('window')} evidence={pf.get('evidence_path')}")

    if summary.get("failure_taxonomy_independent"):
        print()
        print("Failure taxonomy (independent):")
        for stage, count in summary["failure_taxonomy_independent"].items():
            print(f"  {stage}: {count}")

    print()
    print(f"Aggregate: release/evidence/cbc1-b-{wave_id}-aggregate.json")

    exit_codes = {"CERTIFIED": 0, "NOT_CERTIFIED": 1, "QUALIFIED_PARTIAL": 3}
    sys.exit(exit_codes.get(verdict, 1))


if __name__ == "__main__":
    main()
