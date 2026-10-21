"""Deletion boundary regressions use an in-memory fake GitHub API."""
import unittest
from scripts.governance.guarded_branch_cleanup import cleanup, eligible, active_pr_branches, load_superseded

REPO = 'owner/repo'


class GuardedCleanupTests(unittest.TestCase):
    def test_only_unprotected_strict_ancestor_without_active_pr_is_eligible(self):
        branch = {'name': 'old', 'protected': False}
        comparison = {'ahead_by': 0, 'behind_by': 2, 'status': 'behind'}
        self.assertTrue(eligible(branch, comparison, set()))
        self.assertFalse(eligible(branch, comparison, {'old'}))
        self.assertFalse(eligible({**branch, 'protected': True}, comparison, set()))
        self.assertFalse(eligible(branch, {**comparison, 'ahead_by': 1}, set()))
        self.assertFalse(eligible(branch, {'ahead_by': 0, 'behind_by': 0, 'status': 'identical'}, set()))
        self.assertFalse(eligible({'name': 'main', 'protected': False}, comparison, set()))

    def test_both_head_and_base_of_active_pr_are_protected(self):
        pr = {s: {'ref': s, 'repo': {'full_name': REPO}} for s in ('head', 'base')}
        self.assertEqual(active_pr_branches(lambda _: [pr], REPO), {'head', 'base'})

    def run_fake(self, *, execute=True, moved=False, new_pr=False):
        deleted = []
        calls = {'prs': 0}
        branch = {'name': 'old', 'protected': False, 'commit': {'sha': 'a'}}
        def api(path, method='GET'):
            if method == 'DELETE':
                deleted.append(path)
                return 204
            if path.startswith('/pulls?'):
                calls['prs'] += 1
                if new_pr and calls['prs'] > 1:
                    return [{'head': {'ref': 'old', 'repo': {'full_name': REPO}}}]
                return []
            if path.startswith('/branches?'):
                return [branch]
            if path.startswith('/branches/'):
                return {**branch, 'commit': {'sha': 'b' if moved else 'a'}}
            if path.startswith('/compare/'):
                return {'ahead_by': 0, 'behind_by': 2, 'status': 'behind'}
            raise AssertionError(path)
        result = cleanup(api, REPO, execute=execute)
        return result, deleted

    def test_dry_run_never_deletes(self):
        report, deleted = self.run_fake(execute=False)
        self.assertEqual(report['candidates'], ['old'])
        self.assertEqual(deleted, [])

    def test_sha_movement_blocks_delete(self):
        self.assertEqual(self.run_fake(moved=True)[1], [])

    def test_pr_opened_during_run_blocks_delete(self):
        self.assertEqual(self.run_fake(new_pr=True)[1], [])

    def test_verified_ancestor_is_deleted(self):
        report, deleted = self.run_fake()
        self.assertEqual(report['deleted'], ['old'])
        self.assertEqual(deleted, ['/git/refs/heads/old'])


class SupersededRegistryTests(unittest.TestCase):
    SHA = 'a' * 40

    def branch(self, sha=None, protected=False, name='old'):
        return {'name': name, 'protected': protected, 'commit': {'sha': sha or self.SHA}}

    def test_registered_branch_with_exact_sha_is_eligible_even_if_ahead(self):
        diverged = {'ahead_by': 3, 'behind_by': 9, 'status': 'diverged'}
        self.assertTrue(eligible(self.branch(), diverged, set(), {'old': self.SHA}))

    def test_registry_never_overrides_other_guards(self):
        diverged = {'ahead_by': 3, 'behind_by': 9, 'status': 'diverged'}
        reg = {'old': self.SHA, 'main': self.SHA}
        self.assertFalse(eligible(self.branch(sha='b' * 40), diverged, set(), reg))
        self.assertFalse(eligible(self.branch(protected=True), diverged, set(), reg))
        self.assertFalse(eligible(self.branch(), diverged, {'old'}, reg))
        self.assertFalse(eligible(self.branch(name='main'), diverged, set(), reg))
        self.assertFalse(eligible(self.branch(), diverged, set(), {}))

    def test_registry_rejects_malformed_entries(self):
        import json, os, tempfile
        for rows in ([{'name': 'x', 'sha': 'abc'}], [{'name': 'main', 'sha': self.SHA}],
                     [{'name': 'x', 'sha': 'G' * 40}]):
            with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
                json.dump({'branches': rows}, f)
            try:
                with self.assertRaises(ValueError):
                    load_superseded(f.name)
            finally:
                os.unlink(f.name)
        self.assertEqual(load_superseded('/nonexistent/registry.json'), {})

    def test_committed_registry_is_valid(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[3]
        reg = load_superseded(str(root / 'docs/maintenance/superseded-branches.json'))
        self.assertNotIn('main', reg)
        self.assertNotIn('claude-vps-bridge', reg)
