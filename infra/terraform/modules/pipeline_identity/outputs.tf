output "plan_client_id" {
  description = "AZURE_CLIENT_ID for PR plan jobs (store as GitHub secret AZURE_PLAN_CLIENT_ID)."
  value       = azurerm_user_assigned_identity.plan.client_id
}

output "apply_client_id" {
  description = "AZURE_CLIENT_ID for environment-gated apply jobs (store as GitHub secret AZURE_APPLY_CLIENT_ID)."
  value       = azurerm_user_assigned_identity.apply.client_id
}

output "plan_principal_id" {
  value = azurerm_user_assigned_identity.plan.principal_id
}

output "apply_principal_id" {
  value = azurerm_user_assigned_identity.apply.principal_id
}

output "federated_subjects" {
  description = "Map of environment -> GitHub OIDC subject claim (identical for plan and apply identities)."
  value       = { for env, cred in azurerm_federated_identity_credential.plan : env => cred.subject }
}
