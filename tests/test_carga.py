# El ciclo de negocio de la carga: debe dejar un partido finalizado con dos
# predicciones, una acertada y otra no, sin tocar la red.
from canary import carga


def test_ciclo_de_negocio_finaliza_un_partido_con_una_prediccion_acertada(monkeypatch):
    llamadas = []

    def falso(url, cabeceras, metodo="GET", cuerpo=None):
        llamadas.append((metodo, url.split("/api/v1")[1], cuerpo))
        return "canary", "4.0.0", 201, 12.0, {"id": len(llamadas)}

    monkeypatch.setattr(carga, "_pedir", falso)
    registros = []
    carga._ciclo_negocio("https://servicio", {}, lambda *datos: registros.append(datos))

    rutas = [ruta for _, ruta, _ in llamadas]
    assert rutas[:3] == ["/apostadores", "/apostadores", "/partidos"]
    assert rutas[3:5] == ["/predicciones", "/predicciones"]
    assert rutas[5] == "/partidos/3/finalizar"
    assert len(registros) == 6  # cada peticion cuenta para el reparto por track

    resultado = llamadas[5][2]
    marcadores = [
        (p["goles_local_pred"], p["goles_visitante_pred"]) for _, _, p in llamadas[3:5]
    ]
    acertadas = [
        m
        for m in marcadores
        if m == (resultado["resultado_local"], resultado["resultado_visitante"])
    ]
    assert len(acertadas) == 1


def test_si_falla_un_paso_el_ciclo_se_detiene(monkeypatch):
    llamadas = []

    def falso(url, cabeceras, metodo="GET", cuerpo=None):
        llamadas.append(url)
        return "canary", "4.0.0", 500, 5.0, {}

    monkeypatch.setattr(carga, "_pedir", falso)
    carga._ciclo_negocio("https://servicio", {}, lambda *datos: None)
    assert len(llamadas) == 3  # apostadores y partido; sin ids no hay predicciones


def test_con_tasa_fija_la_carga_no_supera_el_ritmo_pedido(monkeypatch):
    # Aunque el servicio responda al instante, la tasa limita las peticiones
    monkeypatch.setattr(
        carga, "_una_peticion", lambda url, cabeceras: ("stable", "3.0.0", 200, 1.0)
    )
    resultados = carga.generar("https://servicio", 2, 4, {}, tasa=10)
    total = sum(len(v) for v in resultados.values())
    assert 14 <= total <= 22  # 10 por segundo durante 2 s, con margen de arranque
