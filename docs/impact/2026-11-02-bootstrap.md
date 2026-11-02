# Bootstrap do versionamento

Solicitação: criar versionamento GitHub, regras de trabalho, consulta obrigatória ao Graphify e MCP Playwright; proibir controle do PC em testes.

Graphify consultado com `list_repositories`, `list_workspaces` e `graphify_file_neighbors(AGENTS.md)`. Resultado: workspace acessível, mas HTTP 403 `no_authorized_repositories`; índice e commit indisponíveis. Nenhuma análise de dependências é alegada.

Escopo: cópia exata das fontes existentes conforme `docs/source-import.json`; novos AGENTS, documentação, configuração MCP, dependência fixada e teste de instalação MCP. Nenhuma alteração de comportamento do cliente/jogo durante esta preparação. Assets, perfis e executáveis excluídos.

Validação prevista: hashes das fontes importadas, suíte Python portátil, testes TypeScript existentes, handshake MCP e navegação em navegador headless isolado, revisão dos arquivos Git e verificação do push remoto. Indexação hospedada permanece dependente da autorização e disponibilidade do painel Graphify.
