variable "account_id" {
  description = "Cloudflare account id. Not a secret: it is CF_ACCOUNT_ID in the Makefile."
  type        = string
}

variable "project_name" {
  description = "The Cloudflare Pages project (ADR-008 keeps it after the sale)."
  type        = string
  default     = "leaving-denver"
}

variable "owner_email" {
  description = "The one address Cloudflare Access lets into /seller/. Read from data/private.sops.yaml by the Makefile as TF_VAR_owner_email; never written to a file."
  type        = string
  sensitive   = true
}

# The ids of what already exists, found read-only by `make infra-ids` and kept in the
# gitignored ids.auto.tfvars. They are not secrets, but they are this account's, so they
# stay out of a public repository. Used only by imports.tf.
variable "access_idp_id" {
  description = "Id of the account's One-time PIN identity provider."
  type        = string
}

variable "access_app_id" {
  description = "Id of the self-hosted Access application in front of /seller/."
  type        = string
}

variable "access_policy_id" {
  description = "Id of the Allow policy that application uses."
  type        = string
}
