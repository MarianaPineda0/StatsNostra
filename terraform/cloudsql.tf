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
    # GCP crea ENTERPRISE_PLUS por defecto y ahí no existe el tier db-f1-micro
    edition           = "ENTERPRISE"
    tier              = "db-f1-micro"
    disk_size         = 10
    disk_type         = "PD_HDD"
    availability_type = "ZONAL"

    # La app entra por el Cloud SQL Auth Proxy, no hay redes autorizadas
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
