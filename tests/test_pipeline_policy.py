"""Pipeline-policy tests: the deterministic offline demo.

Every scenario replays the promotion policy in infra/pipeline/policy.yaml
against the real workflows/templates via tests/pipeline_policy.py:

- behavior: what runs for PR / push-to-main / manual dispatch;
- failure paths: unknown environments, skip-level promotion, ungated apply;
- CI safety: ACTIVE workflows may never mutate terraform state or Azure.
"""

from pathlib import Path
import re
import unittest

import pipeline_policy as pp

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "infra" / "terraform"


class PolicyDataSanity(unittest.TestCase):
    """The simulator must see exactly the committed promotion policy."""

    def test_promotion_path_is_dev_stage_prod(self):
        self.assertEqual(pp.ordered_environments(), ["dev", "stage", "prod"])

    def test_no_environment_auto_applies(self):
        for name, env in pp.environments().items():
            self.assertEqual(env["apply_mode"], "manual",
                             f"{name} drifted to automatic apply")

    def test_policy_environment_names_match_terraform(self):
        src = (TF / "variables.tf").read_text()
        m = re.search(r'variable "environment_names" \{.*?default\s*=\s*\[(.*?)\]', src, re.S)
        declared = re.findall(r'"(\w+)"', m.group(1))
        self.assertEqual(sorted(declared), sorted(pp.ordered_environments()))

    def test_every_environment_has_tfvars_and_backend_template(self):
        for env in pp.ordered_environments():
            self.assertTrue((TF / "environments" / f"{env}.tfvars").is_file(),
                            f"missing environments/{env}.tfvars")
            backend = ROOT / "examples" / "backend" / f"{env}.backend.hcl"
            self.assertTrue(backend.is_file(), f"missing examples/backend/{env}.backend.hcl")
            self.assertIn(f'tfstate-{env}"', backend.read_text())


class ActiveWorkflowSafety(unittest.TestCase):
    """No ACTIVE workflow may ever mutate infrastructure or state."""

    def test_no_forbidden_terraform_or_azure_commands(self):
        self.assertEqual(pp.active_workflow_violations(), [])

    def test_raw_scan_of_workflow_directory(self):
        """Regex sweep of raw bytes — catches what a parser might miss."""
        for path in (ROOT / ".github" / "workflows").glob("*.y*ml"):
            raw = path.read_text()
            self.assertIsNone(
                re.search(r"terraform\s+(apply|destroy|import|taint|untaint|workspace)\b", raw),
                f"{path.name} contains a mutating terraform subcommand",
            )
            self.assertIsNone(
                re.search(r"terraform\s+state\s+\w+", raw),
                f"{path.name} contains a terraform state subcommand",
            )
            self.assertIsNone(re.search(r"armdeploy", raw, re.I),
                              f"{path.name} contains an ARM deployment")
            self.assertNotIn("secrets.", raw,
                             "active workflows must not reference any secrets")

    def test_workflows_declare_minimal_permissions(self):
        for path, doc in pp.iter_yaml(ROOT / ".github" / "workflows"):
            self.assertEqual(doc.get("permissions"), {"contents": "read"},
                             f"{path.name} permissions drifted from contents: read")


class TemplateSafety(unittest.TestCase):
    """The inert pipeline templates must implement the policy they document."""

    def test_no_template_violations(self):
        self.assertEqual(pp.template_violations(), [])

    def test_apply_jobs_are_environment_gated_and_ordered(self):
        jobs = pp.apply_jobs(ROOT / "examples" / "pipelines" / "apply-promotion.yml")
        self.assertEqual(sorted(jobs), ["apply-dev", "apply-prod", "apply-stage"])
        self.assertEqual(jobs["apply-dev"]["environment"], "dev")
        self.assertEqual(jobs["apply-stage"]["environment"], "stage")
        self.assertEqual(jobs["apply-prod"]["environment"], "prod")
        self.assertEqual(jobs["apply-stage"]["needs"], "apply-dev")
        self.assertEqual(jobs["apply-prod"]["needs"], "apply-stage")

    def test_pr_template_has_no_apply(self):
        jobs = pp.apply_jobs(ROOT / "examples" / "pipelines" / "pr-plan.yml")
        self.assertEqual(jobs, {})

    def test_drift_template_is_read_only(self):
        raw = (ROOT / "examples" / "pipelines" / "drift-detection.yml").read_text()
        self.assertIn("-detailed-exitcode", raw)
        self.assertIsNone(re.search(r"terraform\s+(apply|destroy)\b", raw),
                          "drift detection must never apply")

    def test_templates_only_reference_secret_names(self):
        """Secrets may be referenced by name; literal values are forbidden."""
        for path in (ROOT / "examples" / "pipelines").glob("*.yml"):
            raw = path.read_text()
            self.assertIsNone(
                re.search(r"(?i)(password|client_secret|access_key)\s*[:=]\s*['\"][^$<{][^\s'\"]{8,}", raw),
                f"{path.name} contains a hardcoded secret-like value",
            )

    def test_templates_live_outside_workflow_directory(self):
        """Inert-by-location: no pipeline template may sit under .github/workflows."""
        for path in (ROOT / "examples" / "pipelines").glob("*.yml"):
            self.assertTrue(".github" not in path.parts,
                            f"{path} must stay under examples/")


