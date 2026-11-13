# Ingeniería del caos: API de Mari en GKE

Experimento de agotamiento de recursos sobre la API de StatsNostra, que corre en
GKE con 2 réplicas. La pregunta que responde: **si la CPU de un pod llega al
100 %, ¿el flujo se mantiene rápido y disponible?**

## Qué hay aquí

| Archivo | Para qué sirve |
|---|---|
| `experimentos/03-agotamiento.json` | El experimento como código (Chaos Toolkit): estado estable, hipótesis, método, radio de impacto, abortos y reversión |
| `acciones/cpu.sh` | Enciende y apaga el interruptor, satura la CPU de un pod y la detiene; se niega a reiniciar si hay tráfico |
| `acciones/muestrear.sh` | Registra el consumo y el retraso del bucle de cada pod durante una ronda |
| `carga/perfil.js` | El perfil de carga fijo de k6, el mismo en todas las rondas |
| `carga/correr.sh` | Corre una vez el perfil con Docker y guarda la evidencia |
| `carga/serie.sh` | Corre una serie de corridas con su entorno y su muestreo (estado estable) |
| `carga/resumen.py` | Declara el estado estable con la mediana de las corridas |
| `carga/veredicto.py` | Compara una ronda con el estado estable y dice si la hipótesis se cumple |
| `evidencia/` | Resultados medidos: estado estable y, a medida que se hacen, cada ronda |

## El experimento

- **Fallo:** saturar la CPU de **un** pod durante 3 minutos. El otro no se toca.
- **Hipótesis:** con el perfil de carga fijo del grupo (k6: 5, 15 y 30 usuarios de
  60 s cada uno), el flujo mantiene una tasa de éxito ≥ 99 % y un p95 ≤ X ms.
  X es el p95 del estado estable medido más un 25 % de margen; mientras no se
  mida, `x_ms` queda en `null` en el JSON.
- **Radio de impacto:** un pod de `statsnostra-api` y tráfico sintético de k6.
- **Abortos:** éxito del flujo < 50 %, p95 > 15 000 ms durante 30 s, o cualquier
  error al intentar detener el consumo.
- **Cómo se inyecta:** el API trae un endpoint `/fault/cpu` que solo existe con
  `FAULT_HEADER_ENABLED=true` y exige la cabecera `X-Inject-Fault: cpu`. Se llama
  a un pod concreto por `kubectl port-forward`, porque el balanceador repartiría
  entre las dos réplicas y no se saturaría solo una.

## Estado estable medido

Antes de inyectar nada se mide cómo se comporta el flujo sano: tres corridas del
perfil fijo, una tras otra, con los mismos recursos y sin ningún experimento activo.
La evidencia está en `evidencia/estado-estable/` (resumen de k6 y hora de cada
corrida, consumo de los pods y la instantánea del entorno).

| Corrida | Peticiones | Éxito | p50 | p95 | p99 |
|---|---|---|---|---|---|
| 1 | 3.693 | 100 % | 418 ms | 1.208 ms | 1.714 ms |
| 2 | 3.634 | 100 % | 450 ms | 1.200 ms | 1.594 ms |
| 3 | 3.324 | 100 % | 450 ms | 1.479 ms | 1.934 ms |

**Estado estable declarado:** éxito >= 99 % y p95 <= **1.511 ms** (mediana del p95,
1.208 ms, más un 25 % de margen). Las tres corridas se hicieron con la imagen
`1a39510`, 2 réplicas con requests de 100 m y límites de 250 m de CPU, sin HPA y
con el interruptor de fallos apagado. Se comprobó en los logs que llegaron
exactamente las peticiones de k6 y ninguna ajena.

Un dato que condiciona todo lo demás: ya en estado estable cada pod llega a unos
310 m de CPU con un límite de 250 m, es decir, el flujo sano ya trabaja limitado por
CPU.

Se repite con el mismo protocolo en las rondas 0 y 1:

```bash
P95_MAX_MS=1511 bash caos/carga/serie.sh caos/evidencia/CARPETA
```

## Cómo se corre una ronda

Una sola ejecución del experimento hace toda la ronda: enciende el interruptor,
arranca el muestreo de los pods, lanza k6, satura la CPU de un pod mientras corre
la carga, espera el resultado, emite el veredicto contra el estado estable y revierte.

**Antes de empezar** (todo debe cumplirse, si no, no se corre):

1. La ventana está anunciada al grupo, con hora de inicio y de fin, y nadie más
   corre carga ni reinicia nada mientras dura (unos 10 minutos).
2. El código desplegado es el mismo de la ronda anterior: entre la ronda 0 y la 1
   solo cambia la configuración o los manifiestos, no el código.
3. `kubectl` apunta al clúster, Docker está abierto y el equipo no se suspende:

```bash
gcloud container clusters get-credentials statsnostra-v5-gke --zone us-central1-a
bash caos/acciones/cpu.sh trafico     # debe decir 0 peticiones
```

**Ronda 0:**

```bash
chaos run --rollback-strategy always   --journal-path caos/evidencia/ronda-0/journal.json   caos/experimentos/03-agotamiento.json
```

**Ronda 1** (mismo perfil, mismo fallo, misma duración; solo cambia la carpeta):

```bash
chaos run --rollback-strategy always --var carpeta=caos/evidencia/ronda-1   --journal-path caos/evidencia/ronda-1/journal.json   caos/experimentos/03-agotamiento.json
```

`--rollback-strategy always` garantiza que la reversión corra aunque algo falle a
mitad. La carpeta de cada ronda queda con el diario del experimento, el resumen de
k6 (`corrida-1.json`), el retraso del bucle de cada pod (`lag-pods.csv`) y su
consumo de CPU (`cpu-pods.txt`). Que la ronda refute la hipótesis no es un error: el
veredicto queda en el diario con el motivo y la distancia a X.

## Parada y reversión

Cualquiera de estas cosas deja el sistema como estaba:

| Qué | Cómo |
|---|---|
| Detener el consumo ya | `bash caos/acciones/cpu.sh detener` |
| Parada de emergencia | `bash caos/acciones/cpu.sh deshabilitar` (apaga el interruptor y reinicia los pods; nunca se bloquea) |
| Ver el estado | `bash caos/acciones/cpu.sh estado` |

Además, el consumo se detiene solo al cumplirse el plazo (180 s, tope de 600 s) y
reiniciar un pod lo limpia.

## Reglas para no pisar las mediciones

- `cpu.sh habilitar` reinicia los pods, así que **se niega a correr si hubo
  peticiones en los últimos 45 s**. Si es a propósito: `FORZAR=1`.
- Con el interruptor apagado (lo normal), `/fault/cpu` no existe y responde 404.
- El interruptor queda encendido solo durante la ventana del experimento.
