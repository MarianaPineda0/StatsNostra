# Red propia en lugar de la "default": solo en una subred que Terraform controla
# se pueden activar los registros de flujo, que son la señal de red del
# experimento de exposición y segmentación.
resource "google_compute_network" "red" {
  name                    = "${var.nombre}-red"
  auto_create_subnetworks = false

  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "nodos" {
  name          = "${var.nombre}-nodos"
  region        = var.region
  network       = google_compute_network.red.id
  ip_cidr_range = "10.10.0.0/24"

  # GKE en modo VPC nativo: los pods y los servicios salen de rangos propios
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.20.0.0/16"
  }

  secondary_ip_range {
    range_name    = "servicios"
    ip_cidr_range = "10.30.0.0/20"
  }

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}
