import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/ios-workflow/scripts'))
from change_scope import select_checks
from progress_validation import validate_progress_scope
from tests import test_progress_validation as progress_fixture


class ChangeScopeTests(unittest.TestCase):
    def test_document_maintenance_does_not_pull_entire_project_history(self):
        result = select_checks(['README.md'])
        self.assertEqual(result['progress_scope'], 'none')
        self.assertEqual(result['checks'], ['references/checklists/core.md'])

    def test_stage_save_does_not_require_final_completion(self):
        result = select_checks(['App/View.swift'], operation='checkpoint', impacts=['ui'], requirement_ids=['R1'])
        self.assertFalse(result['completion_required'])
        self.assertEqual(result['requirements'], ['R1'])
        self.assertEqual(result['progress_scope'], 'selected')

    def test_semantic_impact_can_override_an_uninformative_filename(self):
        result = select_checks(['config.json'], impacts=['subscription', 'privacy'])
        self.assertIn('references/checklists/subscription.md', result['checks'])
        self.assertIn('references/checklists/technical-design.md', result['checks'])

    def test_dependency_and_generator_changes_select_related_checks(self):
        result = select_checks(['Package.resolved', 'scripts/project_generation.py'])
        self.assertIn('references/checklists/project-generation.md', result['checks'])
        self.assertIn('dependencies', result['impacts'])

    def test_health_is_explicit_and_bad_inputs_rejected(self):
        self.assertEqual(select_checks([], operation='health')['progress_scope'], 'all')
        for kwargs in ({'changed_paths': ['../secret']}, {'changed_paths': [], 'impacts': ['guess']}, {'changed_paths': [], 'operation': 'unknown'}):
            with self.assertRaises(ValueError):
                select_checks(**kwargs)


class ScopedProgressTests(unittest.TestCase):
    def setUp(self):
        self.fixture = progress_fixture.ProgressValidationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_unrelated_missing_historical_evidence_does_not_block_current_requirement(self):
        progress = copy.deepcopy(self.fixture.progress)
        old = copy.deepcopy(progress['items'][0])
        old['id'] = 'OLD-AC'
        old['requirement_id'] = 'OLD'
        old['evidence'][0]['path'] = '.ios-workflow/evidence/missing.txt'
        progress['items'].append(old)
        self.assertEqual([], validate_progress_scope(self.fixture.project, progress, requirement_ids=['REQ-001']))
        self.assertTrue(validate_progress_scope(self.fixture.project, progress, requirement_ids=['OLD']))

    def test_unknown_empty_scope_and_global_duplicate_are_not_silent(self):
        progress = self.fixture.progress
        self.assertTrue(validate_progress_scope(self.fixture.project, progress))
        self.assertTrue(validate_progress_scope(self.fixture.project, progress, requirement_ids=['missing']))
        progress['items'].append(copy.deepcopy(progress['items'][0]))
        self.assertTrue(validate_progress_scope(self.fixture.project, progress, item_ids=['REQ-001-AC-001']))
