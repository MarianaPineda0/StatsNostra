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

resource "google_container_node_pool" "api" {
  name       = "default-pool"
  cluster    = google_container_cluster.api.name
  location   = var.zone
  node_count = 2

  node_config {
    machine_type = "e2-medium"
    disk_size_gb = 30
    disk_type    = "pd-standard"

    # Permite que los pods (proxy de Cloud SQL, imágenes) usen la cuenta de los nodos
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }
}
