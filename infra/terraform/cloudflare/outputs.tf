# What functions/_middleware.js reads. They are not secrets (the aud is in every Access
# redirect), but they stay out of CI and out of the repository: read them with
# `terraform -chdir=infra/terraform/cloudflare output -raw access_aud` and compare with the
# ACCESS_AUD binding. Terraform never writes the binding (see main.tf).
output "access_aud" {
  description = "Audience of the seller application: the value of ACCESS_AUD."
  value       = cloudflare_zero_trust_access_application.seller.aud
  sensitive   = true
}
