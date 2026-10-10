import { validateControl } from './checksum.mjs';
import { suggestCommand } from './suggest.mjs';

/**
 * Formato de saldo del oráculo tras el incidente (15:30): entero en centavos
 * -> cadena decimal con 2 posiciones ("0.01", "5.00", "-10.00").
 */
export function formatSaldo(cents) {
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  const entero = Math.floor(abs / 100);
  const decimal = String(abs % 100).padStart(2, '0');
  return `${sign}${entero}.${decimal}`;
}

export const TRANSFER_LIMIT = 50000; // límite tras el incidente (antes 100000)
export const MAX_FALLOS = 3; // fallos E506/E507 consecutivos antes de bloquear

export class BankingEngine {
  constructor() {
    this.reset();
  }

  reset() {
    this.accounts = new Map(); // cuentaId -> { id, nombre, saldo, fails, blocked, intentos }
    this.operations = new Map(); // operacionId -> { id, tipo, ... }
    this.accountSeq = 1;
    this.operationSeq = 1;
    this.halted = false; // estado "service halted" (comando HALT;1)
  }

  processMessage(rawMessage) {
    if (typeof rawMessage !== 'string') {
      return {
        status: 400,
        body: { error: 'E102', mensaje: 'falta m' },
      };
    }

    // Step 1: Delimiter and segment structure check
    const lastSemi = rawMessage.lastIndexOf(';');
    if (lastSemi === -1) {
      return { status: 400, body: { error: 'E103', mensaje: 'falta control' } };
    }

    const parts = rawMessage.split(';');
    if (parts.some(p => p.length === 0)) {
      return { status: 400, body: { error: 'E104', mensaje: 'segmento vacío' } };
    }

    const rawCmd = parts[0];
    const cmd = rawCmd.toUpperCase();

    // PING in the black box skips checksum verification but strictly enforces arity (exactly 2 segments: PING;<control>)
    if (cmd === 'PING') {
      if (parts.length !== 2) {
        return { status: 400, body: { error: 'E302', mensaje: 'aridad inválida' } };
      }
      return { status: 200, body: { pong: true } };
    }

    // Step 2: Validate control code for all other commands
    const validation = validateControl(rawMessage);
    if (!validation.valid) {
      return {
        status: 400,
        body: { error: validation.error, mensaje: validation.message },
      };
    }

    // Step 3: Parse command and arguments
    const payloadParts = validation.payload.split(';');
    const args = payloadParts.slice(1);

    // Step 4: Route command
    switch (cmd) {

      case 'ALTA': {
        if (args.length !== 1) {
          return { status: 400, body: { error: 'E302', mensaje: 'aridad inválida' } };
        }
        const nombre = args[0];
        const cuentaId = `AC-${String(this.accountSeq++).padStart(4, '0')}`;
        this.accounts.set(cuentaId, {
          id: cuentaId,
          nombre,
          saldo: 0,
          fails: 0,
          blocked: false,
          intentos: 0,
        });
        return { status: 201, body: { cuentaId } };
      }

      case 'CONSULTA': {
        if (args.length !== 1) {
          return { status: 400, body: { error: 'E302', mensaje: 'aridad inválida' } };
        }
        const cuentaId = args[0];
        if (!this.accounts.has(cuentaId)) {
          return { status: 404, body: { error: 'E401', mensaje: 'cuenta inexistente' } };
        }
        const acc = this.accounts.get(cuentaId);
        return {
          status: 200,
          body: {
            cuenta_id: acc.id,
            saldo: formatSaldo(acc.saldo),
          },
        };
      }

      case 'DEPOSITO': {
        if (args.length !== 2) {
          return { status: 400, body: { error: 'E302', mensaje: 'aridad inválida' } };
        }
        const cuentaId = args[0];
        const rawMonto = args[1];

        // Monto check: strictly positive digits, no leading zeros, max 10 digits
        if (!/^[1-9]\d{0,9}$/.test(rawMonto)) {
          return { status: 400, body: { error: 'E303', mensaje: 'monto inválido' } };
        }
        const monto = parseInt(rawMonto, 10);

        if (!this.accounts.has(cuentaId)) {
          return { status: 404, body: { error: 'E401', mensaje: 'cuenta inexistente' } };
        }

        const acc = this.accounts.get(cuentaId);
        acc.saldo += monto;
        // Un depósito exitoso resetea el contador de fallos y desbloquea la cuenta.
        acc.fails = 0;
        acc.blocked = false;
        acc.intentos = 0;
        const operacionId = `OP-${String(this.operationSeq++).padStart(4, '0')}`;
        this.operations.set(operacionId, {
          id: operacionId,
          tipo: 'DEPOSITO',
          cuentaId,
          monto,
          anulada: false,
        });
        return {
          status: 200,
          body: {
            status: 'recieved',
            operacionId,
          },
        };
      }

      case 'TRANSFER': {
        if (args.length !== 3) {
          return { status: 400, body: { error: 'E302', mensaje: 'aridad inválida' } };
        }
        const origenId = args[0];
        const destinoId = args[1];
        const rawMonto = args[2];

        // Precedence 1: Monto validity (no leading zeros, max 10 digits)
        if (!/^[1-9]\d{0,9}$/.test(rawMonto)) {
          return { status: 400, body: { error: 'E303', mensaje: 'monto inválido' } };
        }
        const monto = parseInt(rawMonto, 10);

        // Precedence 2: Origen y destino iguales
        if (origenId === destinoId) {
          return { status: 400, body: { error: 'E304', mensaje: 'origen y destino iguales' } };
        }

        // Precedence 3: Cuenta inexistente
        if (!this.accounts.has(origenId)) {
          return { status: 404, body: { error: 'E401', mensaje: 'cuenta inexistente' } };
        }
        if (!this.accounts.has(destinoId)) {
          return { status: 404, body: { error: 'E401', mensaje: 'cuenta inexistente' } };
        }

        const origen = this.accounts.get(origenId);
        const destino = this.accounts.get(destinoId);

        // Precedence 4 (incidente): cuenta origen bloqueada -> E510 (423)
        if (origen.blocked) {
          origen.intentos += 1;
          return {
            status: 423,
            body: { error: 'E510', mensaje: 'cuenta bloqueada', intentos: origen.intentos },
          };
        }

        // Precedence 5: Límite excedido (50000 tras el incidente)
        if (monto > TRANSFER_LIMIT) {
          this._registrarFallo(origen);
          return { status: 422, body: { error: 'E506', mensaje: 'límite excedido' } };
        }

        // Precedence 6: Saldo insuficiente
        if (origen.saldo < monto) {
          this._registrarFallo(origen);
          return { status: 422, body: { error: 'E507', mensaje: 'saldo insuficiente' } };
        }

        origen.saldo -= monto;
        destino.saldo += monto;
        // Transferencia exitosa: resetea el contador de fallos del origen.
        origen.fails = 0;
        origen.intentos = 0;
        const operacionId = `OP-${String(this.operationSeq++).padStart(4, '0')}`;
        this.operations.set(operacionId, {
          id: operacionId,
          tipo: 'TRANSFER',
          origenId,
          destinoId,
          monto,
          anulada: false,
        });

        return {
          status: 200,
          body: {
            status: 'recieved',
            operacionId,
          },
        };
      }

      case 'ANULA': {
        if (args.length !== 1) {
          return { status: 400, body: { error: 'E302', mensaje: 'aridad inválida' } };
        }
        const operacionId = args[0];
        if (!this.operations.has(operacionId)) {
          return { status: 404, body: { error: 'E402', mensaje: 'operación inexistente' } };
        }
        const op = this.operations.get(operacionId);
        if (op.anulada) {
          return { status: 200, body: { ok: false, motivo: 'ya anulada' } };
        }

        // Reversal of transaction (allows negative balances)
        if (op.tipo === 'TRANSFER') {
          const origen = this.accounts.get(op.origenId);
          const destino = this.accounts.get(op.destinoId);
          if (origen && destino) {
            origen.saldo += op.monto;
            destino.saldo -= op.monto;
          }
        } else if (op.tipo === 'DEPOSITO') {
          const acc = this.accounts.get(op.cuentaId);
          if (acc) {
            acc.saldo -= op.monto;
          }
        }

        op.anulada = true;
        return { status: 200, body: { ok: true, anulada: operacionId } };
      }

      case 'HALT': {
        if (args.length !== 1) {
          return { status: 400, body: { error: 'E302', mensaje: 'aridad inválida' } };
        }
        // Confirmación exacta: el único argumento debe ser literalmente "1".
        if (args[0] === '1') {
          this.halted = true;
          return { status: 503, body: { error: 'E599', mensaje: 'service halted' } };
        }
        return {
          status: 409,
          body: {
            error: 'E520',
            mensaje: 'operación destructiva: detiene el servicio; reenvía con confirmación',
          },
        };
      }

      default: {
        const body = { error: 'E301', mensaje: 'comando desconocido ' };
        const sugerencia = suggestCommand(cmd);
        if (sugerencia) body.sugerencia = sugerencia;
        return { status: 400, body };
      }
    }
  }

  _registrarFallo(cuenta) {
    cuenta.fails += 1;
    if (cuenta.fails >= MAX_FALLOS) {
      cuenta.blocked = true;
    }
  }
}
