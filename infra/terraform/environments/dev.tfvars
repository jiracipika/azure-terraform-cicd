# dev foundation values (promotion level 1 of 3 — see infra/pipeline/policy.yaml).
# deploy_enabled stays false until the owner approves deployment (docs/COSTS.md).
deploy_enabled       = false
location             = "canadacentral"
storage_account_name = "sttfstatecicddev01"
replication_type     = "Standard_LRS"
state_retention_days = 14
