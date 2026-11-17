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
  secret_data_wo_version = 2
}

# URL completa de la base para Cloud Run, que entra por el socket de Cloud SQL.
# Se arma aqui con la misma contraseña efímera y la lee Cloud Run como secreto,
# así la contraseña nunca queda en una variable de entorno en claro.
resource "google_secret_manager_secret" "db_url" {
  secret_id = "${var.nombre}-database-url"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# Al rotar, esta versión sube junto con las dos de arriba: las tres deben
# escribirse en el mismo apply para que la contraseña coincida en los tres sitios
resource "google_secret_manager_secret_version" "db_url" {
  secret = google_secret_manager_secret.db_url.id

  secret_data_wo = join("", [
    "postgresql+psycopg://${google_sql_user.api.name}:${ephemeral.random_password.db.result}",
    "@/${google_sql_database.api.name}?host=/cloudsql/${google_sql_database_instance.api.connection_name}",
  ])
  secret_data_wo_version = 2
}

resource "google_secret_manager_secret_iam_member" "api_lee_db_url" {
  secret_id = google_secret_manager_secret.db_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}
