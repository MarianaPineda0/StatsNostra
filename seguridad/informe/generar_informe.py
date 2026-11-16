"""Arma el informe de seguridad (informe-seguridad-statsnostra.html y .pdf) con la evidencia.

Las cifras salen de seguridad/evidencia/, de la bitácora, del inventario y de los casos de prueba
de detección; el texto solo las describe. El PDF se imprime con Edge o Chrome sin interfaz.

    python seguridad/informe/dibujar.py
    python seguridad/informe/generar_informe.py
"""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SEGURIDAD = AQUI.parent
EVIDENCIA = SEGURIDAD / "evidencia"
T1_S, T2_S = 300, 600


def cargar(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def seg(inicio: str, fin: str) -> float:
    a = datetime.fromisoformat(inicio.replace("Z", "+00:00"))
    b = datetime.fromisoformat(fin.replace("Z", "+00:00"))
    return (b - a).total_seconds()


base = cargar(EVIDENCIA / "linea-base" / "medicion.json")
r0 = cargar(EVIDENCIA / "ronda-0" / "resultado.json")
r1 = cargar(EVIDENCIA / "ronda-1" / "resultado.json")
senuelo = cargar(EVIDENCIA / "honeytoken" / "resultado.json")
antes = {
    c["cuenta"].split("@")[0]: c for c in cargar(EVIDENCIA / "identidades" / "antes.json")
}
despues = {
    c["cuenta"].split("@")[0]: c for c in cargar(EVIDENCIA / "identidades" / "despues.json")
}
ci_antes, ci_despues = antes["statsnostra-ci"], despues["statsnostra-ci"]

mttd1 = seg(r1["creacion_utc"], r1["alerta"])
mttc1 = seg(r1["alerta"], r1["contencion_utc"])
mttd_senuelo = seg(senuelo["apertura_utc"], senuelo["alerta_utc"])
casos = list((SEGURIDAD / "deteccion" / "casos").glob("*.json"))
positivos = [c for c in casos if "positivo" in c.name and "negativo" not in c.name]
negativos = [c for c in casos if "negativo" in c.name]

# Cobertura por capa, contada en el inventario de controles
inventario = (SEGURIDAD / "inventario-controles.md").read_text(encoding="utf-8")
capas = {}
for bloque in re.split(r"^## ", inventario, flags=re.M)[1:]:
    titulo = bloque.splitlines()[0].strip()
    if titulo == "Cómo se usa":
        continue
    cerrados = bloque.count("cerrado el 15 nov")
    capas[titulo] = (bloque.count("| Activo") - cerrados, cerrados, bloque.count("**Hueco**"))
filas_capas = "".join(
    f"<tr><td>{c}</td><td>{a}</td><td>{k}</td><td>{h}</td></tr>"
    for c, (a, k, h) in capas.items()
)
total_activos = sum(a for a, _, _ in capas.values())
total_cerrados = sum(k for _, k, _ in capas.values())
total_huecos = sum(h for _, _, h in capas.values())

# Bitácora: las filas de cada ronda, con la hora de Colombia
filas_bitacora = []
for linea in (SEGURIDAD / "bitacora.md").read_text(encoding="utf-8").splitlines():
    m = re.match(r"\|\s*(\d\d:\d\d:\d\d)\s*\|[^|]*\|([^|]*)\|([^|]*)\|", linea)
    if m:
        filas_bitacora.append((m[1], m[2].strip(), m[3].strip()))
n_acciones = len(filas_bitacora)


def cronologia_ronda(n: int) -> str:
    filas = [f for f in filas_bitacora if f[1].startswith(f"Ronda {n}")]
    return "".join(
        f"<tr><td>{h}</td><td>{a.replace(f'Ronda {n}, ', '').replace(f'Ronda {n}: ', '')}</td><td>{r}</td></tr>"
        for h, a, r in filas
    )


def s(valor: float) -> str:
    return f"{valor:.0f} s"


html = f"""<html><head><meta charset="utf-8"><title>Caos de seguridad en StatsNostra</title>
<style>
@page {{ size: A4; margin: 15mm 16mm; }}
body {{ font-family: "Times New Roman", Times, serif; font-size: 11.5pt; line-height: 1.4; color: #1b2437; margin: 0; }}
h1 {{ font-size: 24pt; margin: 0 0 2pt 0; color: #14213d; line-height: 1.15; }}
h2 {{ font-size: 15pt; margin: 16pt 0 5pt 0; color: #1f5fae; break-after: avoid; }}
p {{ margin: 4pt 0 6pt 0; }}
img {{ display: block; margin: 6pt auto; max-width: 100%; break-inside: avoid; }}
table {{ border-collapse: collapse; margin: 5pt 0 9pt 0; width: 100%; break-inside: avoid; }}
th, td {{ border: 0.6pt solid #c3cad6; padding: 3.5pt 6pt; font-size: 10.5pt; text-align: left; vertical-align: top; }}
th {{ background-color: #eaf1fb; color: #14213d; }}
.sub {{ color: #4b5563; font-size: 12pt; margin: 0 0 10pt 0; }}
.tarjetas {{ border: none; margin: 0 0 8pt 0; border-spacing: 8pt 0; border-collapse: separate; }}
.tarjetas td {{ border: none; border-radius: 6pt; padding: 9pt 11pt; width: 33%; }}
.grande {{ font-size: 26pt; font-weight: bold; line-height: 1.1; }}
.pequeno {{ font-size: 10pt; color: #374151; }}
.nota {{ color: #4b5563; font-size: 10pt; }}
.hipotesis {{ background-color: #eaf1fb; border-left: 4pt solid #3b8eea; padding: 7pt 10pt; margin: 8pt 0; }}
</style></head><body>

<h1>Exposición y segmentación en StatsNostra</h1>
<p class="sub">Experimento de caos de seguridad (defensa en profundidad) en GKE · 15 de noviembre de 2026</p>

<table class="tarjetas"><tr>
<td style="background-color:#f3ecf8"><span class="pequeno">Ronda 0, sin mejoras</span><br/>
<span class="grande" style="color:#5b2a86">sin alerta</span><br/><span class="pequeno">El Service expuesto no avisó a nadie. El salto entre namespaces y la salida a Internet pasaron.</span></td>
<td style="background-color:#e6f6ed"><span class="pequeno">Ronda 1, alerta y NetworkPolicy</span><br/>
<span class="grande" style="color:#0b7a3b">{s(mttd1)}</span><br/><span class="pequeno">hasta la alerta; {s(mttc1)} después se contuvo. Salto y salida, bloqueados.</span></td>
<td style="background-color:#e8f1fd"><span class="pequeno">Credencial señuelo</span><br/>
<span class="grande" style="color:#1f5fae">{s(mttd_senuelo)}</span><br/><span class="pequeno">desde que alguien abre el secreto hasta que suena la alerta.</span></td>
</tr></table>

<p>Nos preguntamos qué pasa si aparece una ruta que nadie declaró dentro del clúster de StatsNostra, y cuánto tardamos en verla y cerrarla. Tal como estaba, no pasaba nada: ninguna regla miraba la creación de Services. Con una alerta basada en logs y una NetworkPolicy de denegación por defecto, el aviso llegó en {s(mttd1)} y las otras dos rutas quedaron cerradas.</p>

<h2>1. Qué probamos y con qué reglas</h2>
<p>Tres rutas no declaradas, inyectadas a la vez: (A) un Service que expone el puerto de administración (el 9090 del Cloud SQL Auth Proxy), (B) un pod de otro namespace que llama a la API, y (C) un pod que sale a Internet sin filtro. Las dos últimas usan un pod de prueba en un namespace aparte (caos-seguridad).</p>
<p class="hipotesis"><b>Hipótesis de control.</b> Con la red tal como está hoy, cuando se cree un Service que exponga el puerto de administración, esperamos una alerta en {T1_S // 60} minutos o menos y su eliminación en {T2_S // 60} minutos o menos.</p>
<table>
<tr><th style="width:22%">Regla de compromiso</th><th>Valor acordado por las tres APIs</th></tr>
<tr><td>Alcance</td><td>Solo cuentas y proyectos del grupo (aquí, el proyecto de Google Cloud de StatsNostra). Nada de terceros, de la Universidad ni de otros grupos.</td></tr>
<tr><td>Datos</td><td>Solo sintéticos.</td></tr>
<tr><td>Radio de impacto</td><td>Un Service de prueba, un namespace de prueba con un pod y una NetworkPolicy. No se tocan el Service público, el Deployment ni los pods de la API. Máximo 10 peticiones por prueba.</td></tr>
<tr><td>Parada y reversión</td><td>Tres comandos de kubectl que borran lo creado; se verifican con el estado de Services, políticas y /health/ready. La reversión se probó antes de la ronda 0.</td></tr>
<tr><td>Aborto</td><td>/health/ready sin responder 200 durante más de 60 s, falla del flujo completo, algo fuera del alcance, fin de la ventana, o cualquiera de las APIs pidiendo parar.</td></tr>
<tr><td>Bitácora</td><td>{n_acciones} acciones con hora, responsable y resultado en bitacora.md.</td></tr>
</table>

<h2>2. Estado estable de seguridad</h2>
<p>El inventario de controles de StatsNostra cuenta {total_activos + total_cerrados} controles activos y {total_huecos} huecos abiertos en cinco capas; {total_cerrados} de esos controles se activaron durante este trabajo. Los huecos de partida eran los que explican la ronda 0: no había NetworkPolicy, ni filtrado de salida, ni alerta sobre Services.</p>
<p><img src="capas.png" style="width:86%"/></p>
<table><tr><th>Capa</th><th>Activos desde el inicio</th><th>Cerrados en este trabajo</th><th>Huecos abiertos</th></tr>
{filas_capas}</table>
<p>Línea base de la señal: con un Service inofensivo, el evento de creación se pudo consultar en Cloud Logging a los {base['segundos_hasta_consultar']} s. Es el piso de cualquier detección que se apoye en esos registros.</p>

<h2>3. Cronología</h2>
<p>Las dos rondas se hicieron el domingo 15 de noviembre con la ventana acordada en el grupo. Cada una crea el Service a la vez que lanza B y C, mide cuándo se puede consultar el evento, espera la alerta y contiene.</p>
<p><img src="cronologia.png" style="width:100%"/></p>
<table style="break-inside: auto"><tr><th>Hora (Colombia)</th><th>Ronda 0</th><th>Resultado</th></tr>
{cronologia_ronda(0)}</table>
<table style="break-inside: auto"><tr><th>Hora (Colombia)</th><th>Ronda 1</th><th>Resultado</th></tr>
{cronologia_ronda(1)}</table>
<p class="nota">En la ronda 0 la contención a los {r0['segundos_hasta_contencion']} s la hizo quien operaba el experimento, que ya sabía del evento; no cuenta como MTTC porque nadie recibió una alerta.</p>

<div style="break-inside: avoid"><h2>4. Resultados de las dos rondas</h2>
<p><img src="resultados.png" style="width:64%"/></p></div>
<table><tr><th></th><th>Ronda 0</th><th>Ronda 1</th></tr>
<tr><td>MTTD (de la creación a la alerta)</td><td>no se detectó</td><td>{s(mttd1)}</td></tr>
<tr><td>MTTC (de la alerta a la contención)</td><td>sin alerta no hubo quién contuviera</td><td>{s(mttc1)}</td></tr>
<tr><td>Evento consultable en Cloud Logging</td><td>{r0['senal_en_logs'].split()[0]} s</td><td>{r1['senal_en_logs'].split()[0]} s</td></tr>
<tr><td>Cobertura de la alerta</td><td>0 de 3 inyecciones</td><td>1 de 3 (la A)</td></tr>
<tr><td>Falsos positivos</td><td>sin alerta que pudiera darlos</td><td>0: la única alerta fue la del Service inyectado</td></tr>
<tr><td>Hipótesis (alerta en {T1_S // 60} min, contención en {T2_S // 60} min)</td><td>se refuta: no hay alerta</td><td>se cumple</td></tr>
</table>
<p>El NodePort quedó sin respuesta desde fuera de la red en las dos rondas, porque el firewall de la red del clúster solo deja pasar el puerto 80 al balanceador. La B y la C se cerraron con la política: la B falló ya en la resolución de nombres, así que para aislar la política de entrada de la API quitamos la del namespace de prueba y llamamos a la API por su ClusterIP; siguió bloqueada. Con las políticas puestas, el flujo completo por el coordinador siguió dando 200 y las dos réplicas quedaron listas.</p>

<h2>5. Mejoras y detección como código</h2>
<table><tr><th style="width:26%">Mejora</th><th>Qué es</th></tr>
<tr><td>Alerta de Services expuestos</td><td>Política de Cloud Monitoring sobre el registro de auditoría de Kubernetes: avisa cuando se crea un Service NodePort o LoadBalancer distinto del público. La notificación llega a un tema de Pub/Sub, de donde se lee la hora real de la alerta.</td></tr>
<tr><td>NetworkPolicy</td><td>Denegación por defecto de entrada y salida, entrada a la API solo por su puerto, y salida solo a DNS, metadatos, la API de Cloud SQL (443) y la base (3307). Se aplicó en la ronda 1 y se revirtió al terminar.</td></tr>
</table>
<p>Las reglas son código versionado (seguridad/deteccion/reglas.py): de una sola definición salen el filtro de Cloud Logging y la evaluación de los casos de prueba. Hay {len(positivos)} casos positivos y {len(negativos)} negativos, que incluyen el flujo normal del despliegue, y corren con el resto de las pruebas en cada push.</p>

<h2>6. Tendencias verificables</h2>
<p><b>Credencial señuelo.</b> Un secreto que ninguna aplicación usa (statsnostra-admin-respaldo, con un valor sintético) y que dispara una alerta al abrirse. Para verlo hubo que habilitar los registros de lectura de datos de Secret Manager, que antes no estaban. Abrirlo avisó a los {s(mttd_senuelo)}; mirar sus metadatos sin abrirlo no avisó. Referencias: MITRE D3FEND, técnica D3-DUC (Decoy User Credential), y ATT&CK T1552 (Unsecured Credentials), consultadas el 15 de noviembre de 2026; documentación de registros de auditoría de Secret Manager de Google Cloud, consultada el 15 de noviembre de 2026.</p>
<p><b>Identidades de máquina con mínimo privilegio.</b> Se inventariaron las {len(antes)} cuentas de servicio del proyecto: ninguna tiene llaves creadas por el usuario. La cuenta que usa GitHub Actions para desplegar tenía {len(ci_antes['roles'])} roles, {len(ci_antes['roles_admin'])} de ellos de administración, heredados de entregas anteriores. Se redujo a {len(ci_despues['roles'])} roles (uno de administración, el de GKE) más permiso de lectura sobre un solo secreto, y cada operación del despliegue se probó suplantando a la cuenta antes de dar el cambio por bueno. Referencia: guía de prácticas recomendadas para cuentas de servicio de Google Cloud (privilegio mínimo y evitar las llaves de cuenta de servicio), consultada el 15 de noviembre de 2026.</p>
<p><img src="identidades.png" style="width:54%"/></p>

<h2>7. Lecciones, riesgos y lo que sigue</h2>
<p>La alerta cubre una de las tres rutas: la B y la C se previenen con la política, pero no dejan una señal propia. Habilitar los registros de lectura de datos agrega volumen de logs; si crece, hay que acotarlo. Los resultados vienen de una sola ejecución por ronda. La NetworkPolicy quedó revertida: hay que decidir si pasa a ser parte del despliegue, y eso reinicia pods. Y la cuenta del despliegue sigue con permisos de administración de GKE, porque el despliegue crea recursos de varios tipos.</p>
<p>Próximos experimentos: una alerta sobre los flujos denegados de la red para cubrir la B y la C, y dejar la NetworkPolicy en el despliegue con una prueba que verifique el flujo completo antes de fusionarla.</p>
<p class="nota">Cómo reproducir: seguridad/README.md. Las gráficas salen de seguridad/evidencia/ con seguridad/informe/dibujar.py.</p>
</body></html>
"""

CSS = html[html.index("<style>") : html.index("</style>") + len("</style>")]
TARJETAS = html[
    html.index('<table class="tarjetas">') : html.index("</table>") + len("</table>")
]

seccion = f"""<html><head><meta charset="utf-8"><title>StatsNostra: sección del informe de seguridad</title>
{CSS}
</head><body>
<h1 style="font-size: 20pt">StatsNostra: exposición y segmentación</h1>
<p class="sub">Sección del informe de seguridad (defensa en profundidad) · API StatsNostra en GKE</p>
{TARJETAS}

<h2>Hipótesis, reglas y estado estable</h2>
<p class="hipotesis"><b>Hipótesis de control.</b> Con la red tal como está hoy, cuando se cree un Service que exponga el puerto de administración, esperamos una alerta en {T1_S // 60} minutos o menos y su eliminación en {T2_S // 60} minutos o menos. Se inyectan tres rutas no declaradas a la vez: (A) el Service expuesto, (B) un pod de otro namespace que llama a la API y (C) un pod que sale a Internet sin filtro.</p>
<p>Reglas de compromiso aceptadas por las tres APIs: solo cuentas del grupo y datos sintéticos; radio de un Service de prueba, un namespace de prueba y una NetworkPolicy; parada y reversión con tres comandos de kubectl, probados antes de la ronda 0; aborto si /health/ready no responde 200 durante más de 60 s. Las {n_acciones} acciones quedaron en la bitácora.</p>
<p>El inventario de controles cuenta {total_activos + total_cerrados} activos y {total_huecos} huecos abiertos en cinco capas; {total_cerrados} se activaron durante este trabajo. La línea base de la señal: el evento de creación de un Service se pudo consultar en Cloud Logging a los {base['segundos_hasta_consultar']} s.</p>
<p><img src="capas.png" style="width:80%"/></p>

<h2>Cronología y resultados</h2>
<p><img src="cronologia.png" style="width:100%"/></p>
<table><tr><th></th><th>Ronda 0, sin mejoras</th><th>Ronda 1, alerta y NetworkPolicy</th></tr>
<tr><td>MTTD (de la creación a la alerta)</td><td>no se detectó</td><td>{s(mttd1)}</td></tr>
<tr><td>MTTC (de la alerta a la contención)</td><td>sin alerta no hubo quién contuviera</td><td>{s(mttc1)}</td></tr>
<tr><td>B: salto este-oeste</td><td>pasó (HTTP {r0['http_este_oeste']})</td><td>bloqueado</td></tr>
<tr><td>C: salida a Internet</td><td>pasó (HTTP {r0['http_salida']})</td><td>bloqueada</td></tr>
<tr><td>Cobertura de la alerta</td><td>0 de 3</td><td>1 de 3 (la A)</td></tr>
<tr><td>Falsos positivos</td><td>sin alerta que pudiera darlos</td><td>0</td></tr>
<tr><td>Hipótesis</td><td>se refuta: no hay alerta</td><td>se cumple</td></tr>
</table>
<p class="nota">En la ronda 0 la contención a los {r0['segundos_hasta_contencion']} s la hizo quien operaba el experimento, que ya sabía del evento; no cuenta como MTTC. El NodePort quedó sin respuesta desde fuera de la red en las dos rondas, porque el firewall solo deja pasar el puerto 80 al balanceador. Con las políticas puestas, el flujo completo siguió dando 200.</p>

<h2>Mejoras, detección y tendencias</h2>
<p><b>Alerta de Services expuestos</b> sobre el registro de auditoría de Kubernetes, con la notificación en Pub/Sub para leer la hora real. <b>NetworkPolicy</b> de denegación por defecto de entrada y salida, con entrada solo al puerto de la API y salida solo a DNS, metadatos, la API de Cloud SQL y la base. Las reglas de detección son código versionado, con {len(positivos)} casos positivos y {len(negativos)} negativos que corren en cada push.</p>
<p><b>Credencial señuelo:</b> un secreto que nadie usa; abrirlo avisó a los {s(mttd_senuelo)} y mirar sus metadatos no avisó (MITRE D3FEND D3-DUC y ATT&amp;CK T1552, consultados el 15 de noviembre de 2026). <b>Mínimo privilegio:</b> la cuenta que despliega pasó de {len(ci_antes['roles'])} a {len(ci_despues['roles'])} roles y de {len(ci_antes['roles_admin'])} a {len(ci_despues['roles_admin'])} de administración, probando cada operación del despliegue con su identidad (guía de prácticas recomendadas para cuentas de servicio de Google Cloud, consultada el 15 de noviembre de 2026).</p>
<p><b>Riesgos y pendientes.</b> La alerta cubre una de las tres rutas: la B y la C se previenen pero no dejan señal propia, y falta una alerta sobre los flujos de red denegados. Los resultados son de una sola ejecución por ronda. La NetworkPolicy se revirtió al terminar el experimento. Habilitar los registros de lectura de Secret Manager suma volumen de logs.</p>
<p class="nota">Informe completo de StatsNostra: seguridad/informe/informe-seguridad-statsnostra.pdf. Evidencia: seguridad/evidencia/.</p>
</body></html>
"""

(AQUI / "informe-seguridad-statsnostra.html").write_text(html, encoding="utf-8")
(AQUI / "seccion-statsnostra.html").write_text(seccion, encoding="utf-8")


def navegador() -> str:
    for c in (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ):
        if Path(c).exists():
            return c
    raise SystemExit("No encontré Edge ni Chrome para imprimir el PDF")


def imprimir(nombre: str) -> None:
    salida = AQUI / f"{nombre}.pdf"
    subprocess.run(
        [
            navegador(),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={salida}",
            (AQUI / f"{nombre}.html").as_uri(),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    try:
        import pymupdf

        print(f"{nombre}: {pymupdf.open(str(salida)).page_count} páginas")
    except ImportError:
        print("PDF escrito en", salida)


imprimir("informe-seguridad-statsnostra")
imprimir("seccion-statsnostra")
