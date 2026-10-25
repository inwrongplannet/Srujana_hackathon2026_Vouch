"""Unit tests for the docs gates (run by `make test`)."""
import unittest

import check_docs
import check_docs_style as style


def run(changes, text=""):
    return check_docs.evaluate(changes, text)


class DocsSyncTests(unittest.TestCase):
    def test_backend_code_without_docs_fails(self):
        self.assertTrue(run([("M", "backend/app/main.py")]))

    def test_backend_code_with_zone_readme_passes(self):
        self.assertEqual(run([("M", "backend/app/main.py"), ("M", "backend/README.md")]), [])

    def test_feature_manifest_satisfies_frontend(self):
        self.assertEqual(run([("M", "frontend/src/App.tsx"), ("M", "docs/frontend-features/portfolio.md")]), [])

    def test_tests_and_lockfiles_need_no_docs(self):
        self.assertEqual(run([("M", "backend/tests/test_api.py"), ("M", "frontend/pnpm-lock.yaml")]), [])

    def test_waiver_needs_a_real_reason(self):
        change = [("M", "backend/app/main.py")]
        self.assertEqual(run(change, "fix typo\n\nDocs-Impact: none (comment-only change)"), [])
        self.assertTrue(run(change, "Docs-Impact: none (<reason>)"))
        self.assertTrue(run(change, "Docs-Impact: none (x)"))

    def test_spike_needs_its_own_readme(self):
        self.assertTrue(run([("A", "spikes/fx-rates/fetch.py")]))
        self.assertEqual(run([("A", "spikes/fx-rates/fetch.py"), ("A", "spikes/fx-rates/README.md")]), [])

    def test_dependency_manifest_needs_decision(self):
        changes = [("M", "frontend/package.json"), ("M", "frontend/README.md")]
        self.assertTrue(run(changes))
        self.assertEqual(run(changes + [("M", "docs/DECISIONS.md")]), [])

    def test_convention_surface_needs_agents_md(self):
        self.assertTrue(run([("M", "Makefile")]))
        self.assertEqual(run([("M", "Makefile"), ("M", "AGENTS.md")]), [])
        self.assertEqual(run([("M", "Makefile")], "Agents-Impact: none (recipe typo fix)"), [])

    def test_editing_a_skill_body_is_not_surface_but_adding_one_is(self):
        self.assertEqual(run([("M", ".claude/skills/spike/SKILL.md")]), [])
        self.assertTrue(run([("A", ".claude/skills/new-skill/SKILL.md")]))


class StyleTests(unittest.TestCase):
    def test_fence_without_language_flagged(self):
        self.assertTrue(style.parse("# T\n\n```\ncode\n```\n")["errors"])

    def test_fence_with_language_ok(self):
        self.assertFalse(style.parse("# T\n\n```bash\nmake check\n```\n")["errors"])

    def test_headings_ignore_code_and_comments(self):
        doc = style.parse("<!-- c -->\n# T\n```bash\n# not a heading\n```\n## A\n")
        self.assertEqual([h[1] for h in doc["headings"]], [1, 2])

    def test_naming(self):
        self.assertIsNone(style.naming_error("docs/API_CONTRACT.md"))
        self.assertIsNotNone(style.naming_error("docs/api-contract.md"))
        self.assertIsNone(style.naming_error("docs/frontend-features/portfolio-view.md"))
        self.assertIsNotNone(style.naming_error("docs/frontend-features/PortfolioView.md"))


if __name__ == "__main__":
    unittest.main()
