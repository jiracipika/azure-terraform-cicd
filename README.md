# 08 — Terraform CI/CD Pipeline

**Azure Cloud Engineering Portfolio** · [GitHub: jiracipika](https://github.com/jiracipika) · **PRIVATE repository** · **Offline scaffold / Azure NOT DEPLOYED**

## Goal
Validate plan workflows without automatically applying paid infrastructure:
GitHub PR validate and plan -> protected OIDC apply to dev -> human-approved
production, with remote state in Azure Storage (blob-lease locking).

## Status — milestone implemented 2026-11-16 (offline validation green)

- **Terraform modules** (all gated behind `deploy_enabled`, default false):
  `state_backend` (hardened remote-state storage: Entra-only auth, versioning,
  soft delete, per-environment containers) and `pipeline_identity`
  (separate plan/apply OIDC identities, environment-scoped federated
  credentials, least-privilege RBAC).
- **Promotion model as code**: `infra/pipeline/policy.yaml` (dev -> stage ->
  prod, manual applies only) + `tests/pipeline_policy.py`, an offline
  simulator that replays PR / push-main / dispatch events against the REAL
  workflows and templates.
- **Pipeline templates (INERT)**: `examples/pipelines/` (PR plan, apply with
  GitHub-environment approval gates, weekly read-only drift detection) and
  `examples/backend/*.backend.hcl` azurerm backend templates — inert by
  location, never executed by GitHub Actions.
- **Active CI** (`.github/workflows/validate.yml`): validation-only
  (unittest static security/policy scanners + terraform fmt/init/validate),
  `contents: read`, pinned actions. **No automatic apply exists in this
  repository.**
- 70-test offline battery green; terraform fmt/init/validate green
  (docs/VALIDATION.md has the real outputs).

## GLM / ZCode — start here

1. Read [AGENTS.md](AGENTS.md), [GLM tasks](docs/GLM_TASKS.md), [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), and [validation](docs/VALIDATION.md).
2. Implement the next offline milestone in **docs/GLM_TASKS.md** with runnable code and negative tests, not just a plan.
3. Verify Terraform syntax and security, run unit tests, record actual results, and keep diagrams/documentation current.
4. **Do not apply Terraform or deploy any billable Azure resources or alter cloud IAM without my explicit approval.**
5. Report changed files, actual tests and blockers in your ZCode session and commits.

## Offline starting commands

```sh
python3 -m unittest discover -s tests -v
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init -backend=false -input=false
terraform -chdir=infra/terraform validate
```

## Source contents

- `AGENTS.md`: enforceable GLM implementation contract
- `docs/GLM_TASKS.md`: project-specific milestones and status
- `docs/ARCHITECTURE.md`: promotion model, trust boundaries, DR
- `docs/SECURITY.md` / `docs/COSTS.md`: threat-model control map and cost gate
- `docs/VALIDATION.md`: real evidence only
- `docs/TEARDOWN.md`: future approved cleanup plan
- `diagrams/architecture.mmd`: promotion topology (editable Mermaid)
- `infra/terraform/`: root foundation stack + `modules/state_backend`,
  `modules/pipeline_identity`, `environments/{dev,stage,prod}.tfvars`
- `infra/pipeline/policy.yaml`: environment promotion policy (data)
- `examples/`: INERT pipeline templates, backend config templates, OIDC claims
- `.github/workflows/validate.yml`: offline validation, no deploy step
- `tests/`: 70-test offline battery incl. pipeline-policy simulator

## Status and safety

Terraform defines Azure resources only behind `deploy_enabled=false`
(default, and in every per-environment tfvars), so `terraform plan` proposes
zero changes. Applies exist only as inert templates under `examples/`.
**Repository visibility must remain PRIVATE.** No credentials, secrets, real
customer data, Terraform state or internal account identifiers may be committed.
