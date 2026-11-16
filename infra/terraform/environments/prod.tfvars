# prod foundation values (promotion level 3 of 3 — see infra/pipeline/policy.yaml).
# deploy_enabled stays false until the owner approves deployment (docs/COSTS.md).
deploy_enabled       = false
location             = "canadacentral"
storage_account_name = "sttfstatecicdprd01"
replication_type     = "Standard_ZRS"
state_retention_days = 90
