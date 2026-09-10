import copy
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/ios-workflow/scripts'))
from change_scope import assess_gate, select_checks
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

    def test_entitlement_change_also_loads_release_checks(self):
        result = select_checks(['App/Puzzle.entitlements'], release_target='ios_app')
        self.assertIn('references/checklists/release-distribution.md', result['checks'])
        self.assertIn('privacy', result['impacts'])
        self.assertIn('release', result['impacts'])
        self.assertFalse(result['completion_required'])

    def test_health_is_explicit_and_bad_inputs_rejected(self):
        self.assertEqual(select_checks([], operation='health')['progress_scope'], 'all')
        for kwargs in ({'changed_paths': ['../secret']}, {'changed_paths': [], 'impacts': ['guess']}, {'changed_paths': [], 'operation': 'unknown'}):
            with self.assertRaises(ValueError):
                select_checks(**kwargs)


class CheckpointGateTests(unittest.TestCase):
    def setUp(self):
        self.integrity = dict.fromkeys(('scope', 'privacy', 'user_files', 'records'), 'passed')

    def assess(self, **kwargs):
        if kwargs.get('operation') == 'release':
            kwargs.setdefault('release_target', 'ios_app')
        return assess_gate(['App/Feature.swift'], integrity=self.integrity, **kwargs)

    def test_actual_failed_check_can_be_saved_without_becoming_successful(self):
        execution = subprocess.run([sys.executable, '-c', 'raise SystemExit(1)'],
                                   capture_output=True, text=True, timeout=10)
        self.assertEqual(1, execution.returncode)
        result = self.assess(operation='checkpoint',
                             validation_result='passed' if execution.returncode == 0 else 'failed')
        self.assertTrue(result['gate_passed'])
        self.assertEqual('failed', result['validation_result'])
        self.assertFalse(result['validation_passed'])
        self.assertEqual('unknown', result['completion_result'])
        self.assertFalse(result['completion_required'])

    def test_unexecuted_or_blocked_validation_can_be_saved_with_its_original_status(self):
        for status in ('unknown', 'blocked', 'skipped'):
            with self.subTest(status=status):
                result = self.assess(operation='checkpoint', validation_result=status)
                self.assertTrue(result['gate_passed'])
                self.assertEqual(status, result['validation_result'])
                self.assertFalse(result['validation_passed'])

    def test_actual_or_unknown_integrity_problems_block_even_checkpoint(self):
        for check in self.integrity:
            for status in ('failed', 'unknown'):
                with self.subTest(check=check, status=status):
                    checks = dict(self.integrity, **{check: status})
                    result = assess_gate(['App/Feature.swift'], operation='checkpoint',
                                          integrity=checks, validation_result='failed')
                    self.assertFalse(result['gate_passed'])
                    self.assertEqual([f'integrity.{check}:{status}'], result['blocking_reasons'])
                    self.assertEqual(checks, result['integrity'])

    def test_normal_delivery_keeps_relevant_success_requirements(self):
        for operation in ('commit', 'push', 'review', 'release'):
            for status in ('failed', 'unknown', 'blocked', 'skipped', 'not_required'):
                with self.subTest(operation=operation, status=status):
                    self.assertFalse(self.assess(operation=operation, validation_result=status)['gate_passed'])
        self.assertTrue(self.assess(operation='commit', validation_result='passed')['gate_passed'])

    def test_release_requires_completion_and_checkpoint_cannot_claim_unverified_completion(self):
        self.assertFalse(self.assess(operation='release', validation_result='passed')['gate_passed'])
        self.assertTrue(self.assess(operation='release', validation_result='passed',
                                    completion_result='passed')['gate_passed'])
        self.assertFalse(self.assess(operation='checkpoint', validation_result='failed',
                                     completion_result='passed')['gate_passed'])

    def test_document_only_commit_does_not_fabricate_test_success(self):
        result = assess_gate(['README.md'], integrity=self.integrity, validation_result='not_required')
        self.assertTrue(result['gate_passed'])
        self.assertFalse(result['validation_required'])
        self.assertFalse(result['validation_passed'])
        self.assertEqual('not_required', result['validation_result'])

    def test_assessment_does_not_mutate_inputs_and_rejects_ambiguous_facts(self):
        before = copy.deepcopy(self.integrity)
        result = self.assess(operation='checkpoint', validation_result='failed')
        result['integrity']['records'] = 'unknown'
        self.assertEqual(before, self.integrity)
        for kwargs in ({'integrity': {}}, {'integrity': dict(before, privacy=True)},
                       {'validation_result': True}, {'validation_result': 'maybe'},
                       {'completion_result': []}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                assess_gate(['App/Feature.swift'], **{'integrity': before, **kwargs})


class ReleaseTargetTests(unittest.TestCase):
    def setUp(self):
        self.integrity = dict.fromkeys(('scope', 'privacy', 'user_files', 'records'), 'passed')

    def test_release_target_is_explicit_and_cannot_be_inferred_from_changelog(self):
        for target in (None, 'guess', [], True):
            with self.subTest(target=target), self.assertRaises(ValueError):
                select_checks(['CHANGELOG.md'], operation='release', release_target=target)
        for paths, impacts in ((['App/Puzzle.entitlements'], ()), (['pipeline.yml'], ['release'])):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                select_checks(paths, impacts=impacts)
        self.assertIsNone(select_checks(['CHANGELOG.md'])['release_target'])

    def test_workflow_release_uses_package_checks_without_app_acceptance(self):
        result = select_checks(['CHANGELOG.md'], operation='release', release_target='workflow',
                               requirement_ids=['workflow-task'])
        self.assertEqual(['references/checklists/core.md', 'references/checklists/workflow-release.md'], result['checks'])
        self.assertFalse(result['completion_required'])
        self.assertEqual('none', result['progress_scope'])
        self.assertTrue(result['release_result_required'])
        self.assertTrue(result['validation_required'])
        self.assertEqual(['workflow-task'], result['requirements'])

    def test_app_release_keeps_app_checks_even_for_the_same_changelog_path(self):
        result = select_checks(['CHANGELOG.md'], operation='release', release_target='ios_app',
                               requirement_ids=['APP-REQ'])
        self.assertIn('references/checklists/release-distribution.md', result['checks'])
        self.assertIn('references/checklists/testing.md', result['checks'])
        self.assertIn('references/checklists/requirement-traceability.md', result['checks'])
        self.assertNotIn('references/checklists/workflow-release.md', result['checks'])
        self.assertTrue(result['completion_required'])
        self.assertFalse(result['release_result_required'])
        self.assertEqual('selected', result['progress_scope'])

    def test_workflow_generator_changes_keep_generation_checks(self):
        result = select_checks(['.agents/skills/ios-workflow/scripts/project_generation.py'],
                               operation='release', release_target='workflow')
        self.assertIn('references/checklists/project-generation.md', result['checks'])
        self.assertIn('references/checklists/workflow-release.md', result['checks'])
        self.assertNotIn('references/checklists/testing.md', result['checks'])

    def test_workflow_gate_requires_validation_and_package_readiness_not_business_completion(self):
        arguments = {'integrity': self.integrity, 'operation': 'release', 'release_target': 'workflow'}
        ready = assess_gate(['CHANGELOG.md'], **arguments, validation_result='passed', release_result='passed')
        self.assertTrue(ready['gate_passed'])
        self.assertEqual('unknown', ready['completion_result'])
        for status in ('failed', 'unknown'):
            with self.subTest(status=status):
                self.assertFalse(assess_gate(['CHANGELOG.md'], **arguments, validation_result='passed',
                                             release_result=status)['gate_passed'])
                self.assertFalse(assess_gate(['CHANGELOG.md'], **arguments, validation_result=status,
                                             release_result='passed')['gate_passed'])

    def test_package_readiness_cannot_replace_app_acceptance(self):
        result = assess_gate(['CHANGELOG.md'], integrity=self.integrity, operation='release',
                             release_target='ios_app', validation_result='passed', release_result='passed')
        self.assertFalse(result['gate_passed'])
        self.assertIn('completion:unknown', result['blocking_reasons'])

    def test_workflow_automation_commit_does_not_require_a_future_published_tag(self):
        result = assess_gate(['.github/workflows/release.yml'], integrity=self.integrity,
                             impacts=['release'], release_target='workflow', validation_result='passed')
        self.assertTrue(result['gate_passed'])
        self.assertFalse(result['release_result_required'])
        self.assertEqual('unknown', result['release_result'])


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
