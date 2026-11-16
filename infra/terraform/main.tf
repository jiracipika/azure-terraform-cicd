# Root module: the Terraform CI/CD foundation (remote-state backend +
# pipeline identities). Every Azure resource is gated behind deploy_enabled
# (default false): with the default variables `terraform plan` proposes zero
# changes outside the placeholder provider configuration.
#
# The foundation itself is promoted dev -> stage -> prod via the per-
# environment files in environments/ (see infra/pipeline/policy.yaml); the
# workload stacks deployed BY this pipeline use examples/ as their starting
# point.
locals {
  project = "azure-terraform-cicd"
  tags    = merge(var.tags, { project = local.project })
}

resource "azurerm_resource_group" "this" {
  count    = var.deploy_enabled ? 1 : 0
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

module "state_backend" {
  count = var.deploy_enabled ? 1 : 0

  source                        = "./modules/state_backend"
  resource_group_name           = one(azurerm_resource_group.this[*].name)
  location                      = var.location
  storage_account_name          = var.storage_account_name
  environment_names             = var.environment_names
  replication_type              = var.replication_type
  state_retention_days          = var.state_retention_days
  public_network_access_enabled = var.state_public_network_access_enabled
  tags                          = local.tags
}

module "pipeline_identity" {
  count = var.deploy_enabled ? 1 : 0

  source                   = "./modules/pipeline_identity"
  resource_group_name      = one(azurerm_resource_group.this[*].name)
  location                 = var.location
  github_org               = var.github_org
  github_repo              = var.github_repo
  environment_names        = var.environment_names
  state_storage_account_id = one(module.state_backend[*].storage_account_id)
  target_resource_group_id = var.target_resource_group_id
  tags                     = local.tags
}
