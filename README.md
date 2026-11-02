# KOFAS local — fontes e migração experimental

Controle de versão do launcher local funcional e da investigação do cliente PC 1.17.0. Leia [AGENTS.md](AGENTS.md) antes de trabalhar.

**Escopo atual: análise comparativa, sem novas adaptações.** O experimento híbrido 1.17 com dados antigos fica suspenso. O objetivo é avaliar separadamente reparar a versão nova ou portar funções para a antiga, antes de implementar qualquer caminho. Login/lobby do experimento não comprovam a atualização.

Consulte o [relatório comparativo de diferenças, esforço e viabilidade](docs/assessment/COMPARATIVO-1.11-1.17.md), produzido com extrações refeitas a partir dos clientes originais.

## Estado

O backup completo da instalação 1.11.2 está fora do Git e foi verificado por SHA-256 (17.936 arquivos, 11.098.474.923 bytes). Os originais foram preservados. A cópia experimental 1.17.0 chegou à autenticação local, carregamento das tabelas reconstruídas, conexão TCP e renderização do lobby. Isso não comprova migração completa, combate nem disponibilidade dos personagens recentes.

Este repositório contém fontes e metadados: não é uma distribuição pronta do jogo. Clientes, assets, ferramentas, Python portátil, tabelas binárias e saves continuam locais. O launcher 1.11 e o servidor experimental têm portas diferentes; ainda não foram integrados numa única distribuição. [Detalhes e limites](docs/STATUS.md).

## Testes sem controlar o PC

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r server\requirements.txt
.venv\Scripts\python.exe scripts\prepare-local-fixtures.py --server-data "CAMINHO\DA\COPIA\EXPERIMENTAL\outputs\KOFAS-Local-Server"
.venv\Scripts\python.exe -B -m unittest discover -s server\tests -v
npm ci
npm run test:launcher
npm run test:mcp
```

O teste do MCP inicia um Chrome headless separado, navega apenas numa página temporária servida em loopback, verifica o resultado e encerra o contexto. Não conecta ao Chrome pessoal, não abre o jogo e não movimenta mouse ou teclado do desktop. Chrome instalado é necessário. O MCP serve a testes web/API; não substitui validação nativa do Unity pelo usuário.

Os 39 testes existentes precisam das tabelas locais importadas pelo comando acima; elas são ignoradas pelo Git. O importador lê uma lista restrita de tabelas e confere as chaves, sem copiar saves ou iniciar processos. Os quatro testes de `server/tests_integration` exigem ainda a árvore local completa, incluindo o cache Unity. Não fazem parte da suíte de código deste checkout. Não executar o inicializador de jogo como teste autônomo.

## Ferramentas

- [Playwright MCP e ativação no Codex](docs/PLAYWRIGHT.md)
- [Graphify, índice e análise de impacto](docs/GRAPHIFY.md)
- [Procedência das fontes importadas](docs/source-import.json)
- [Estado e verificação manual do jogo](docs/STATUS.md)

O primeiro snapshot preserva fontes existentes, sem atribuir licença aos componentes originais ou ao conteúdo do jogo. Nenhum cliente ou asset Unity é publicado aqui.
