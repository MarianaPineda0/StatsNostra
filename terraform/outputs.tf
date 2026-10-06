output "ip_api" {
  description = "IP pública estática por la que se accede al API"
  value       = google_compute_address.api.address
}

output "cluster" {
  description = "Nombre del clúster GKE"
  value       = google_container_cluster.api.name
}