class PullRequestScenarios(unittest.TestCase):
    """Given a PR changing module X, expected checks run — and no apply."""

    def test_pr_changing_state_backend_module(self):
        r = pp.simulate_event(
            "pull_request",
            changed_paths=["infra/terraform/modules/state_backend/main.tf"],
        )
        self.assertIn("terraform fmt -check", r["checks"])
        self.assertIn("terraform validate", r["checks"])
        self.assertIn("unittest", r["checks"])
        self.assertEqual(r["plans"], ["dev"])
        self.assertFalse(r["apply"]["permitted"])

    def test_pr_changing_identity_module_plans_dev_only(self):
        r = pp.simulate_event(
            "pull_request",
            changed_paths=["infra/terraform/modules/pipeline_identity/main.tf"],
        )
        self.assertEqual(r["plans"], ["dev"])
        self.assertFalse(r["apply"]["permitted"])

    def test_pr_changing_docs_still_never_applies(self):
        r = pp.simulate_event("pull_request", changed_paths=["README.md"])
        self.assertFalse(r["apply"]["permitted"])
        self.assertIn("apply_mode=manual", r["apply"]["reason"])


class PushMainScenarios(unittest.TestCase):
    """Given a push to main, no automatic apply ever happens."""

    def test_push_main_plans_configured_environments(self):
        r = pp.simulate_event("push_main")
        self.assertEqual(r["plans"], ["stage", "prod"])

    def test_push_main_never_applies(self):
        r = pp.simulate_event("push_main")
        self.assertFalse(r["apply"]["permitted"])
        self.assertIn("no auto-apply", r["apply"]["reason"])

    def test_push_main_runs_offline_checks(self):
        r = pp.simulate_event("push_main")
        for check in ("unittest", "terraform fmt -check", "terraform validate"):
            self.assertIn(check, r["checks"])


class DispatchScenarios(unittest.TestCase):
    """Manual dispatch of the inert apply template, with and without gates."""

    def test_dispatch_prod_expands_to_full_path(self):
        r = pp.simulate_event("workflow_dispatch", target_environment="prod")
        self.assertTrue(r["apply"]["permitted"])
        self.assertEqual(r["apply"]["path"], ["dev", "stage", "prod"])
        self.assertTrue(r["apply"]["approval_required"])

    def test_dispatch_dev_stays_at_dev(self):
        r = pp.simulate_event("workflow_dispatch", target_environment="dev")
        self.assertEqual(r["apply"]["path"], ["dev"])

    def test_dispatch_unknown_environment_refused(self):
        r = pp.simulate_event("workflow_dispatch", target_environment="canary")
        self.assertFalse(r["apply"]["permitted"])

    def test_ungated_apply_template_refused(self):
        """Negative test: removing environment gates must block apply."""
        r = pp.simulate_event("workflow_dispatch", target_environment="prod",
                              template_gates_present=False)
        self.assertFalse(r["apply"]["permitted"])
        self.assertIn("gates", r["apply"]["reason"])

    def test_apply_template_gates_really_exist(self):
        """The negative scenario must be load-bearing: gates are present now."""
        for meta in pp.apply_jobs(ROOT / "examples" / "pipelines" / "apply-promotion.yml").values():
            self.assertTrue(meta["environment"],
                            "apply job lost its environment gate")


class PromotionOrdering(unittest.TestCase):
    """Strict sequential promotion; skips and regressions refused."""

    def test_valid_full_promotion(self):
        ok, reason = pp.validate_promotion_sequence(["dev", "stage", "prod"])
        self.assertTrue(ok, reason)

    def test_dev_only_is_valid(self):
        ok, _ = pp.validate_promotion_sequence(["dev"])
        self.assertTrue(ok)

    def test_skip_level_refused(self):
        ok, reason = pp.validate_promotion_sequence(["dev", "prod"])
        self.assertFalse(ok)
        self.assertIn("skip-level", reason)

    def test_direct_prod_refused(self):
        ok, reason = pp.validate_promotion_sequence(["prod"])
        self.assertFalse(ok)

    def test_backwards_refused(self):
        ok, reason = pp.validate_promotion_sequence(["dev", "stage", "dev"])
        self.assertFalse(ok)
        self.assertIn("backwards", reason)

    def test_policy_orders_contiguous(self):
        policy = pp.load_policy()
        for endpoint in pp.ordered_environments(policy):
            self.assertEqual(
                pp.promotion_path(policy, endpoint),
                pp.ordered_environments(policy)[: pp.environments(policy)[endpoint]["order"]],
            )


class BackendTemplateConsistency(unittest.TestCase):
    """Backend templates must stay consistent with the Terraform modules."""

    def test_backend_templates_use_entra_auth_only(self):
        for env in pp.ordered_environments():
            raw = (ROOT / "examples" / "backend" / f"{env}.backend.hcl").read_text()
            self.assertRegex(raw, r"use_azuread_auth\s*=\s*true")
            self.assertRegex(raw, r"use_oidc\s*=\s*true")

    def test_backend_templates_contain_no_real_identifiers(self):
        guid = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                          r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
        for env in pp.ordered_environments():
            raw = (ROOT / "examples" / "backend" / f"{env}.backend.hcl").read_text()
            self.assertIsNone(guid.search(raw), f"{env} backend leaks a real GUID")
            self.assertIn("<STATE_RESOURCE_GROUP_NAME>", raw)
            self.assertIn("<STATE_STORAGE_ACCOUNT_NAME>", raw)

    def test_module_container_naming_matches_templates(self):
        src = (TF / "modules" / "state_backend" / "main.tf").read_text()
        self.assertIn('name                  = "tfstate-${each.value}"', src)
        for env in pp.ordered_environments():
            raw = (ROOT / "examples" / "backend" / f"{env}.backend.hcl").read_text()
            self.assertIn(f'"tfstate-{env}"', raw)


if __name__ == "__main__":
    unittest.main()
