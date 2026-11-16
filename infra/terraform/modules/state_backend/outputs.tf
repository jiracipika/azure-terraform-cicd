output "storage_account_id" {
  description = "RBAC scope for the pipeline identities (Storage Blob Data Contributor)."
  value       = azurerm_storage_account.state.id
}

output "storage_account_name" {
  description = "Feeds storage_account_name in examples/backend/*.backend.hcl."
  value       = azurerm_storage_account.state.name
}

output "container_names" {
  description = "Map of environment -> state container name; feeds container_name in examples/backend/*.backend.hcl."
  value       = { for env, c in azurerm_storage_container.state : env => c.name }
}

output "primary_blob_endpoint" {
  value = azurerm_storage_account.state.primary_blob_endpoint
}
