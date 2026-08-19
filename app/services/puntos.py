def calcular_puntos(
    goles_local_pred: int,
    goles_visitante_pred: int,
    goles_local_real: int,
    goles_visitante_real: int,
) -> tuple[bool, int]:
    """Calcula el puntaje de una prediccion contra el resultado real.

    Reglas: marcador exacto = 3 puntos; acierta quien gana (o el empate)
    pero falla el marcador = 1 punto; falla el ganador = 0 puntos.
    Funcion pura (sin acceso a BD) para poder probarla de forma aislada.
    """
    if goles_local_pred == goles_local_real and goles_visitante_pred == goles_visitante_real:
        return True, 3

    if _resultado(goles_local_pred, goles_visitante_pred) == _resultado(
        goles_local_real, goles_visitante_real
    ):
        return True, 1

    return False, 0


def _resultado(goles_local: int, goles_visitante: int) -> str:
    # Reduce un marcador a "quien gano" (o empate), para comparar el
    # ganador predicho contra el ganador real sin importar el marcador exacto
    if goles_local > goles_visitante:
        return "LOCAL"
    if goles_local < goles_visitante:
        return "VISITANTE"
    return "EMPATE"
