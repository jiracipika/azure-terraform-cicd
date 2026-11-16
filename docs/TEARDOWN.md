# Teardown

No Azure resources are deployed (`deploy_enabled = false`). This is the
inventory of what an approved deployment of this stack WOULD create, in
reverse teardown order, plus rollback notes.

## Deployment inventory (per promotion level applied)

| Order | Resource | Terraform address |
|---|---|---|
| 1 | Role assignments (state blob + optional workload Reader/Contributor) | `module.pipeline_identity[0].azurerm_role_assignment.*` |
| 2 | Federated identity credentials (6 = 2 identities x 3 environments) | `module.pipeline_identity[0].azurerm_federated_identity_credential.*` |
| 3 | User-assigned identities `id-cicd-plan`, `id-cicd-apply` | `module.pipeline_identity[0].azurerm_user_assigned_identity.*` |
| 4 | State containers `tfstate-dev/stage/prod` | `module.state_backend[0].azurerm_storage_container.state` |
| 5 | State storage account | `module.state_backend[0].azurerm_storage_account.state` |
| 6 | Resource group `rg-terraform-cicd-foundation` | `azurerm_resource_group.this` |

## Teardown sequence (owner-approved only)

1. **Export state first**: back up every `tfstate-*` blob (they are
   soft-deleted for 14/30/90 days per level, but treat soft delete as a
   safety net, not a backup strategy).
2. `terraform destroy` against the same `-var-file=environments/<env>.tfvars`
   and backend config used at apply — never delete the storage account while
   another stack's state lives in it.
3. If destroying manually instead: remove role assignments and federated
   credentials BEFORE the identities, containers before the account.
4. Post-checks: no orphaned resource groups, no leftover `tfstate-*`
   containers elsewhere, GitHub environments/secrets referencing the
   identities removed, and any workload stacks re-pointed or torn down.
5. Inspect afterward for orphaned paid endpoints, IPs, disks, gateways and
   log retention.

Before any approved deployment, document state, resource dependencies and
rollback steps, authorize deletion, and re-verify this list against the
actual plan output.
