// Perfil de carga fijo del grupo: se usa igual en el estado estable, en la ronda 0
// y en la ronda 1. Cambiarlo entre rondas invalida la comparación.
//
// Uso (desde la raíz del repositorio): caos/carga/correr.sh CARPETA NUMERO
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    perfil: {
      executor: 'ramping-vus',
      startVUs: 0,
      gracefulRampDown: '10s',
      // 5 usuarios 60 s, luego 15 durante 60 s y luego 30 durante 60 s: 3 minutos
      stages: [
        { duration: '60s', target: 5 },
        { duration: '60s', target: 15 },
        { duration: '60s', target: 30 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1500'],
  },
};

export default function () {
  // Un X-Trace-Id distinto por iteración permite seguir cada petición por las
  // tres nubes con el mismo identificador
  const r = http.get(`${__ENV.BASE_URL}/api/v2/trades/${__ENV.TRADE_ID}`, {
    headers: { 'X-Trace-Id': `k6-${__VU}-${__ITER}` },
  });
  check(r, { 'status 200': (x) => x.status === 200 });
}
