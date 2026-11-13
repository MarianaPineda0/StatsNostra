# Ingeniería del caos: API de Mari en GKE

Experimento de agotamiento de recursos sobre la API de StatsNostra, que corre en
GKE con 2 réplicas. La pregunta que responde: **si la CPU de un pod llega al
100 %, ¿el flujo se mantiene rápido y disponible?**

## Qué hay aquí

| Archivo | Para qué sirve |
|---|---|
| `experimentos/03-agotamiento.json` | El experimento como código (Chaos Toolkit): estado estable, hipótesis, método, radio de impacto, abortos y reversión |
| `acciones/cpu.sh` | Los comandos que inyectan el fallo y lo revierten; los usa el experimento y se pueden correr a mano |

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

## Cómo se corre

Desde la raíz del repositorio, con `kubectl` apuntando al clúster:

```bash
gcloud container clusters get-credentials statsnostra-v5-gke --zone us-central1-a
```

1. **Avisar la ventana al grupo** (hora de inicio y de fin). Nadie más corre carga
   ni reinicia nada mientras dura.
2. Arrancar el perfil de k6 del grupo, en paralelo.
3. Correr el experimento:

```bash
chaos run caos/experimentos/03-agotamiento.json
```

El experimento enciende el interruptor, satura la CPU de un pod, deja pasar la
ventana de 3 minutos y, al terminar o si algo falla, revierte solo.

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
