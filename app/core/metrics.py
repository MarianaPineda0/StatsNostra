from prometheus_client import Counter

cache_aciertos = Counter(
    "statsnostra_cache_aciertos_total", "Aciertos de la cache distribuida"
)
cache_fallos = Counter("statsnostra_cache_fallos_total", "Fallos de la cache distribuida")
