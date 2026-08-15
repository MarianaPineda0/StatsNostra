# Prueba temporal e intencional para validar que el pipeline bloquea el
# despliegue cuando una prueba falla. Se elimina inmediatamente despues de
# confirmar el comportamiento.


def test_falla_temporal_para_validar_el_pipeline():
    assert False
