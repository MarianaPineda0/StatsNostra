resource "google_container_cluster" "api" {
  name     = "${var.nombre}-gke"
  location = var.zone

  # El pool de nodos se define aparte (google_container_node_pool)
  remove_default_node_pool = true
  initial_node_count       = 1

  # Necesario para poder destruir el clúster con terraform destroy
  deletion_protection = false

  release_channel {
    channel = "REGULAR"
  }

  depends_on = [google_project_service.apis]
}
