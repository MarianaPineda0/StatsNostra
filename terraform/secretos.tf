resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.nombre}-db-password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}
