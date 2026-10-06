resource "google_compute_address" "api" {
  name         = "${var.nombre}-ip"
  region       = var.region
  address_type = "EXTERNAL"

  depends_on = [google_project_service.apis]
}
