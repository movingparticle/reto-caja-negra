import { createServer } from './src/server.mjs';

const PORT = parseInt(process.env.PORT || '3000', 10);
const TOKEN = process.env.TEAM_TOKEN || 'cn-p-abh_bog_wlw9_8r83-QnLthfmAjCo3D6QXyf_Ztb';

const { server } = createServer({ token: TOKEN });

server.listen(PORT, '0.0.0.0', () => {
  console.log(`[Caja Negra Reemplazo] Running on port ${PORT}`);
  console.log(`[Caja Negra Reemplazo] Configured Team Token: ${TOKEN}`);
});
