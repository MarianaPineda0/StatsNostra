# La contraseña de la base de datos es un recurso efímero: Terraform la genera
# en memoria durante el apply y no la guarda en el archivo de estado.
ephemeral "random_password" "db" {
  length = 24
  # Sin caracteres especiales para no tener que codificarlos en la DATABASE_URL
  special = false
}

# Contenedor del secreto. El valor real vive en la versión de abajo.
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.nombre}-db-password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# secret_data_wo es write-only: se envía a Secret Manager pero no queda en el estado.
# Para rotar la contraseña se sube el número de secret_data_wo_version (y el de
# password_wo_version del usuario en cloudsql.tf).
resource "google_secret_manager_secret_version" "db_password" {
  secret = google_secret_manager_secret.db_password.id

  secret_data_wo         = ephemeral.random_password.db.result
  secret_data_wo_version = 1
}
