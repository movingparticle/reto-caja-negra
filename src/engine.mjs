import { validateControl } from './checksum.mjs';

export class BankingEngine {
  constructor() {
    this.reset();
  }

  reset() {
    this.accounts = new Map(); // cuentaId -> { id, nombre, saldo }
    this.operations = new Map(); // operacionId -> { id, tipo, ... }
    this.accountSeq = 1;
    this.operationSeq = 1;
  }

  processMessage(rawMessage) {
    if (typeof rawMessage !== 'string') {
      return {
        status: 400,
        body: { error: 'E102', mensaje: 'falta m' },
      };
    }

    // Step 1: Validate control code, semicolon existence, and non-empty segments
    const validation = validateControl(rawMessage);
    if (!validation.valid) {
      return {
        status: 400,
        body: { error: validation.error, mensaje: validation.message },
      };
    }

    // Step 2: Parse command and arguments
    const parts = validation.payload.split(';');
    const rawCmd = parts[0];
    const cmd = rawCmd.toUpperCase();
    const args = parts.slice(1);

    // Step 3: Route command
    switch (cmd) {
      case 'PING': {
        if (args.length !== 0) {
          return { status: 400, body: { error: 'E302', mensaje: 'aridad inválida' } };
        }
        return { status: 200, body: { pong: true } };
      }

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
            saldo: acc.saldo,
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

        // Precedence 4: Límite excedido
        if (monto > 100000) {
          return { status: 422, body: { error: 'E506', mensaje: 'límite excedido' } };
        }

        // Precedence 5: Saldo insuficiente
        const origen = this.accounts.get(origenId);
        const destino = this.accounts.get(destinoId);

        if (origen.saldo < monto) {
          return { status: 422, body: { error: 'E507', mensaje: 'saldo insuficiente' } };
        }

        origen.saldo -= monto;
        destino.saldo += monto;
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

      default: {
        return { status: 400, body: { error: 'E301', mensaje: 'comando desconocido ' } };
      }
    }
  }
}
