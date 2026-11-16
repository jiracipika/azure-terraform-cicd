variable "resource_group_name" {
  description = "Resource group hosting the pipeline identities."
  type        = string
}

variable "location" {
  description = "Azure region for the managed identities."
  type        = string
}

variable "github_org" {
  description = "GitHub organization/user owning the repository."
  type        = string
}

variable "github_repo" {
  description = "Repository name used in the OIDC subject claim."
  type        = string
}

variable "environment_names" {
  description = "Promotion path environments; one federated credential per environment per identity (must match infra/pipeline/policy.yaml)."
  type        = set(string)
  default     = ["dev", "stage", "prod"]
}

variable "plan_identity_name" {
  description = "Read-only identity used by PR plan jobs."
  type        = string
  default     = "id-cicd-plan"
}

variable "apply_identity_name" {
  description = "Write identity used ONLY by environment-gated apply jobs."
  type        = string
  default     = "id-cicd-apply"
}

variable "state_storage_account_id" {
  description = "Scope of the identities' state access (Storage Blob Data Contributor: read/write state blobs + blob lease locks)."
  type        = string
}

variable "target_resource_group_id" {
  description = "Optional workload resource-group scope: plan identity receives Reader, apply identity receives Contributor. Leave null until a workload stack is approved."
  type        = string
  default     = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
