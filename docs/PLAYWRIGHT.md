# Playwright MCP no projeto

O servidor oficial da Microsoft está fixado em `@playwright/mcp` 0.0.84, com dependências em `package-lock.json`. A configuração de projeto está em `.codex/config.toml`.

```powershell
npm ci
npm run test:mcp
npm run mcp:playwright
```

O último comando fica aguardando um cliente MCP via stdio. Não é uma página web nem precisa ficar aberto fora do cliente.

Abra este checkout como projeto no Codex. Configurações `.codex/config.toml` de projeto são carregadas em projetos confiáveis; responda ao aviso de confiança pelo próprio aplicativo quando aparecer. Reinicie a conexão/chat se o servidor ainda não aparecer nas ferramentas. O teste de protocolo comprova inicialização/listagem/navegação do servidor, não seu carregamento automático neste chat já aberto.

Modos obrigatórios: `--headless --isolated --browser chrome`. Não usar `--extension`, `--cdp-endpoint`, perfil pessoal, `--user-data-dir` compartilhado nem `--allow-unrestricted-file-access`. A instalação não altera a configuração global do Codex.

O usuário deve executar verificações que precisem da interface nativa Unity/Tauri. O MCP testa a camada web isolada e serviços HTTP; não controla o desktop.

Referências oficiais:
- https://github.com/microsoft/playwright-mcp
- https://playwright.dev/mcp/clients/other-clients
- https://developers.openai.com/codex/mcp
