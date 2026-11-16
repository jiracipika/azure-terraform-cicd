import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class SafetyTests(unittest.TestCase):
    def test_docs(self):
        self.assertTrue((R/"AGENTS.md").is_file())
        self.assertTrue((R/"docs/GLM_TASKS.md").is_file())
    def test_cloud_disabled(self):
        self.assertIn("default = false",(R/"infra/terraform/variables.tf").read_text())
        self.assertNotIn("terraform apply",(R/".github/workflows/validate.yml").read_text())
    def test_diagram(self):
        self.assertIn("flowchart",(R/"diagrams/architecture.mmd").read_text())
