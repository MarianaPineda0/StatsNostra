def calcular_puntos(
    goles_local_pred: int,
    goles_visitante_pred: int,
    goles_local_real: int,
    goles_visitante_real: int,
) -> tuple[bool, int]:
    if goles_local_pred == goles_local_real and goles_visitante_pred == goles_visitante_real:
        return True, 3

    if _resultado(goles_local_pred, goles_visitante_pred) == _resultado(
        goles_local_real, goles_visitante_real
    ):
        return True, 1

    return False, 0


def _resultado(goles_local: int, goles_visitante: int) -> str:
    if goles_local > goles_visitante:
        return "LOCAL"
    if goles_local < goles_visitante:
        return "VISITANTE"
    return "EMPATE"
