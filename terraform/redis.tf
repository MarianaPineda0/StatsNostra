data "google_compute_network" "default" {
  name = "default"

  depends_on = [google_project_service.apis]
}

resource "google_redis_instance" "cache" {
  name               = "${var.nombre}-redis"
  region             = var.region
  tier               = "BASIC"
  memory_size_gb     = 1
  redis_version      = "REDIS_7_0"
  authorized_network = data.google_compute_network.default.id
  connect_mode       = "DIRECT_PEERING"

  depends_on = [google_project_service.apis]
}
