resource "google_artifact_registry_repository" "imagenes" {
  location      = var.region
  repository_id = "${var.nombre}-repo"
  description   = "Imágenes del API de StatsNostra"
  format        = "DOCKER"

  depends_on = [google_project_service.apis]
}
