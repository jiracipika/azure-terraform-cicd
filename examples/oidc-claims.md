# GitHub OIDC claims

Federated identity must restrict audience to `api://AzureADTokenExchange`
and issuer to `https://token.actions.githubusercontent.com`. Avoid credential
secrets and overly broad wildcard subjects. Review plan output and state
permissions; never automatically apply in this scaffold.

## Subject claim design used by modules/pipeline_identity

This repository federates **environment-scoped** subjects:

```
repo:jiracipika/azure-terraform-cicd:environment:<env>
```

for `env` in `dev`, `stage`, `prod` (matching `infra/pipeline/policy.yaml`).
A token is minted only inside a workflow job that declares
`environment: <env>`, which is where the human approval gate lives: configure
each GitHub environment with required reviewers and branch restrictions
before any approved deployment. Two separate identities keep plan and apply
least-privilege:

| Identity | Federated credential per env | Azure roles |
|---|---|---|
| `id-cicd-plan` | `github-plan-<env>` | Storage Blob Data Contributor (state only) + optional Reader on workload scope |
| `id-cicd-apply` | `github-apply-<env>` | Storage Blob Data Contributor (state only) + optional Contributor on workload scope |

A compromised PR "plan" job therefore cannot mutate Azure resources: it holds
no write permission, and only environment-gated (approved) jobs can federate
as the apply identity.

## Forbidden subject patterns

Never configure (or accept in review):

- `repo:org/repo:*` — matches every claim shape for the repo
- `repo:org/repo:ref:refs/heads/*` — any branch, including unprotected ones
- `repo:org/*` or broader — other repositories in the org

The offline test-suite pins this: `tests/test_terraform_security.py` fails if
a wildcard subject appears in `modules/pipeline_identity/main.tf`.
