# Remote-state backend: Azure Blob Storage with blob-lease locking (the
# azurerm backend's native state lock). Hardened for CI/CD: Entra ID / OIDC
# authorization only (shared key disabled), versioned and soft-deleted state
# blobs, private containers, TLS 1.2 floor, infrastructure encryption.

resource "azurerm_storage_account" "state" {
  name                              = var.storage_account_name
  resource_group_name               = var.resource_group_name
  location                          = var.location
  account_kind                      = "StorageV2"
  account_tier                      = "Standard"
  account_replication_type          = var.replication_type
  https_traffic_only_enabled        = true
  min_tls_version                   = "TLS1_2"
  public_network_access_enabled     = var.public_network_access_enabled
  shared_access_key_enabled         = false
  allow_nested_items_to_be_public   = false
  default_to_oauth_authentication   = true
  infrastructure_encryption_enabled = true
  tags                              = var.tags

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = var.state_retention_days
    }

    container_delete_retention_policy {
      days = var.state_retention_days
    }
  }
}

resource "azurerm_storage_container" "state" {
  for_each = var.environment_names

  name                  = "tfstate-${each.value}"
  storage_account_name  = azurerm_storage_account.state.name
  container_access_type = "private"
}
