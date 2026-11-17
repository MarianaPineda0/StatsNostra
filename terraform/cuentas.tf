# Cuenta con la que corre el API en Cloud Run. Se le da solo lo que necesita:
# conectarse a Cloud SQL y leer el secreto con la URL de la base (secretos.tf).
resource "google_service_account" "api" {
  account_id   = "${var.nombre}-run"
  display_name = "API ${var.nombre} en Cloud Run"

  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}
