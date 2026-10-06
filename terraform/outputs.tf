output "ip_api" {
  description = "IP pública estática por la que se accede al API"
  value       = google_compute_address.api.address
}

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
