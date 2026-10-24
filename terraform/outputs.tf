output "cluster" {
  description = "Nombre del clúster GKE"
  value       = google_container_cluster.api.name
}

output "redis_host" {
  description = "IP privada de Memorystore Redis"
  value       = google_redis_instance.cache.host
}

output "cloudsql_conexion" {
  description = "Nombre de conexión de Cloud SQL para el proxy"
  value       = google_sql_database_instance.api.connection_name
}

output "repositorio_imagenes" {
  description = "Ruta del repositorio de Artifact Registry donde se sube la imagen"
  value       = "${google_artifact_registry_repository.imagenes.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.imagenes.repository_id}"
}

output "secreto_db" {
  description = "ID del secreto de Secret Manager con la contraseña de la base de datos"
  value       = google_secret_manager_secret.db_password.secret_id
}
