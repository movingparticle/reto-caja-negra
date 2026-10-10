/**
 * Motor de la Réplica (State Machine & Reglas de Negocio)
 * Reemplazo determinista y autónomo para el servicio de caja negra.
 */

export class ReplicaEngine {
  constructor() {
    this.reset();
  }

  /**
   * Restablece el estado interno a sus valores de fábrica.
   */
  reset() {
    this.state = {
      initializedAt: Date.now(),
      records: new Map(),
      counters: new Map(),
    };
  }

  /**
   * Procesa una petición delegada del servicio original.
   * @param {Object} context - { method, path, headers, query, body }
   * @returns {Object} { status, headers, body }
   */
  processRequest({ method, path, headers = {}, body = null }) {
    // 1. Manejo inicial de rutas descubiertas (se extenderá según avance el probing)
    if (method === 'GET' && (path === '/' || path === '')) {
      return {
        status: 200,
        headers: { 'content-type': 'application/json; charset=utf-8' },
        body: { service: 'legacy-service', active: true },
      };
    }

    // 2. Ruta desconocida o no implementada aún en el servicio original
    return {
      status: 404,
      headers: { 'content-type': 'application/json; charset=utf-8' },
      body: { error: 'not_found', path },
    };
  }
}
