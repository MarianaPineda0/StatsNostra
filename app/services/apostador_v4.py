from app.core.exceptions import RecursoNoEncontrado
from app.repositories.apostador import ApostadorRepository
from app.repositories.prediccion import PrediccionRepository
from app.schemas.apostador_v4 import ResumenApostadorV4


class ApostadorV4Service:
    """Resumen de desempeno de un apostador (Entrega 4). Solo lee: no
    cambia reglas ni datos de las versiones anteriores."""

    def __init__(
        self, apostadores: ApostadorRepository, predicciones: PrediccionRepository
    ) -> None:
        self.apostadores = apostadores
        self.predicciones = predicciones

    def resumen(self, apostador_id: int) -> ResumenApostadorV4:
        apostador = self.apostadores.obtener_por_id(apostador_id)
        if apostador is None:
            raise RecursoNoEncontrado(f"Apostador {apostador_id} no encontrado")

        todas = self.predicciones.listar_por_apostador(apostador_id)
        evaluadas = [p for p in todas if p.acertada is not None]
        aciertos = sum(1 for p in evaluadas if p.acertada)

        # Orden por fecha y, si empatan (misma transaccion), por id: la mas
        # reciente primero para contar la racha hacia atras
        recientes = sorted(evaluadas, key=lambda p: (p.fecha_prediccion, p.id), reverse=True)
        racha = 0
        for prediccion in recientes:
            if not prediccion.acertada:
                break
            racha += 1

        con_confianza = [p.confianza for p in todas if p.confianza is not None]
        return ResumenApostadorV4(
            apostador_id=apostador.id,
            username=apostador.username,
            total_predicciones=len(todas),
            evaluadas=len(evaluadas),
            aciertos=aciertos,
            precision=round(aciertos / len(evaluadas) * 100, 2) if evaluadas else 0.0,
            puntos_totales=sum(p.puntos or 0 for p in evaluadas),
            racha_actual=racha,
            confianza_promedio=(
                round(sum(con_confianza) / len(con_confianza), 2) if con_confianza else None
            ),
        )
