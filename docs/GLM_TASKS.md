# GLM implementation instructions — Terraform CI/CD Pipeline

**Architecture:** GitHub PR validate and plan -> protected OIDC apply to dev -> human-approved production; remote state in Azure Storage with blob lease locking.

**Goal:** Generate safe plans, secure PR checks and reviewable infrastructure changes.

## Offline implementation backlog

- [x] Audit existing files, Azure documentation and actual available tools. *(2026-11-16: audit complete — terraform v1.9.8 + azurerm 4.81.0 schema verified via `providers schema -json`; no tflint/checkov locally, so scanners are unittest-based; CI was red on scaffold fmt + exact-string test — both fixed.)*
- [x] Implement realistic modular IaC for all named services; leave deploy_enabled=false as default. *(2026-11-16: `modules/state_backend` — hardened Azure Storage state backend with per-environment containers, blob-lease locking, versioning + soft delete, Entra-only auth; `modules/pipeline_identity` — separate plan/apply OIDC identities, environment-scoped federated credentials, least-privilege RBAC; root gates everything behind `deploy_enabled`; per-level `environments/{dev,stage,prod}.tfvars`.)*
- [x] Implement deterministic offline demo covering generate safe plans, secure pr checks and reviewable infrastructure changes. *(2026-11-16: `infra/pipeline/policy.yaml` promotion policy as data + `tests/pipeline_policy.py` simulator replaying PR / push-main / dispatch events against the real workflows and inert templates: PR => checks + dev plan, never apply; main => no auto-apply; dispatch => sequential gated apply only; skip-level refused; ungated apply refused.)*
- [x] Create behavior, failure and negative-security tests. *(2026-11-16: 70 tests — behavior scenarios, failure paths (unknown env, skip-level, backwards, ungated apply), negative security (wildcard subjects, secrets-like literals, forbidden terraform/azure subcommands, unpinned actions/modules).)*
- [x] Add static security scanners, dependency review and minimal CI permissions; pin tested action versions. *(2026-11-16: unittest-based static HCL/YAML scanners run as a named CI step (reproducible locally and in CI, zero network); dependency pinning enforced by tests (provider lock file committed, `~> 4.0` pin, external modules must carry ref/version); active workflow `permissions: contents: read`; all actions pinned. tflint/checkov jobs deferred — no local binaries to prove green, same decision as the sibling repos.)*
- [x] Refine topology diagram, network/identity trust boundaries and disaster recovery paths. *(2026-11-16: `diagrams/architecture.mmd` rewritten to the implemented promotion model; trust boundaries + DR (state versioning/soft delete, ZRS, drift detection) documented in docs/ARCHITECTURE.md.)*
- [x] Run unittest, terraform fmt, init -backend=false, validate and document real output. *(2026-11-16: all green — real commands and outputs in docs/VALIDATION.md.)*

## Cost gate

- [x] Estimate fixed and variable regional Azure costs; verify licenses and quotas. *(2026-11-16: foundation estimate well under $1/mo documented in docs/COSTS.md; authorized spend remains $0.)*
- [ ] Require explicit approval for exact deployment scope, maximum budget and teardown. *(Awaiting owner.)*
- [ ] Only after approval may live testing, performance measurements and cost validation occur.

## Next milestone (offline, no approval needed)

- Add a policy-as-code drift guard: parse `policy.yaml` into a rendered
  CONTRIBUTING/PIPELINE.md for human reviewers.
- Add a template workflow for module release tagging (registry pinning
  practice: tag + checksum verification) under examples/pipelines/.
- Consider a tflint job (pinned) once a runner-local reproduction path exists.

## Live deployment (owner approval required first)

Approve the cost scope in docs/COSTS.md, provide the subscription, configure
GitHub environments `dev`/`stage`/`prod` with required reviewers, then run the
teardown-inventory apply sequence from docs/TEARDOWN.md.

Don't stop at proposals. Start implementing an offline slice now and submit evidence.
