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

    verdict, summary = run_wave(wave_id, scale_override=scale)
    print(f"Verdict: {verdict}")
    print(f"Reason:  {summary.get('verdict_reason', '')}")
    print(f"Trials:  {summary.get('total_trials', 0)}")
    print(f"Certified: {summary.get('certified', 0)}/{summary.get('total_trials', 0)}")

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
