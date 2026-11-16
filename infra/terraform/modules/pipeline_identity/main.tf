# Pipeline identities: GitHub Actions federates to Entra ID via OIDC.
# Two least-privilege identities keep plan and apply separated so a
# compromised PR "plan" job can never mutate Azure resources: only the
# apply identity holds write permissions, and only environment-gated
# (manually approved) workflow jobs can federate as it.

resource "azurerm_user_assigned_identity" "plan" {
  name                = var.plan_identity_name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_user_assigned_identity" "apply" {
  name                = var.apply_identity_name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

# Federated credentials are environment-scoped
# (repo:ORG/REPO:environment:E): a token is minted only inside a job that
# requests GitHub environment E, where required reviewers / branch rules
# enforce the human approval gate. Never widen the subject to wildcard claims
# (whole repo or any branch) without re-reviewing docs/SECURITY.md.
resource "azurerm_federated_identity_credential" "plan" {
  for_each = var.environment_names

  name      = "github-plan-${each.value}"
  parent_id = azurerm_user_assigned_identity.plan.id
  audience  = ["api://AzureADTokenExchange"]
  issuer    = "https://token.actions.githubusercontent.com"
  subject   = "repo:${var.github_org}/${var.github_repo}:environment:${each.value}"
}

resource "azurerm_federated_identity_credential" "apply" {
  for_each = var.environment_names

  name      = "github-apply-${each.value}"
  parent_id = azurerm_user_assigned_identity.apply.id
  audience  = ["api://AzureADTokenExchange"]
  issuer    = "https://token.actions.githubusercontent.com"
  subject   = "repo:${var.github_org}/${var.github_repo}:environment:${each.value}"
}

# State access for both identities: read/write state blobs and acquire the
# blob lease that implements azurerm backend state locking.
resource "azurerm_role_assignment" "plan_state" {
  scope                = var.state_storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.plan.principal_id
}

resource "azurerm_role_assignment" "apply_state" {
  scope                = var.state_storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.apply.principal_id
}

# Optional workload scope. Plan stays read-only (Reader); only the apply
# identity can change Azure resources, and only after the environment gate.
resource "azurerm_role_assignment" "plan_read" {
  count = var.target_resource_group_id != null ? 1 : 0

  scope                = var.target_resource_group_id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.plan.principal_id
}

resource "azurerm_role_assignment" "apply_write" {
  count = var.target_resource_group_id != null ? 1 : 0

  scope                = var.target_resource_group_id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.apply.principal_id
}
