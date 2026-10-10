import { createServer } from './src/server.mjs';

const PORT = parseInt(process.env.PORT || '3000', 10);
const TOKEN = process.env.TEAM_TOKEN || '';

const { server } = createServer({ token: TOKEN });

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[Caja Negra Reemplazo] Running on port ${PORT}`);
  console.log(`[Caja Negra Reemplazo] Team Token configured: ${TOKEN ? 'yes' : 'no'}`);
});
