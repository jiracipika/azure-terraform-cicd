"""Security assertions over the Terraform sources.

Offline static analysis: each test pins a control the modules must keep
enforcing. Regex assertions only — exact-string matches break on every
`terraform fmt` realignment. If someone relaxes a control, this suite fails
before CI does.
"""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "infra" / "terraform"


def read(rel: str) -> str:
    return (TF / rel).read_text()


class StateBackendHardening(unittest.TestCase):
    """Remote state storage: Entra-auth-only, encrypted, versioned, private."""

    def setUp(self):
        self.src = read("modules/state_backend/main.tf")

    def test_https_only(self):
        self.assertRegex(self.src, r"https_traffic_only_enabled\s*=\s*true")

    def test_minimum_tls_1_2(self):
        self.assertRegex(self.src, r'min_tls_version\s*=\s*"TLS1_2"')

    def test_no_shared_key_auth(self):
        self.assertRegex(self.src, r"shared_access_key_enabled\s*=\s*false")

    def test_oauth_preferred(self):
        self.assertRegex(self.src, r"default_to_oauth_authentication\s*=\s*true")

    def test_no_public_blob_acl(self):
        self.assertRegex(self.src, r"allow_nested_items_to_be_public\s*=\s*false")

    def test_infrastructure_encryption(self):
        self.assertRegex(self.src, r"infrastructure_encryption_enabled\s*=\s*true")

    def test_state_blobs_are_versioned(self):
        self.assertRegex(self.src, r"versioning_enabled\s*=\s*true")

    def test_state_blobs_soft_deleted(self):
        self.assertIn("delete_retention_policy", self.src)
        self.assertRegex(self.src, r"days\s*=\s*var\.state_retention_days")

    def test_deleted_containers_soft_deleted(self):
        self.assertIn("container_delete_retention_policy", self.src)

    def test_state_containers_private(self):
        self.assertRegex(self.src, r'container_access_type\s*=\s*"private"')

    def test_one_container_per_promotion_environment(self):
        self.assertIn("for_each = var.environment_names", self.src)
        self.assertRegex(self.src, r'name\s*=\s*"tfstate-\$\{each\.value\}"')

    def test_public_network_access_is_an_explicit_variable(self):
        """Documented tradeoff: required for hosted runners, never hardcoded."""
        self.assertRegex(self.src,
                         r"public_network_access_enabled\s*=\s*var\.public_network_access_enabled")
        self.assertRegex(read("variables.tf"),
                         r'"state_public_network_access_enabled"\s*\{[^}]*default\s*=\s*true')


class PipelineIdentityHardening(unittest.TestCase):
    """OIDC federation: environment-scoped subjects, least privilege, no keys."""

    def setUp(self):
        self.src = read("modules/pipeline_identity/main.tf")

    def test_oidc_issuer_is_github(self):
        self.assertIn("https://token.actions.githubusercontent.com", self.src)

    def test_audience_is_azure_token_exchange(self):
        self.assertIn("api://AzureADTokenExchange", self.src)

    def test_subjects_are_environment_scoped(self):
        self.assertEqual(
            len(re.findall(
                r'subject\s*=\s*"repo:\$\{var\.github_org\}/\$\{var\.github_repo\}:environment:\$\{each\.value\}"',
                self.src)),
            2,  # plan + apply federated credential sets
        )

    def test_no_wildcard_subjects(self):
        self.assertIsNone(re.search(r'subject\s*=\s*"repo:[^"]*\*', self.src))
        self.assertIsNone(re.search(r"repo:\*", self.src))

    def test_plan_and_apply_identities_are_separate(self):
        self.assertIn('resource "azurerm_user_assigned_identity" "plan"', self.src)
        self.assertIn('resource "azurerm_user_assigned_identity" "apply"', self.src)

    def test_state_role_is_blob_data_contributor_only(self):
        roles = re.findall(r'role_definition_name\s*=\s*"([^"]+)"', self.src)
        self.assertEqual(sorted(roles),
                         ["Contributor", "Reader", "Storage Blob Data Contributor",
                          "Storage Blob Data Contributor"])

    def test_workload_write_role_only_on_optional_target(self):
        self.assertRegex(self.src,
                         r'count\s*=\s*var\.target_resource_group_id\s*!=\s*null\s*\?\s*1\s*:\s*0')
        self.assertRegex(read("variables.tf"),
                         r'"target_resource_group_id"\s*\{[^}]*default\s*=\s*null')

    def test_no_client_secrets_in_module(self):
        self.assertIsNone(re.search(r"(?i)client_secret", self.src))


class SpendGuard(unittest.TestCase):
    """No resources may exist unless deploy_enabled is explicitly set."""

    def test_deploy_disabled_by_default(self):
        self.assertRegex(read("variables.tf"),
                         r'"deploy_enabled"\s*\{[^}]*default\s*=\s*false')

    def test_resource_group_and_both_modules_gated(self):
        main = read("main.tf")
        self.assertEqual(main.count("var.deploy_enabled ? 1 : 0"), 3,
                         "resource group + 2 modules must all be gated")

    def test_every_environment_tfvars_stays_disabled(self):
        for env in ("dev", "stage", "prod"):
            src = read(f"environments/{env}.tfvars")
            self.assertRegex(src, r"deploy_enabled\s*=\s*false",
                             f"environments/{env}.tfvars enabled deployment")


class ProviderHygiene(unittest.TestCase):
    """Provider and module pinning practices (the repo's own theme)."""

    def test_every_child_module_declares_required_providers(self):
        for versions in sorted((TF / "modules").glob("*/versions.tf")):
            self.assertRegex(versions.read_text(),
                             r'required_providers\s*\{[^}]*azurerm',
                             f"{versions.parent.name} missing required_providers")

    def test_azurerm_pinned_to_major_4(self):
        self.assertRegex(read("versions.tf"), r'azurerm\s*=\s*\{[^}]*version\s*=\s*"~>\s*4\.0"')

    def test_subscription_id_is_placeholder(self):
        self.assertRegex(read("providers.tf"), r"subscription_id\s*=\s*var\.azure_subscription_id")
        self.assertRegex(read("variables.tf"),
                         r'"azure_subscription_id"\s*\{[^}]*default\s*=\s*"00000000-0000-0000-0000-000000000000"')

    def test_no_unpinned_external_module_sources(self):
        """Any github/registry module reference must carry a version/ref pin."""
        block_re = re.compile(r'module\s+"\w+"\s*\{(.*?)\n\}', re.S)
        for tf in sorted(TF.rglob("*.tf")):
            for m in block_re.finditer(tf.read_text()):
                body = m.group(1)
                src_m = re.search(r'source\s*=\s*"([^"]+)"', body)
                if not src_m or src_m.group(1).startswith(("./", "../", "\"")):
                    continue
                src = src_m.group(1)
                pinned = "?ref=" in src or re.search(r'version\s*=\s*"', body)
                self.assertTrue(
                    pinned,
                    f"unpinned external module source '{src}' in {tf.name}: "
                    "pin with ?ref= (git) or version = (registry)",
                )

    def test_no_real_subscription_guids_anywhere(self):
        zero = "00000000-0000-0000-0000-000000000000"
        for tf in sorted(TF.rglob("*.tf")):
            for m in re.finditer(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                                 r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", tf.read_text()):
                self.assertEqual(m.group(0), zero,
                                 f"real-looking GUID in {tf.name}: {m.group(0)}")


if __name__ == "__main__":
    unittest.main()
