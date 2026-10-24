# Metrica de negocio: el servicio deja un log por cada prediccion evaluada al
# finalizar un partido (app/services/partido.py). Aqui se cuenta, separando
# aciertos de fallos; al venir de Cloud Run lleva tambien la revision, asi se
# compara el desempeño de negocio de la estable contra el del canary.
resource "google_logging_metric" "predicciones_evaluadas" {
  name        = "${replace(var.nombre, "-", "_")}_predicciones_evaluadas"
  description = "Predicciones evaluadas al finalizar un partido, por resultado"
  filter      = "resource.type=\"cloud_run_revision\" AND jsonPayload.evento=\"prediccion_evaluada\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"

    labels {
      key         = "acertada"
      value_type  = "STRING"
      description = "true si el pronostico acerto el ganador o el marcador"
    }
  }

  label_extractors = {
    acertada = "EXTRACT(jsonPayload.acertada)"
  }

  depends_on = [google_project_service.apis]
}
