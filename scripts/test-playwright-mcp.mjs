import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
const child = spawn(process.execPath, [
  path.join(root, 'node_modules/@playwright/mcp/cli.js'),
  '--headless', '--isolated', '--browser', 'chrome',
], { cwd: root, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });
const pending = new Map();
let nextId = 0;
let stderr = '';
child.stderr.on('data', data => { stderr = (stderr + data).slice(-4000); });
const lines = createInterface({ input: child.stdout });
lines.on('line', line => {
  let message;
  try { message = JSON.parse(line); } catch { return; }
  const request = pending.get(message.id);
  if (!request) return;
  pending.delete(message.id);
  clearTimeout(request.timer);
  if (message.error) request.reject(new Error(JSON.stringify(message.error)));
  else request.resolve(message.result);
});
child.on('error', failAll);
child.on('exit', code => failAll(new Error(`MCP encerrou (${code}). ${stderr}`)));
function failAll(error) {
  for (const request of pending.values()) {
    clearTimeout(request.timer);
    request.reject(error);
  }
  pending.clear();
}
function request(method, params = {}, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Timeout: ${method}. ${stderr}`));
    }, timeout);
    pending.set(id, { resolve, reject, timer });
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
  });
}
function notify(method) {
  child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method }) + '\n');
}
let navigated = false;
const fixture = createServer((req, res) => {
  if (req.url === '/mcp-install-check') navigated = true;
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end('<title>KOFAS MCP installation check</title><main><h1>Isolated browser verified</h1></main>');
});
await new Promise(resolve => fixture.listen(0, '127.0.0.1', resolve));
try {
  const initialized = await request('initialize', {
    protocolVersion: '2024-11-05', capabilities: {},
    clientInfo: { name: 'kofas-installation-check', version: '0.1.0' },
  });
  assert.ok(initialized.serverInfo?.name);
  notify('notifications/initialized');
  const { tools } = await request('tools/list');
  for (const name of ['browser_navigate', 'browser_snapshot', 'browser_close']) {
    assert.ok(tools.some(tool => tool.name === name), `Ferramenta ausente: ${name}`);
  }
  const url = `http://127.0.0.1:${fixture.address().port}/mcp-install-check`;
  const navigation = await request('tools/call', { name: 'browser_navigate', arguments: { url } });
  assert.ok(!navigation.isError, JSON.stringify(navigation));
  const snapshot = await request('tools/call', { name: 'browser_snapshot', arguments: {} });
  assert.ok(!snapshot.isError, JSON.stringify(snapshot));
  assert.match(JSON.stringify(snapshot.content), /Isolated browser verified/);
  assert.ok(navigated, 'A página de verificação não recebeu a navegação');
  console.log(`PASS: ${initialized.serverInfo.name}; ${tools.length} ferramentas; navegação headless isolada em loopback.`);
} finally {
  try { await request('tools/call', { name: 'browser_close', arguments: {} }, 5000); }
  catch { /* The process may already have exited; cleanup still runs. */ }
  fixture.closeAllConnections();
  await new Promise(resolve => fixture.close(resolve));
  lines.close();
  child.stdin.end();
  child.kill();
}
