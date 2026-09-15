from contextvars import ContextVar

# Header propuesto por esta API para el identificador de correlacion
# (trace-id); pendiente de confirmar el nombre final con el orquestador
# del equipo.
TRACE_ID_HEADER = "X-Trace-Id"

# Disponible durante toda la peticion (lo fija TraceIdMiddleware), para que
# el cliente HTTP externo pueda propagarlo sin que cada funcion tenga que
# recibirlo como parametro explicito.
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
