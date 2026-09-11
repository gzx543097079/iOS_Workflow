import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/ios-workflow/scripts'))
from requirement_gate import assess_requirement_gate
from tests import test_tracking_update as fixtures


class RequirementGateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TrackingUpdateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.project
        self.card = {'goal': 'Storefront', 'scope': ['Search'], 'acceptance': ['Missing query shows empty state'],
                     'exclusions': ['Payment'], 'assumptions': ['Local sample products']}

    def gate(self, **overrides):
        values = dict(task_kind='feature', phase='start', card=self.card, requirement_id='REQ-001')
        values.update(overrides)
        return assess_requirement_gate(self.root, **values)

    def test_feature_cannot_use_maintenance_exemption(self):
        result = self.gate(requirement_id=None, low_risk=True, single_turn=True, acceptance_clear=True)
        self.assertTrue(result['tracking_required'])
        self.assertFalse(result['gate_passed'])

    def test_small_bug_still_requires_tracking(self):
        self.assertFalse(self.gate(task_kind='bug', requirement_id=None, low_risk=True,
                                   single_turn=True, acceptance_clear=True)['gate_passed'])

    def test_pure_maintenance_can_be_exempt_but_still_needs_card(self):
        args = dict(task_kind='maintenance', requirement_id=None, low_risk=True,
                    single_turn=True, acceptance_clear=True)
        self.assertTrue(self.gate(**args)['gate_passed'])
        self.assertFalse(self.gate(card={}, **args)['gate_passed'])

    def test_prior_continuity_or_related_records_prevent_exemption(self):
        for flag in ('continuity_required', 'related_requirement'):
            with self.subTest(flag=flag):
                result = self.gate(task_kind='maintenance', requirement_id=None, low_risk=True,
                                   single_turn=True, acceptance_clear=True, **{flag: True})
                self.assertFalse(result['gate_passed'])
                self.assertTrue(result['tracking_required'])

    def test_invalid_or_unknown_classification_is_not_permission(self):
        for values in ({'task_kind': None}, {'phase': 'unknown'}, {'single_turn': 'true'}, {'card': None}):
            with self.subTest(values=values):
                self.assertFalse(self.gate(**values)['gate_passed'])

    def test_complete_card_requires_nonempty_acceptance(self):
        card = copy.deepcopy(self.card)
        card['acceptance'] = []
        self.assertFalse(self.gate(card=card)['gate_passed'])

    def test_missing_ledger_blocks_start_even_when_test_report_exists(self):
        (self.root / '.ios-workflow/progress.json').unlink()
        self.assertFalse(self.gate()['gate_passed'])

    def test_start_checks_real_linkage_without_writing(self):
        before = self.fixture.targets()
        self.assertTrue(self.gate()['gate_passed'])
        self.assertEqual(before, self.fixture.targets())
        p = self.root / self.fixture.archive
        p.write_text(p.read_text().replace('sequence: 1', 'sequence: 2'))
        self.assertFalse(self.gate()['gate_passed'])

    def test_checkpoint_preserves_failed_implemented_item(self):
        progress = copy.deepcopy(self.fixture.progress)
        progress['items'][0]['status'] = 'implemented'
        progress['items'][0]['evidence'][0]['result'] = 'failed'
        (self.root / '.ios-workflow/progress.json').write_text(json.dumps(progress))
        self.assertTrue(self.gate(phase='checkpoint')['gate_passed'])
        self.assertFalse(self.gate(phase='complete')['gate_passed'])

    def test_completion_requires_terminal_state_and_current_evidence(self):
        self.assertFalse(self.gate(phase='complete')['gate_passed'])
        index = {'version': 3, 'active_requirement': None, 'last_requirement_id': 'REQ-001'}
        (self.root / '.ios-workflow/index.jsonc').write_text(json.dumps(index))
        history = copy.deepcopy(self.fixture.history)
        history['execution_order'][0]['status'] = 'done'
        (self.root / '.ios-workflow/history.jsonc').write_text(json.dumps(history))
        archive = self.root / self.fixture.archive
        archive.write_text(archive.read_text().replace('status: in_progress', 'status: done'))
        self.assertTrue(self.gate(phase='complete')['gate_passed'])
        self.assertFalse(self.gate(phase='start')['gate_passed'])
        (self.root / 'App/MemoryGrid.swift').write_text('changed')
        self.assertFalse(self.gate(phase='complete')['gate_passed'])
