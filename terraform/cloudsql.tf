# El nombre de una instancia borrada no se puede reutilizar por varios días
resource "random_id" "sql_sufijo" {
  byte_length = 2
}

resource "google_sql_database_instance" "api" {
  name             = "${var.nombre}-db-${random_id.sql_sufijo.hex}"
  region           = var.region
  database_version = "POSTGRES_16"

  # Permite borrarla con terraform destroy
  deletion_protection = false

  settings {
    # GCP crea ENTERPRISE_PLUS por defecto y ahí no existe este tipo de tier
    edition = "ENTERPRISE"
    # db-f1-micro solo admite unas 25 conexiones: con dos revisiones de Cloud
    # Run bajo carga se agotaban y salian 500 que no eran del codigo. El
    # g1-small cuesta poco mas (~US$1 al dia) y aguanta el peor caso.
    tier              = "db-g1-small"
    disk_size         = 10
    disk_type         = "PD_HDD"
    availability_type = "ZONAL"

    # Peor caso: 2 revisiones x 3 instancias x 15 conexiones del pool = 90
    database_flags {
      name  = "max_connections"
      value = "100"
    }

    # Cloud Run entra por el socket de Cloud SQL (--add-cloudsql-instances),
    # sin redes autorizadas
    ip_configuration {
      ipv4_enabled = true
    }
  }

  depends_on = [google_project_service.apis]
}

# password_wo: la contraseña (secretos.tf) no se guarda en el estado
resource "google_sql_user" "api" {
  name     = "statsnostra_app"
  instance = google_sql_database_instance.api.name

  password_wo         = ephemeral.random_password.db.result
  password_wo_version = 2
}

resource "google_sql_database" "api" {
  name     = "statsnostra_v4"
  instance = google_sql_database_instance.api.name
}
