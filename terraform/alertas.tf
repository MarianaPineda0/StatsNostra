locals {
  # Mismo filtro que el dashboard, pero solo las revisiones canary
  filtro_canary = "monitored_resource=\"cloud_run_revision\",service_name=\"${var.servicio_cloud_run}\",revision_name=~\".*canary.*\""
}

# Segunda red de seguridad: la puerta de calidad del pipeline (canary/gate.py)
# ya aborta el despliegue, pero esta alerta queda abierta en Cloud Monitoring
# aunque el pipeline no este corriendo.
resource "google_monitoring_alert_policy" "canary_errores" {
  display_name = "${var.nombre}: errores 5xx del canary por encima del 5 %"
  combiner     = "OR"

  conditions {
    display_name = "5xx del canary superan el 5 % durante 2 minutos"

    condition_prometheus_query_language {
      query = join(" / ", [
        "sum(rate(run_googleapis_com:request_count{${local.filtro_canary},response_code_class=\"5xx\"}[2m]))",
        "sum(rate(run_googleapis_com:request_count{${local.filtro_canary}}[2m])) > 0.05",
      ])
      duration            = "120s"
      evaluation_interval = "60s"
    }
  }

  documentation {
    mime_type = "text/markdown"
    content   = "El canary devuelve mas del 5 % de errores 5xx. Umbral definido en `canary/slo.yaml`. Accion: ejecutar el workflow `Canary v4 · Revertir a la estable` para dejar 0 % de trafico al canary."
  }

  depends_on = [google_project_service.apis]
}

resource "google_monitoring_alert_policy" "canary_latencia" {
  display_name = "${var.nombre}: latencia p95 del canary por encima de 2 s"
  combiner     = "OR"

  conditions {
    display_name = "p95 del canary supera los 2000 ms durante 2 minutos"

    condition_prometheus_query_language {
      query               = "histogram_quantile(0.95, sum by (le) (rate(run_googleapis_com:request_latencies_bucket{${local.filtro_canary}}[2m]))) > 2000"
      duration            = "120s"
      evaluation_interval = "60s"
    }
  }

  documentation {
    mime_type = "text/markdown"
    content   = "La latencia p95 del canary supera el limite de abortar de `canary/slo.yaml`."
  }

  depends_on = [google_project_service.apis]
}
