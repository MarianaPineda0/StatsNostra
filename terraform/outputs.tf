output "ip_api" {
  description = "IP pública estática por la que se accede al API (puerto 80)"
  value       = google_compute_address.api.address
}

output "cluster" {
  description = "Nombre del clúster GKE"
  value       = google_container_cluster.api.name
}

output "zona" {
  description = "Zona del clúster, para get-credentials"
  value       = var.zone
}

output "cloudsql_conexion" {
  description = "Nombre de conexión de Cloud SQL para el proxy"
  value       = google_sql_database_instance.api.connection_name
}

output "repositorio_imagenes" {
  description = "Ruta del repositorio de Artifact Registry donde se sube la imagen"
  value       = "${google_artifact_registry_repository.imagenes.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.imagenes.repository_id}"
}

output "secreto_database_url" {
  description = "ID del secreto con la URL completa de la base de datos"
  value       = google_secret_manager_secret.db_url.secret_id
}

output "cuenta_nodos" {
  description = "Cuenta de servicio de los nodos del clúster"
  value       = google_service_account.nodos.email
}
