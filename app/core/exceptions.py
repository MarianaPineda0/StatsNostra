class ErrorDominio(Exception):
    """Base de todas las excepciones de negocio de la app.

    Los servicios lanzan estas excepciones sin conocer HTTP; los
    exception_handler de app/main.py son los que las traducen a un
    codigo de estado (404/409/400 respectivamente).
    """


class RecursoNoEncontrado(ErrorDominio):
    pass


class ConflictoDeDatos(ErrorDominio):
    pass


class ReglaDeNegocioViolada(ErrorDominio):
    pass
