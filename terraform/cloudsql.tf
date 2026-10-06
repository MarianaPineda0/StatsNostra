resource "random_id" "sql_sufijo" {
  byte_length = 2
}

resource "google_sql_database_instance" "api" {
  name             = "${var.nombre}-db-${random_id.sql_sufijo.hex}"
  region           = var.region
  database_version = "POSTGRES_16"

  deletion_protection = false

  settings {
    tier              = "db-f1-micro"
    disk_size         = 10
    disk_type         = "PD_HDD"
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled = true
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_sql_user" "api" {
  name     = "statsnostra_app"
  instance = google_sql_database_instance.api.name

  password_wo         = ephemeral.random_password.db.result
  password_wo_version = 1
}

resource "google_sql_database" "api" {
  name     = "statsnostra_v3"
  instance = google_sql_database_instance.api.name
}
