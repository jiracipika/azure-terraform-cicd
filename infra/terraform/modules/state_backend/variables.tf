variable "resource_group_name" {
  description = "Resource group hosting the state storage account."
  type        = string
}

variable "location" {
  description = "Azure region for the state storage account."
  type        = string
}

variable "storage_account_name" {
  description = "Globally unique, 3-24 lowercase alphanumeric characters."
  type        = string
}

variable "environment_names" {
  description = "Promotion path environments; one private state container (tfstate-<name>) is created per environment."
  type        = set(string)
  default     = ["dev", "stage", "prod"]
}

variable "replication_type" {
  description = "Standard_LRS for dev foundations, Standard_ZRS for stage/prod (state durability)."
  type        = string
  default     = "Standard_ZRS"

  validation {
    condition     = contains(["Standard_LRS", "Standard_ZRS", "Standard_GRS"], var.replication_type)
    error_message = "replication_type must be Standard_LRS, Standard_ZRS or Standard_GRS."
  }
}

variable "state_retention_days" {
  description = "Soft-delete retention for state blobs and deleted containers."
  type        = number
  default     = 30

  validation {
    condition     = var.state_retention_days >= 1 && var.state_retention_days <= 365
    error_message = "state_retention_days must be between 1 and 365."
  }
}

variable "public_network_access_enabled" {
  description = "GitHub-hosted runners must reach state over the public endpoint (Entra ID auth only). Set false only together with trusted self-hosted runners and network rules."
  type        = bool
  default     = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
