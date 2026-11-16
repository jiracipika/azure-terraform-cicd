# Tests and verification

Every entry below is an actual command execution with its real result. Azure
live deployment: **NOT RUN** (no authorization; `deploy_enabled=false`).

## 2026-11-16T15:55Z — local offline battery (GLM/ZCode session, terraform v1.9.8, azurerm 4.81.0)

| Command | Result | Evidence |
|---|---|---|
| `python3 -m unittest discover -s tests` | **PASS** | `Ran 70 tests ... OK` |
| `terraform -chdir=infra/terraform fmt -check -recursive` | **PASS** | exit 0 |
| `terraform -chdir=infra/terraform init -backend=false -input=false` | **PASS** | azurerm v4.81.0 from committed lock file; state_backend + pipeline_identity modules loaded |
| `terraform -chdir=infra/terraform validate` | **PASS** | `Success! The configuration is valid.` |
| `terraform -chdir=infra/terraform providers schema -json` | **PASS** | azurerm 4.81.0 schema dump used to verify every resource attribute before writing (see method note) |

### Failures found and fixed during this run (real history)

1. Prior CI runs (43875639885, 43875792120) failed `fmt -check` exit 3 on the
   scaffold `variables.tf` — fixed with `terraform fmt -recursive` and pushed
   (commit "fix: canonical terraform fmt so validate workflow passes").
2. That fix exposed a second latent failure: run 43898443936 failed
   `python3 -m unittest` because `tests/test_scaffold.py` asserted the exact
   string `default = false`, which canonical fmt realigns to
   `default     = false`. All scaffold assertions were rewritten as regexes
   (the milestone rewrite) — exact-string matching is now banned by convention
   in this repo's tests.
3. First milestone test run (70 tests): 6 failures, all real catches —
   (a) PR scenarios expected `plans == ["dev"]` but `policy.yaml` had stage
   planning on PRs too; resolved by design decision (PRs preview dev,
   push-to-main previews stage+prod) and fixed the policy;
   (b) the diagram test failed because `diagrams/architecture.mmd` was still
   the scaffold stub — the diagram was rewritten to the implemented
   promotion model (the failure was stale documentation, exactly what the
   test exists to catch);
   (c) gitignore assertion lacked `re.M` for line-anchored patterns;
   (d) lock-file assertion expected `"hashicorp/azurerm"` quoted form (lock
   file uses the full registry address);
   (e) the wildcard-subject test matched the *comment* "repo:*" in
   pipeline_identity/main.tf — comment reworded;
   (f) two stray placeholder lines in freshly written tests were removed.
4. `terraform validate` passed first try after variable declaration fix —
   resource attributes were verified against the provider schema BEFORE
   writing (no validate churn).

### Schema verification method (as required)

`terraform -chdir=infra/terraform providers schema -json` (azurerm 4.81.0)
confirmed every resource/block used: `azurerm_storage_account`
(`https_traffic_only_enabled`, `shared_access_key_enabled`,
`default_to_oauth_authentication`, `allow_nested_items_to_be_public`,
`infrastructure_encryption_enabled`, `min_tls_version`,
`public_network_access_enabled`, nested `blob_properties` list block with
`versioning_enabled`, `delete_retention_policy { days }`,
`container_delete_retention_policy { days }`), `azurerm_storage_container`
(`container_access_type`), `azurerm_user_assigned_identity`
(`client_id`/`principal_id`), `azurerm_federated_identity_credential`
(`parent_id`, `audience`, `issuer`, `subject`), `azurerm_role_assignment`
(`scope`, `role_definition_name`, `principal_id`). Nothing was guessed.

### Pipeline simulator evidence (the deterministic offline demo)

- PR changing `infra/terraform/modules/state_backend/main.tf` ->
  checks `[unittest, terraform fmt -check, terraform init -backend=false,
  terraform validate]`, plans `['dev']`, apply NOT permitted.
- push to main -> plans `['stage', 'prod']`, apply NOT permitted
  ("no auto-apply on push").
- dispatch endpoint prod -> apply permitted ONLY as full path
  `['dev', 'stage', 'prod']` with approval required, and ONLY while the
  template's `environment:` gates exist (removing them is refused — pinned
  by `test_dispatch_ungated_apply_template_refused`).

## GitHub Actions

| Date | Run | Conclusion |
|---|---|---|
| 2026-11-16T13:25Z | 43875639885 (scaffold) | failure — `fmt -check` exit 3 |
| 2026-11-16T13:26Z | 43875792120 (scaffold) | failure — `fmt -check` exit 3 |
| 2026-11-16T15:38Z | 43898443936 (fmt fix) | failure — exact-string unittest assertion (`default = false`) |
| 2026-11-16 (milestone) | recorded after push | see below |
