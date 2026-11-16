output "status" {
  description = "Always-offline marker; the pipeline never applies this stack automatically."
  value       = "offline-scaffold-only"
}

output "state_resource_group_name" {
  description = "Feeds resource_group_name in examples/backend/*.backend.hcl. Populated only after an approved deployment (deploy_enabled)."
  value       = one(azurerm_resource_group.this[*].name)
}

output "state_storage_account_name" {
  description = "Feeds storage_account_name in examples/backend/*.backend.hcl. Null while deploy_enabled is false."
  value       = one(module.state_backend[*].storage_account_name)
}

output "state_container_names" {
  description = "Environment -> state container (tfstate-<env>). Null while deploy_enabled is false."
  value       = one(module.state_backend[*].container_names)
}

output "plan_identity_client_id" {
  description = "AZURE_CLIENT_ID for PR plan jobs; store as GitHub secret AZURE_PLAN_CLIENT_ID."
  value       = one(module.pipeline_identity[*].plan_client_id)
}

output "apply_identity_client_id" {
  description = "AZURE_CLIENT_ID for environment-gated apply jobs; store as GitHub secret AZURE_APPLY_CLIENT_ID."
  value       = one(module.pipeline_identity[*].apply_client_id)
}
