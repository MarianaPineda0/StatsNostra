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
    # db-f1-micro admite unas 25 conexiones y con el HPA de la ronda 1 se
    # agotarían y saldrían 500 que no son del código. El g1-small cuesta poco
    # más (~US$1 al día) y aguanta el peor caso.
    tier              = "db-g1-small"
    disk_size         = 10
    disk_type         = "PD_HDD"
    availability_type = "ZONAL"

    # Peor caso: 4 pods x 15 conexiones del pool, más las de la migración
    database_flags {
      name  = "max_connections"
      value = "100"
    }

    # Los pods entran por el Cloud SQL Auth Proxy (sidecar), no hay redes
    # autorizadas: sin el proxy no se puede conectar a la base
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
  password_wo_version = 1
}

resource "google_sql_database" "api" {
  name     = "statsnostra_v5"
  instance = google_sql_database_instance.api.name
}
