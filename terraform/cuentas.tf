# Cuenta propia para los nodos, con solo lo que necesitan. La cuenta de Compute
# que usa GKE por defecto tiene rol de Editor sobre todo el proyecto, y cualquier
# pod comprometido heredaría ese alcance.
resource "google_service_account" "nodos" {
  account_id   = "${var.nombre}-nodos"
  display_name = "Nodos de GKE ${var.nombre}"

  depends_on = [google_project_service.apis]
}

locals {
  roles_nodos = [
    # Mínimo que GKE documenta para los nodos
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceMetadata.writer",
    # Bajar la imagen del API desde Artifact Registry
    "roles/artifactregistry.reader",
    # El proxy de Cloud SQL corre como sidecar y usa la cuenta del nodo
    "roles/cloudsql.client",
  ]
}

resource "google_project_iam_member" "nodos" {
  for_each = toset(local.roles_nodos)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.nodos.email}"
}
