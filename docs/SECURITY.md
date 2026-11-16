# Threat model

Threats: supply-chain compromise, privileged CI job, state exposure,
accidental public endpoints, lateral workload movement, log data leaks and
incomplete teardown.

## Controls as implemented

| Threat | Control (file) | Offline test |
|---|---|---|
| Supply-chain compromise | pinned actions (`@v4`/`@v3`/`@v2`/`@v7`), committed provider lock file, `~> 4.0` provider pin, external modules must be ref/version-pinned | `test_terraform_security.ProviderHygiene`, `test_pipeline_policy.ActiveWorkflowSafety` |
| Privileged CI job runs apply | ACTIVE workflows may run terraform `fmt/init/validate` only; applies exist solely in the inert `examples/pipelines/` templates, and only in `environment:`-gated jobs; plan/apply identities are separate Entra identities | `test_pipeline_policy.ActiveWorkflowSafety`, `TemplateSafety`, `test_terraform_security.PipelineIdentityHardening` |
| Stolen GitHub token replay | OIDC subjects are environment-scoped (`repo:ORG/REPO:environment:E`); no wildcard subjects; no stored cloud secrets (names only, values in GitHub/Entra) | `test_terraform_security.test_no_wildcard_subjects`, `test_pipeline_policy.test_templates_only_reference_secret_names` |
| State exposure | `shared_access_key_enabled = false`, Entra/OIDC-only auth, TLS 1.2 floor, HTTPS-only, private containers, infrastructure encryption, versioning + soft delete | `test_terraform_security.StateBackendHardening` |
| Accidental public endpoints | `allow_nested_items_to_be_public = false`; state containers `container_access_type = "private"`; no public IP/front-door resources in this stack | same |
| Lateral movement | RBAC scoped to the state storage account (+ optional single workload RG); plan identity is read-only outside state | `test_state_role_is_blob_data_contributor_only`, `test_workload_write_role_only_on_optional_target` |
| Unapproved spend | `deploy_enabled = false` everywhere (root default + all environments/*.tfvars); every module gated | `test_terraform_security.SpendGuard` |
| Unreviewed promotion | sequential dev -> stage -> prod only; skip-level refused by simulator | `test_pipeline_policy.PromotionOrdering` |

## Mitigations summary

Minimum GitHub permissions (`contents: read` active workflows), reviewable
changes, state protection, scoped OIDC, no public admin access, cloud policy
guardrails and negative tests. Templates that could mutate Azure live ONLY
under `examples/pipelines/` (inert by location — outside
`.github/workflows/`).

## Runner network tradeoff (documented, not hidden)

GitHub-hosted runners must reach the state storage public endpoint, so
`public_network_access_enabled` defaults to true (variable
`state_public_network_access_enabled`). Authorization is Entra-only, which
is the actual security boundary; when moving to trusted self-hosted runners,
set it to false and add network rules.

## Before any approved deployment

- Configure GitHub environments `dev`/`stage`/`prod` with required reviewers
  and branch restrictions (verify they exist — do not assume).
- Store only identity/tenant/subscription IDs as GitHub secrets; never
  storage keys (they are disabled at the account level anyway).
- Re-review docs/TEARDOWN.md and docs/COSTS.md with the owner.

Do not configure cloud admin roles or enable paid production resources
automatically.
