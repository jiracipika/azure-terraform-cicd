variable "deploy_enabled" {
  description = "Default-off guard. When false, `terraform plan` shows zero Azure resources."
  type        = bool
  default     = false
}

variable "location" {
  description = "Azure region for the pipeline foundation."
  type        = string
  default     = "canadacentral"
}

variable "azure_subscription_id" {
  description = "Target subscription. Placeholder default passes offline validation only."
  type        = string
  default     = "00000000-0000-0000-0000-000000000000"
}

variable "resource_group_name" {
  description = "Resource group for the state backend and pipeline identities."
  type        = string
  default     = "rg-terraform-cicd-foundation"
}

variable "storage_account_name" {
  description = "State storage account: globally unique, 3-24 lowercase alphanumeric characters."
  type        = string
  default     = "sttfstatecicddev01"
}

variable "replication_type" {
  description = "Standard_LRS for dev foundations, Standard_ZRS for stage/prod."
  type        = string
  default     = "Standard_ZRS"
}

variable "state_retention_days" {
  description = "Soft-delete retention for state blobs and deleted containers."
  type        = number
  default     = 30
}

variable "state_public_network_access_enabled" {
  description = "Required true for GitHub-hosted runners (Entra ID auth only); set false only with trusted self-hosted runners."
  type        = bool
  default     = true
}

variable "environment_names" {
  description = "Promotion path environments; must match infra/pipeline/policy.yaml."
  type        = set(string)
  default     = ["dev", "stage", "prod"]
}

variable "github_org" {
  description = "GitHub organization/user for OIDC subject claims."
  type        = string
  default     = "jiracipika"
}

variable "github_repo" {
  description = "Repository name for OIDC subject claims."
  type        = string
  default     = "azure-terraform-cicd"
}

variable "target_resource_group_id" {
  description = "Optional workload resource-group scope for plan (Reader) / apply (Contributor) role assignments. Leave null until a workload stack is approved."
  type        = string
  default     = null
}

variable "tags" {
  type = map(string)
  default = {
    environment = "portfolio-lab"
    managed_by  = "terraform"
  }
}
