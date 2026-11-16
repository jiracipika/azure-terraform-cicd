# Azure cost gate

Authorized Azure spend: **$0**. Nothing is deployed (`deploy_enabled=false`
in the root default and every `environments/*.tfvars`).

## Estimate IF the foundation were deployed after approval

Verified against Azure pricing structure, not a quote (region canadacentral;
prices change — re-check at approval time):

| Resource | SKU | Rough monthly cost |
|---|---|---|
| Resource group | — | $0 |
| Storage account (state) | Standard LRS (dev) | < $0.10 (state blobs are KB-scale) |
| Storage account (state) | Standard ZRS (stage/prod) | ~2x LRS, still < $0.50 |
| Blob soft delete + versioning | included | marginal, doubles billed blobs at most |
| User-assigned identities (x2) | — | $0 |
| Federated credentials (x6) | — | $0 |
| Role assignments (x4-6) | — | $0 |

Realistic total for the foundation: **well under $1/month**. Variable costs
would come from the workload stacks this pipeline deploys — each has its own
SKU, region, capacity, egress and telemetry retention and needs its own
approval. GitHub-hosted runners on public repos are free for this private
repo within the account's included minutes; validation-only jobs are ~1 min
each.

Budgets notify rather than enforce a hard spending ceiling. Request approval
for every chargeable deployment, with the exact scope and maximum budget.
