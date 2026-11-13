resource "google_container_cluster" "api" {
  name     = "${var.nombre}-gke"
  location = var.zone

  # El pool de nodos se define aparte (google_container_node_pool)
  remove_default_node_pool = true
  initial_node_count       = 1

  # Necesario para poder destruir el clúster con terraform destroy
  deletion_protection = false

  network         = google_compute_network.red.id
  subnetwork      = google_compute_subnetwork.nodos.id
  networking_mode = "VPC_NATIVE"

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "servicios"
  }

  # Dataplane V2: es lo que hace cumplir las NetworkPolicy (sin él serían
  # objetos que el clúster acepta pero no aplica) y permite registrar sus
  # decisiones para el experimento de segmentación
  datapath_provider = "ADVANCED_DATAPATH"

  release_channel {
    channel = "REGULAR"
  }

  # Registros de los componentes del sistema y de las cargas: de ahí salen los
  # eventos de auditoría de Kubernetes que alimentan la detección
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  # Prometheus administrado cobra por muestra ingerida; las métricas del
  # clúster que se necesitan ya salen con los componentes del sistema
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]

    managed_prometheus {
      enabled = false
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_container_node_pool" "api" {
  name     = "default-pool"
  cluster  = google_container_cluster.api.name
  location = var.zone

  initial_node_count = 2

  # Dos nodos alcanzan para las 2 réplicas de la ronda 0. El tercero es el
  # margen para la ronda 1: si el HPA pide hasta 4 pods y no caben, el
  # autoscaler del pool agrega un nodo en lugar de dejarlos en Pending
  autoscaling {
    min_node_count = 2
    max_node_count = 3
  }

  node_config {
    machine_type    = "e2-medium"
    disk_size_gb    = 30
    disk_type       = "pd-standard"
    service_account = google_service_account.nodos.email

    # El acceso real lo limitan los roles de la cuenta (cuentas.tf), no el scope
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }

  depends_on = [google_project_iam_member.nodos]
}
