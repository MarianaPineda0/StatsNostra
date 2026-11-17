locals {
  # Filtro comun: solo el servicio del canary. Cada grafico agrupa por
  # revision_name, asi la estable y el canary salen como lineas distintas
  # en el mismo grafico y se comparan a simple vista.
  filtro_servicio = "monitored_resource=\"cloud_run_revision\",service_name=\"${var.servicio_cloud_run}\""

  graficos = [
    {
      titulo   = "Reparto de tráfico (peticiones por segundo)"
      tipo     = "STACKED_AREA"
      consulta = "sum by (revision_name) (rate(run_googleapis_com:request_count{${local.filtro_servicio}}[1m]))"
    },
    {
      titulo = "Errores 5xx (fracción de las peticiones)"
      tipo   = "LINE"
      # El "or ... * 0" mantiene en 0 % a la revision que no tuvo errores; sin
      # el, Prometheus omite la serie y su linea desaparece del grafico
      consulta = join(" / ", [
        "(sum by (revision_name) (rate(run_googleapis_com:request_count{${local.filtro_servicio},response_code_class=\"5xx\"}[1m])) or sum by (revision_name) (rate(run_googleapis_com:request_count{${local.filtro_servicio}}[1m])) * 0)",
        "sum by (revision_name) (rate(run_googleapis_com:request_count{${local.filtro_servicio}}[1m]))",
      ])
    },
    {
      titulo = "Errores 4xx (fracción de las peticiones)"
      tipo   = "LINE"
      # Mismo truco del "or ... * 0" que en los 5xx; los 4xx muestran errores del cliente
      consulta = join(" / ", [
        "(sum by (revision_name) (rate(run_googleapis_com:request_count{${local.filtro_servicio},response_code_class=\"4xx\"}[1m])) or sum by (revision_name) (rate(run_googleapis_com:request_count{${local.filtro_servicio}}[1m])) * 0)",
        "sum by (revision_name) (rate(run_googleapis_com:request_count{${local.filtro_servicio}}[1m]))",
      ])
    },
    {
      titulo   = "Latencia p50 (ms)"
      tipo     = "LINE"
      consulta = "histogram_quantile(0.50, sum by (le, revision_name) (rate(run_googleapis_com:request_latencies_bucket{${local.filtro_servicio}}[2m])))"
    },
    {
      titulo   = "Latencia p95 (ms)"
      tipo     = "LINE"
      consulta = "histogram_quantile(0.95, sum by (le, revision_name) (rate(run_googleapis_com:request_latencies_bucket{${local.filtro_servicio}}[2m])))"
    },
    {
      titulo   = "Latencia p99 (ms)"
      tipo     = "LINE"
      consulta = "histogram_quantile(0.99, sum by (le, revision_name) (rate(run_googleapis_com:request_latencies_bucket{${local.filtro_servicio}}[2m])))"
    },
    {
      titulo   = "Saturación: CPU del contenedor (p95)"
      tipo     = "LINE"
      consulta = "histogram_quantile(0.95, sum by (le, revision_name) (rate(run_googleapis_com:container_cpu_utilizations_bucket{${local.filtro_servicio}}[2m])))"
    },
    {
      titulo   = "Saturación: memoria del contenedor (p95)"
      tipo     = "LINE"
      consulta = "histogram_quantile(0.95, sum by (le, revision_name) (rate(run_googleapis_com:container_memory_utilizations_bucket{${local.filtro_servicio}}[2m])))"
    },
    {
      titulo   = "Negocio: predicciones evaluadas por resultado (por minuto)"
      tipo     = "STACKED_BAR"
      consulta = "sum by (revision_name, acertada) (increase(logging_googleapis_com:user_${google_logging_metric.predicciones_evaluadas.name}{monitored_resource=\"cloud_run_revision\"}[1m]))"
    },
  ]
}

resource "google_monitoring_dashboard" "canary" {
  dashboard_json = jsonencode({
    displayName = "StatsNostra v4: estable contra canary"
    mosaicLayout = {
      columns = 12
      # Dos graficos por fila, cada uno de la mitad del ancho. La API de
      # Monitoring guarda sin xPos/yPos cuando valen 0 y agrega targetAxis;
      # escribirlo igual evita un cambio fantasma en cada plan.
      tiles = [
        for i, grafico in local.graficos : merge(
          { width = 6, height = 4 },
          i % 2 == 1 ? { xPos = 6 } : {},
          i >= 2 ? { yPos = floor(i / 2) * 4 } : {},
          {
            widget = {
              title = grafico.titulo
              xyChart = {
                dataSets = [{
                  timeSeriesQuery = { prometheusQuery = grafico.consulta }
                  plotType        = grafico.tipo
                  targetAxis      = "Y1"
                }]
                yAxis = { scale = "LINEAR" }
              }
            }
          }
        )
      ]
    }
  })

  depends_on = [google_project_service.apis]
}
