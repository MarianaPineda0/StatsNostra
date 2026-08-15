from app.core.exceptions import ConflictoDeDatos, RecursoNoEncontrado
from app.models.apostador import Apostador
from app.repositories.apostador import ApostadorRepository
from app.schemas.apostador import ApostadorActualizar, ApostadorCrear


class ApostadorService:
    def __init__(self, repositorio: ApostadorRepository) -> None:
        self.repositorio = repositorio

    def crear(self, datos: ApostadorCrear) -> Apostador:
        if self.repositorio.obtener_por_username(datos.username):
            raise ConflictoDeDatos(f"El username '{datos.username}' ya está en uso")
        if self.repositorio.obtener_por_email(datos.email):
            raise ConflictoDeDatos(f"El email '{datos.email}' ya está en uso")

        apostador = Apostador(nombre=datos.nombre, username=datos.username, email=datos.email)
        return self.repositorio.crear(apostador)

    def listar(self) -> list[Apostador]:
        return self.repositorio.listar()

    def obtener(self, apostador_id: int) -> Apostador:
        apostador = self.repositorio.obtener_por_id(apostador_id)
        if apostador is None:
            raise RecursoNoEncontrado(f"Apostador {apostador_id} no encontrado")
        return apostador

    def actualizar(self, apostador_id: int, datos: ApostadorActualizar) -> Apostador:
        apostador = self.obtener(apostador_id)

        if datos.username and datos.username != apostador.username:
            if self.repositorio.obtener_por_username(datos.username):
                raise ConflictoDeDatos(f"El username '{datos.username}' ya está en uso")
            apostador.username = datos.username

        if datos.email and datos.email != apostador.email:
            if self.repositorio.obtener_por_email(datos.email):
                raise ConflictoDeDatos(f"El email '{datos.email}' ya está en uso")
            apostador.email = datos.email

        if datos.nombre is not None:
            apostador.nombre = datos.nombre
        if datos.activo is not None:
            apostador.activo = datos.activo

        return self.repositorio.actualizar(apostador)

    def eliminar(self, apostador_id: int) -> None:
        apostador = self.obtener(apostador_id)
        self.repositorio.eliminar(apostador)
