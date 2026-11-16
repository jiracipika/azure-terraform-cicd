variable "deploy_enabled" {
  type = bool
  default = false
  description = "Safety gate. No billable resources defined in this starting scaffold."
}
variable "location" {
  type = string
  default = "canadacentral"
}
