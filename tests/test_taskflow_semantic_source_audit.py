from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments' / 'taskflow-native'))

from provider_free.semantic_source_audit import build_source_audit  # noqa: E402


def test_audit_covers_all_fields_without_resolving_or_authorizing_generation():
    report = build_source_audit()
    assert report['summary']['mandatory_fields'] == 15
    assert report['summary']['resolved_fields'] == 0
    assert report['generation_authorized'] is False
    assert report['certification_authorized'] is False
    assert all(item['source_fragments_present'] for item in report['entries'])
    assert all(item['resolved'] is False for item in report['entries'])


def test_audit_exposes_underspecified_contracts():
    report = build_source_audit()
    fields = {item['field_path']: item for item in report['entries']}
    assert fields['authorization.owner_manager_member_permissions']['coverage'] == 'PARTIAL'
    assert fields['api.request_response_and_error_contracts']['coverage'] == 'NOT_SPECIFIED'
    assert fields['deployment.reproducible_execution_environment']['coverage'] == 'NOT_SPECIFIED'
