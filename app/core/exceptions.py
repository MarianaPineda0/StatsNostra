class ErrorDominio(Exception):
    pass


class RecursoNoEncontrado(ErrorDominio):
    pass


class ConflictoDeDatos(ErrorDominio):
    pass


class ReglaDeNegocioViolada(ErrorDominio):
    pass
