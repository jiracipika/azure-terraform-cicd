"""Repository scaffold safety gates.

Regex assertions only (exact-string matches break on terraform fmt
realignment — that is how the first CI run of this repo went red).
"""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ScaffoldTests(unittest.TestCase):
    def test_docs(self):
        for rel in ("AGENTS.md", "docs/GLM_TASKS.md", "docs/ARCHITECTURE.md",
                    "docs/SECURITY.md", "docs/COSTS.md", "docs/TEARDOWN.md",
                    "docs/VALIDATION.md"):
            self.assertTrue((ROOT / rel).is_file(), f"missing {rel}")

    def test_cloud_disabled_by_default(self):
        variables = (ROOT / "infra" / "terraform" / "variables.tf").read_text()
        self.assertRegex(variables, r'"deploy_enabled"\s*\{[^}]*default\s*=\s*false')

    def test_active_workflows_never_apply(self):
        for path in (ROOT / ".github" / "workflows").glob("*.y*ml"):
            self.assertNotIn("terraform apply", path.read_text(),
                             f"{path.name} contains terraform apply")

    def test_diagram_matches_promotion_model(self):
        diagram = (ROOT / "diagrams" / "architecture.mmd").read_text()
        self.assertIn("flowchart", diagram)
        for env in ("dev", "stage", "prod"):
            self.assertIn(env, diagram, f"diagram missing promotion environment {env}")
        self.assertIn("state", diagram.lower())

    def test_yaml_files_are_valid_yaml(self):
        import yaml
        for pattern in (".github/workflows/*.yml", ".github/workflows/*.yaml",
                        "examples/pipelines/*.yml", "examples/pipelines/*.yaml",
                        "infra/pipeline/*.yaml", "infra/pipeline/*.yml"):
            for path in sorted(ROOT.glob(pattern)):
                yaml.safe_load(path.read_text())

    def test_gitignore_keeps_environment_tfvars_and_blocks_state_and_mimosa(self):
        gi = (ROOT / ".gitignore").read_text()
        self.assertIsNotNone(re.search(r"^\*\.tfvars$", gi, re.M),
                             "tfvars must be ignored by default")
        self.assertIn("!**/environments/*.tfvars", gi,
                      "per-environment tfvars must be force-included")
        self.assertIn("*.tfstate", gi)
        self.assertIn("*.tfplan", gi)
        self.assertIn(".mimosa/", gi)
        self.assertNotIn("\n.terraform.lock.hcl", gi,
                         "provider lock file must stay committed (pinning)")

    def test_no_state_or_plans_committed(self):
        for pattern in ("**/*.tfstate", "**/*.tfstate.*", "**/*.tfplan", ".mimosa/**"):
            self.assertEqual(list(ROOT.glob(pattern)), [],
                             f"forbidden tracked artifact matching {pattern}")

    def test_lock_file_committed(self):
        lock = ROOT / "infra" / "terraform" / ".terraform.lock.hcl"
        self.assertTrue(lock.is_file(), "provider lock file must be committed")
        self.assertIn("hashicorp/azurerm", lock.read_text())

    def test_readme_documents_offline_commands(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("unittest discover", readme)
        self.assertIn("init -backend=false", readme)


if __name__ == "__main__":
    unittest.main()
