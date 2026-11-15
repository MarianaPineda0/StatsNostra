"""Arma el informe del experimento (informe-caos-statsnostra.html y .pdf) con la evidencia.

Todas las cifras se calculan aquí a partir de caos/evidencia/ y caos/tablero/datos/; el
texto solo describe. Si se repite una ronda, basta con volver a correr:

    python caos/tablero/dibujar.py
    python caos/informe/arquitectura.py
    python caos/informe/generar_informe.py      (con el Python que tenga PyMuPDF)
"""
import csv
import json
import statistics
from pathlib import Path

import pymupdf

AQUI = Path(__file__).resolve().parent
CAOS = AQUI.parent
EVIDENCIA = CAOS / "evidencia"
DATOS = CAOS / "tablero" / "datos"


def leer(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def n(valor: float) -> str:
    """Miles con punto, como se escribe en español."""
    return f"{valor:,.0f}".replace(",", ".")


def dec(valor: float, cifras: int = 1) -> str:
    return f"{valor:.{cifras}f}".replace(".", ",")


def variacion(nuevo: float, base: float) -> str:
    v = 100 * (nuevo - base) / base
    return f"{'+' if v > 0 else '−'}{dec(abs(v))} %"


# ---- datos ----------------------------------------------------------------------------
estable = leer(EVIDENCIA / "estado-estable" / "estado-estable.json")
X = estable["x_ms"]


def k6(ronda: str) -> dict:
    m = leer(EVIDENCIA / f"ronda-{ronda}" / "corrida-1.json")["metrics"]
    d = m["http_req_duration"]
    return {"p50": d["med"], "p95": d["p(95)"], "p99": d["p(99)"], "max": d["max"], "flujos": m["http_reqs"]["count"],
            "exito": 100 * (1 - m["http_req_failed"]["value"])}


r0, r1 = k6("0"), k6("1")
mediana = estable["mediana"]
flujos_estable = statistics.median(c["peticiones"] for c in estable["detalle"])
pods = leer(DATOS / "resumen-pods.json")
iny = {r: leer(DATOS / f"inyeccion-ronda{r}.json") for r in "01"}


def lag_stats(ronda: str) -> dict:
    saturado = iny[ronda]["pod_saturado"]
    sat, sano = [], []
    for f in csv.DictReader(open(EVIDENCIA / f"ronda-{ronda}" / "lag-pods.csv", encoding="utf-8")):
        if f["lag_ms"] == "NA":
            continue
        (sat if f["pod"] == saturado else sano).append(float(f["lag_ms"]))
    return {"sat_med": statistics.median(sat), "sat_max": max(sat), "sano_med": statistics.median(sano),
            "sat_sobre": sum(v > 50 for v in sat), "sat_n": len(sat),
            "sano_sobre": sum(v > 50 for v in sano), "sano_n": len(sano)}


lag0, lag1 = lag_stats("0"), lag_stats("1")


def cpu_max(ruta: Path, solo_pod: str | None = None) -> float:
    mayor = 0.0
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        for par in linea.split()[1:]:
            pod, valor = par.split("=")
            if solo_pod is None or pod == solo_pod:
                mayor = max(mayor, float(valor.rstrip("m")))
    return mayor


cpu_estable = cpu_max(EVIDENCIA / "estado-estable" / "cpu-pods.txt")
cpu_sat0 = cpu_max(EVIDENCIA / "ronda-0" / "cpu-pods.txt", iny["0"]["pod_saturado"])
cpu_sat1 = cpu_max(EVIDENCIA / "ronda-1" / "cpu-pods.txt", iny["1"]["pod_saturado"])


def segundos_hasta_hpa() -> float:
    from datetime import datetime
    inicio = datetime.fromisoformat(iny["1"]["inicio_utc"].replace("Z", "+00:00"))
    for linea in (EVIDENCIA / "ronda-1" / "cpu-pods.txt").read_text(encoding="utf-8").splitlines():
        partes = linea.split()
        if len(partes) - 1 > 2:
            return (datetime.fromisoformat(partes[0].replace("Z", "+00:00")) - inicio).total_seconds()
    return float("nan")


hpa_s = segundos_hasta_hpa()


def pod_de(ronda: str, rol: str) -> dict:
    return next(p for p in pods[f"ronda{ronda}"]["pods"] if p["rol"] == rol)


sat0, sano0, sat1 = pod_de("0", "saturado"), pod_de("0", "sano"), pod_de("1", "saturado")
sanos1 = [p for p in pods["ronda1"]["pods"] if p["rol"] == "sano"]
reparto = {r: {m["minuto"]: m["parte_saturado"] for m in pods[f"ronda{r}"]["reparto_por_minuto"]} for r in "01"}
traza = pods["traza"]
ruta_corta = lambda r: r.replace("/api/v1/", "")  # noqa: E731

# ---- fragmentos HTML ------------------------------------------------------------------
corridas = "".join(
    f"<tr><td>{c['corrida']}</td><td>{n(c['peticiones'])}</td><td>{dec(100 * c['exito'], 0)} %</td>"
    f"<td>{n(c['p50_ms'])} ms</td><td>{n(c['p95_ms'])} ms</td><td>{n(c['p99_ms'])} ms</td></tr>"
    for c in estable["detalle"])

comparacion = [
    ("Éxito", f"{dec(100 * mediana['exito'], 0)} %", f"{dec(r0['exito'], 0)} %", f"{dec(r1['exito'], 0)} %", "igual"),
    ("p50", f"{n(mediana['p50_ms'])} ms", f"{n(r0['p50'])} ms", f"{n(r1['p50'])} ms", variacion(r1["p50"], r0["p50"])),
    ("p95", f"{n(mediana['p95_ms'])} ms", f"{n(r0['p95'])} ms", f"{n(r1['p95'])} ms", variacion(r1["p95"], r0["p95"])),
    ("p99", f"{n(mediana['p99_ms'])} ms", f"{n(r0['p99'])} ms", f"{n(r1['p99'])} ms", variacion(r1["p99"], r0["p99"])),
    ("Máximo", "sin medir", f"{n(r0['max'])} ms", f"{n(r1['max'])} ms", variacion(r1["max"], r0["max"])),
    ("Flujos completados", n(flujos_estable), n(r0["flujos"]), n(r1["flujos"]), variacion(r1["flujos"], r0["flujos"])),
]
filas_comparacion = "".join(
    f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td>{e}</td></tr>" for a, b, c, d, e in comparacion)

filas_traza = "".join(
    f"<tr><td>{ruta_corta(c0['ruta'])}</td><td>{n(c0['ms'])} ms (pod {c0['rol']})</td>"
    f"<td>{n(c1['ms'])} ms (pod {c1['rol']})</td></tr>"
    for c0, c1 in zip(traza["ronda0"], traza["ronda1"]))

HTML = f"""<html><head><meta charset="utf-8"><title>Agotamiento de CPU en StatsNostra</title>
<style>
body {{ font-family: sans-serif; font-size: 10pt; line-height: 1.35; color: #1c1c1b; }}
h1 {{ font-size: 18pt; margin: 0; color: #0b0b0b; }}
h2 {{ font-size: 12pt; margin: 11pt 0 3pt 0; color: #2a78d6; }}
p {{ margin: 3pt 0 4pt 0; }}
table {{ border-collapse: collapse; margin: 3pt 0 6pt 0; }}
th, td {{ border: 0.5pt solid #b9b8b2; padding: 2.5pt 5pt; font-size: 9pt; }}
th {{ background-color: #eef3f9; text-align: left; }}
.sub {{ color: #52514e; font-size: 10pt; margin: 2pt 0 8pt 0; }}
.tarjeta td {{ border: none; padding: 7pt 9pt; }}
.grande {{ font-size: 22pt; font-weight: bold; }}
.pequeno {{ font-size: 8.5pt; color: #3b3a38; }}
.nota {{ color: #52514e; font-size: 8.5pt; }}
.hipotesis {{ background-color: #eef3f9; padding: 6pt 8pt; }}
</style></head><body>

<h1>Agotamiento de CPU en un pod de StatsNostra</h1>
<p class="sub">Experimento de ingeniería del caos en GKE · 14 de noviembre de 2026</p>

<table class="tarjeta" width="100%"><tr>
<td width="34%" style="background-color:#fdf0ea"><span class="pequeno">Ronda 0, sin mejoras</span><br/>
<span class="grande" style="color:#c2481a">{n(r0['p95'])} ms</span><br/><span class="pequeno">p95 del flujo. Límite aceptado: {n(X)} ms. No se cumple.</span></td>
<td width="34%" style="background-color:#eaf2fc"><span class="pequeno">Ronda 1, con mejoras</span><br/>
<span class="grande" style="color:#1f5fae">{n(r1['p95'])} ms</span><br/><span class="pequeno">p95 del flujo. Se cumple, {dec(abs(100 * (r1['p95'] - r0['p95']) / r0['p95']), 0)} % menos que en la ronda 0.</span></td>
<td width="32%" style="background-color:#f1f1ee"><span class="pequeno">Errores en las dos rondas</span><br/>
<span class="grande">{pods['ronda0']['errores_5xx'] + pods['ronda1']['errores_5xx']}</span><br/><span class="pequeno">El servicio contestó siempre; lo que falló fue la rapidez.</span></td>
</tr></table>

<p>Saturamos durante 3 minutos la CPU de uno de los pods de StatsNostra mientras k6 mandaba carga por el flujo completo: trading-journal en Azure, ecommerce en AWS y StatsNostra en GKE. Queríamos ver si el servicio aguanta que un pod se degrade. Sin cambios no aguantó. Con tres ajustes de configuración, sin tocar el código, sí.</p>
<p><img src="resultados.png" width="505"/></p>
<p><img src="arquitectura.png" width="400"/></p>

<h2>1. Cómo medimos</h2>
<p>El perfil de carga es el mismo en todas las pruebas: 5 usuarios durante 60 s, luego 15 y luego 30, sobre el flujo GET /api/v2/trades/5540 de trading-journal, que llama a StatsNostra y a ecommerce. Antes de inyectar nada lo corrimos tres veces con el sistema sano.</p>
<table><tr><th>Corrida</th><th>Flujos</th><th>Éxito</th><th>p50</th><th>p95</th><th>p99</th></tr>
{corridas}
<tr><th>Mediana</th><th>{dec(mediana["throughput_rps"])} p/s</th><th>{dec(100 * mediana['exito'], 0)} %</th><th>{n(mediana['p50_ms'])} ms</th><th>{n(mediana['p95_ms'])} ms</th><th>{n(mediana['p99_ms'])} ms</th></tr></table>
<p>Con la mediana fijamos el límite en p95 ≤ {n(X)} ms, que es el p95 más un {dec(100 * estable['margen'], 0)} %. Ya en estado estable cada pod llegó a {n(cpu_estable)} m de CPU, por encima de su límite de 250 m, así que partíamos sin holgura.</p>
<p class="hipotesis"><b>Hipótesis.</b> Si la CPU de un pod de StatsNostra llega al 100 % durante 3 minutos, el flujo mantiene una tasa de éxito de al menos 99 % y un p95 de a lo sumo {n(X)} ms.</p>
<table>
<tr><th width="24%">Falla</th><td>Un hilo del pod consume CPU durante 180 s (POST /fault/cpu). Solo funciona con el interruptor de fallos encendido y la cabecera X-Inject-Fault: cpu.</td></tr>
<tr><th>Qué se mide</th><td>p95 y éxito del flujo con k6; además el retraso del bucle de eventos y la CPU de cada pod, y los logs por trace id.</td></tr>
<tr><th>Alcance</th><td>Un solo pod de StatsNostra; el otro no se toca. Tráfico sintético.</td></tr>
<tr><th>Se aborta si</th><td>El éxito baja de 50 %, el p95 pasa de 15 s durante 30 s, o no se puede detener el consumo.</td></tr>
<tr><th>Reversión</th><td>DELETE /fault/cpu en cada pod y apagar el interruptor. Corre siempre al final y se probó antes de la primera ronda. El consumo además se corta solo a los 180 s.</td></tr>
</table>
<p class="nota">El experimento está escrito como código (caos/experimentos/03-agotamiento.json, Chaos Toolkit): una ejecución es una ronda completa. Como reiniciar pods o mandar carga estorba a las mediciones de las otras APIs, cada ronda se hizo en una ventana acordada y las acciones se niegan a correr si llegaron peticiones en los últimos 45 s.</p>

<h2>2. Ronda 0: qué pasó</h2>
<p>El pod saturado no devolvió errores, contestó tarde. Por eso el éxito siguió en 100 % y la sonda de readiness, que solo comprobaba que el proceso respondiera, nunca lo sacó del balanceo.</p>
<p>Lo que atendió ese pod fue lento: p50 de {n(sat0['p50_ms'])} ms y p95 de {n(sat0['p95_ms'])} ms, contra un p95 de {n(sano0['p95_ms'])} ms del pod sano. Su retraso del bucle de eventos pasó de {dec(lag0['sano_med'], 0)} ms a una mediana de {dec(lag0['sat_med'], 0)} ms (máximo {n(lag0['sat_max'])} ms) y su CPU se quedó en el límite de 250 m. La mediana del flujo apenas se movió ({n(r0['p50'])} ms) porque la mitad de las peticiones seguía cayendo en el pod sano; el p95 sube por las que cayeron en el otro.</p>
<p>El trace id {traza['id']} muestra la diferencia con una misma petición lógica (k6 genera el id con el usuario y la iteración, así que se repite en las dos rondas):</p>
<table><tr><th>Llamada a StatsNostra</th><th>Ronda 0</th><th>Ronda 1</th></tr>
{filas_traza}</table>
<p>Las dos rondas, lado a lado (la zona naranja es la ventana de 3 minutos con la CPU saturada):</p>
<p><img src="tablero.png" width="515"/></p>

<h2>3. Qué cambiamos</h2>
<table>
<tr><th width="25%">Cambio</th><th width="33%">Valor</th><th>Por qué</th></tr>
<tr><td>Readiness por saturación</td><td>El pod sale del balanceo si su retraso del bucle pasa de 50 ms. Se revisa cada 5 s y sale tras 2 fallos (antes, 30 s).</td><td>En la ronda 0 el pod saturado superó 50 ms en {lag0['sat_sobre']} de {lag0['sat_n']} muestras y el sano en {lag0['sano_sobre']} de {lag0['sano_n']}.</td></tr>
<tr><td>CPU del pod</td><td>Request 200 m y límite 500 m (antes 100 m y 250 m).</td><td>Con 250 m los pods ya estaban al límite sin ninguna falla.</td></tr>
<tr><td>HPA</td><td>Autoescalado por CPU al 60 %, entre 2 y 4 réplicas.</td><td>Más capacidad cuando un pod rinde menos, en vez de cargar a los demás.</td></tr>
</table>
<p class="nota">Las tres son solo configuración: el código de la API es el mismo en las dos rondas. El umbral de 50 ms sale de los datos de la ronda 0.</p>

<h2>4. Ronda 1</h2>
<p>Mismo perfil, mismo fallo, misma duración, y el pod elegido otra vez el primero de los pods vivos.</p>
<table><tr><th>Métrica</th><th>Estado estable</th><th>Ronda 0</th><th>Ronda 1</th><th>Ronda 1 frente a ronda 0</th></tr>
{filas_comparacion}</table>
<p>El pod saturado siguió consumiendo CPU toda la ventana (se quedó en su límite de 500 m, con picos medidos de {n(cpu_sat1)} m; en la ronda 0 fue el límite de 250 m, con picos de {n(cpu_sat0)} m). Lo que cambió es cuánto tráfico le llegó: {dec(100 * sat1['parte'], 0)} % de las llamadas en la ronda 1 contra {dec(100 * sat0['parte'], 0)} % en la 0. Sus respuestas siguieron siendo más lentas que las de los demás (p95 de {n(sat1['p95_ms'])} ms contra {n(min(p['p95_ms'] for p in sanos1))} a {n(max(p['p95_ms'] for p in sanos1))} ms), pero ya no mandaban sobre la cola. A los {n(hpa_s)} s de empezar la carga el HPA ya había subido el servicio a 4 réplicas.</p>
<p><img src="reparto.png" width="330"/></p>
<p><b>Conclusión.</b> La hipótesis se refuta en la ronda 0 y se cumple en la ronda 1. Con una sola ejecución por ronda y las tres mejoras juntas no podemos decir cuánto aportó cada una, y la ronda 1 además tiene más CPU por pod que la 0. El p95 de k6 incluye la red y las otras dos nubes.</p>

<h2>5. Lo que aprendimos</h2>
<p>Un pod lento no da errores. El éxito y la disponibilidad no lo ven; hay que mirar latencia o saturación.</p>
<p>El primer minuto el pod saturado casi no recibió llamadas en ninguna de las dos rondas ({dec(100 * reparto['0'][0], 0)} % y {dec(100 * reparto['1'][0], 0)} %) y su parte creció al subir los usuarios. No lo verificamos; sospechamos que el coordinador reutiliza conexiones y el balanceador reparte por conexión y no por petición.</p>
<p>El HPA cambia lo que se puede comparar: el nodo extra tardó unos minutos en aparecer y la comprobación del experimento, que exigía exactamente 2 réplicas, marcó la ronda 1 como desviada hasta que la cambiamos a entre 2 y 4.</p>
<p>La ronda 0 se repitió cuatro veces por fallos nuestros en las herramientas: una guarda que se contaba a sí misma, un pod en terminación elegido como objetivo (sin confirmar que el consumo había empezado, el resultado parecía válido y no lo era) y un journal que se cortaba por codificación. Quedaron corregidos en el código.</p>
<p>Riesgo que sigue abierto: si todos los pods se saturaran a la vez, la readiness por saturación dejaría el balanceador sin destinos y la caída sería total.</p>

<h2>Pendiente de resiliencia</h2>
<table><tr><th width="9%">Prioridad</th><th>Qué hacer</th></tr>
<tr><td>Alta</td><td>Límite de concurrencia por pod que responda 503 rápido en lugar de encolar, y tiempos de espera y circuito abierto en las llamadas de trading-journal.</td></tr>
<tr><td>Alta</td><td>Alerta sobre el retraso del bucle y el p95 por pod: hoy esta falla solo se ve mirando el tablero.</td></tr>
<tr><td>Media</td><td>HPA por latencia o peticiones por segundo además de CPU, y nodos de reserva para no esperar a uno nuevo.</td></tr>
<tr><td>Media</td><td>PodDisruptionBudget, clúster regional (hoy es de una sola zona) y varias repeticiones por ronda para tener un intervalo del p95.</td></tr>
<tr><td>Baja</td><td>Enviar las métricas de la API a Grafana Cloud con su service.name y usar este experimento como puerta del pipeline.</td></tr>
</table>
<p class="nota">Cómo reproducir todo, las gráficas y los datos: caos/README.md y caos/tablero/README.md.</p>
</body></html>
"""

(AQUI / "informe-caos-statsnostra.html").write_text(HTML, encoding="utf-8")

archivo = pymupdf.Archive(str(AQUI))
archivo.add(str(CAOS / "tablero"))
historia = pymupdf.Story(html=HTML, archive=archivo)
salida = AQUI / "informe-caos-statsnostra.pdf"
escritor = pymupdf.DocumentWriter(str(salida))
pagina = pymupdf.paper_rect("a4")
zona = pagina + (40, 36, -40, -36)
hay_mas = True
while hay_mas:
    dispositivo = escritor.begin_page(pagina)
    hay_mas, _ = historia.place(zona)
    historia.draw(dispositivo)
    escritor.end_page()
escritor.close()
print("páginas:", pymupdf.open(str(salida)).page_count)
