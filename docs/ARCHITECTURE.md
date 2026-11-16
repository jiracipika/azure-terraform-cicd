# Architecture

**Goal:** GitHub PR validate and plan -> protected OIDC apply to dev -> human-approved production; remote state in Azure Storage with blob-lease locking. This is an offline scaffold, NOT deployed production architecture (deploy_enabled=false gates every resource).

## Topology (as implemented)

```
Terraform CI/CD pipeline (this repo)
├── infra/terraform/                  root: the pipeline FOUNDATION stack
│   ├── modules/state_backend         hardened Azure Storage for remote state
│   ├── modules/pipeline_identity     plan/apply OIDC identities + RBAC
│   └── environments/{dev,stage,prod}.tfvars   per-level foundation values
├── infra/pipeline/policy.yaml        promotion policy (data, test-enforced)
├── examples/
│   ├── backend/*.backend.hcl         azurerm backend templates (Entra auth)
│   ├── pipelines/*.yml               INERT pipeline templates (PR plan,
│   │                                 apply-with-approval, drift detection)
│   └── oidc-claims.md                subject-claim design
├── .github/workflows/validate.yml    ACTIVE, validation-only (fmt/init/
│                                     validate + unittest scanners)
└── tests/                            70-test offline battery incl. the
                                      pipeline-policy simulator
```

## Promotion model (dev -> stage -> prod)

Defined as data in `infra/pipeline/policy.yaml` and enforced offline by
`tests/pipeline_policy.py`:

| Event | What runs | Apply? |
|---|---|---|
| pull_request | offline checks (fmt, validate, unittest scanners) + `terraform plan` preview for dev | never |
| push to main | offline checks + plan previews for stage and prod | never |
| workflow_dispatch | (inert template only) sequential apply dev -> stage -> prod, each job held until its GitHub environment reviewer approves | manual + gated |
| weekly schedule | read-only drift detection (`plan -detailed-exitcode`) per environment; opens an issue on drift | never |

Design decisions:

- **PRs preview dev only.** The PR is the change's first plan; stage/prod are
  planned post-merge (push to main) so previews reflect the merged ref.
- **Skip-level promotion is impossible.** A dispatch of the endpoint `prod`
  expands to the full path `dev, stage, prod`; the simulator refuses
  non-contiguous sequences (negative tests pin this).
- **Plan/apply separation.** Separate Entra identities: `id-cicd-plan`
  (Storage Blob Data Contributor on state + optional Reader) and
  `id-cicd-apply` (Storage Blob Data Contributor + optional Contributor on
  the workload scope). A compromised plan job cannot mutate resources.
- **The approval gate is the GitHub environment.** Federated subjects are
  `repo:ORG/REPO:environment:E`, so an OIDC token is minted only inside a
  job that declares `environment: E`; configure required reviewers there
  before any approved deployment.

## Remote state

`modules/state_backend` creates one storage account with private
`tfstate-<env>` containers per environment (blob-lease locking is native to
the azurerm backend). Hardening: HTTPS-only, TLS 1.2 floor,
`shared_access_key_enabled = false` (Entra/OIDC authorization only —
`use_azuread_auth` + `use_oidc` in the backend templates),
`default_to_oauth_authentication = true`, infrastructure encryption, blob
versioning + soft delete for blobs and containers. Backend templates live in
`examples/backend/` with `<PLACEHOLDER>` names — never real identifiers.

## Trust boundaries

1. **GitHub control plane** — pushes/PRs/dispatches; only the inert template
   can ever reach an apply, and only through environment approvals.
2. **OIDC boundary** — token exchange pinned to audience
   `api://AzureADTokenExchange`, issuer `token.actions.githubusercontent.com`,
   subject = repo + environment. No persistent cloud keys anywhere.
3. **State data plane** — public endpoint reachable by hosted runners
   (documented tradeoff; disable via variable when moving to trusted
   self-hosted runners), Entra-auth-only, RBAC-scoped to the account.
4. **Workload scope** — optional `target_resource_group_id` is the ONLY
   place the apply identity gets Contributor; null until a workload is
   approved.

## Disaster recovery

State blob versioning + container soft delete (14/30/90 days per level) allow
recovering overwritten/deleted state; ZRS for stage/prod foundations
tolerates a zone outage. Drift detection (weekly) surfaces out-of-band
changes for triage. Verify regional availability and quotas before any
approved deployment.

## Separation of planes

Internet edge (GitHub runners), CI credentials (OIDC identities), control
plane (GitHub environments + policy.yaml) and data plane (state storage) are
separate. Private services would additionally require a reachable private
runner or network path; DNS/routing/firewall verification is a deployment-time
task, not assumed here.
