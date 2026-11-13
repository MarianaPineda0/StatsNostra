# IP regional reservada: la URL del API no cambia aunque se recree el Service o
# el clúster, así que el coordinador del grupo la configura una sola vez
resource "google_compute_address" "api" {
  name         = "${var.nombre}-ip"
  region       = var.region
  address_type = "EXTERNAL"

  depends_on = [google_project_service.apis]
}
