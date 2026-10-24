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

output "cuenta_cloud_run" {
  description = "Cuenta de servicio con la que corre el API en Cloud Run"
  value       = google_service_account.api.email
}

output "secreto_database_url" {
  description = "ID del secreto con la DATABASE_URL que lee Cloud Run"
  value       = google_secret_manager_secret.db_url.secret_id
}
