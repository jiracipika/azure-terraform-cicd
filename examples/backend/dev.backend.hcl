# Partial backend configuration template for the dev environment (order 1).
#
# INERT EXAMPLE: pass with `terraform init -backend-config=<file>` only after
# an approved bootstrap deployment, substituting the <PLACEHOLDER> values with
# the root module outputs (state_resource_group_name, state_storage_account_name).
# container_name and key are deterministic — they match modules/state_backend
# naming for this stack (foundation).
#
# Authorization is Entra ID / OIDC only (use_azuread_auth + use_oidc): the
# storage account has shared_access_key_enabled = false, so no account key is
# ever used for state access. Blob-lease locking is native to the azurerm
# backend. Values for the auth environment variables come from the job's OIDC
# login (ARM_CLIENT_ID, ARM_TENANT_ID, ARM_SUBSCRIPTION_ID, ARM_USE_AZUREAD,
# ARM_USE_OIDC).

resource_group_name  = "<STATE_RESOURCE_GROUP_NAME>"
storage_account_name = "<STATE_STORAGE_ACCOUNT_NAME>"
container_name       = "tfstate-dev"
key                  = "foundation-dev.tfstate"

use_azuread_auth = true
use_oidc         = true
