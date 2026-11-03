# Regras do projeto KOFAS

Estas regras valem para todo o repositório. Instruções diretas do usuário têm prioridade.

## Trabalho ativo autorizado pelo usuário

- A opção A está pausada a pedido do usuário. O trabalho atual é corrigir o Skill Up das Battle Cards na instalação funcional `KOF ALLSTAR Local` (1.11.2).
- Esse pedido autoriza excepcionalmente corrigir os fontes do servidor dessa instalação, com backup verificado de cada arquivo alterado e do save antes da instalação da correção. Não alterar o cliente, tabelas ou mods e não misturar dados com a 1.17.
- Exceção adicional explicitamente solicitada: balancear todos os status de Awaken pela proporção direta do nível 1 ao 6. É autorizado gerar efeitos exclusivos nas tabelas locais reconstruídas da 1.11, preservando efeitos/status normais, e atualizar descrições, hashes e versões de download, com backup verificado. Não alegar valores oficiais nem alterar cliente/mods/saves para isso. Seguir `docs/superpowers/plans/2026-11-02-awaken-linear.md`.
- Desenvolver e testar com perfis temporários ou cópias. Não editar o save ativo em paralelo com o jogo; a recuperação de níveis inconsistentes deve ocorrer pelo serviço corrigido na leitura normal do perfil, sem nova cobrança.
- Não encerrar nem reiniciar a sessão aberta do usuário. A instalação do fonte exige que o usuário feche e reabra o jogo/launcher para carregar o serviço corrigido. Não executar testes dirigindo a interface.

## Escopo vigente: opção A — recuperar a 1.17.0 original

- O usuário escolheu explicitamente reparar a versão mais recente, preservando personagens, conteúdo e mecânicas de aprimoramento da própria 1.17.0.
- Não combinar arquivos, tabelas, saves ou mods da 1.11.2 com a nova versão. Não usar o experimento híbrido como ponto de partida, fallback ou prova de sucesso.
- A instalação funcional 1.11.2, seu backup e o experimento híbrido suspenso são referências separadas. A execução futura da opção A deve nascer de uma cópia limpa da base original 1.17.0, com perfil novo e procedência verificável.
- É autorizado analisar e implementar as adaptações necessárias dentro desse escopo, respeitando Graphify, backup, isolamento e testes sem controle do PC. Ferramentas genéricas de análise não são dados de uma versão do jogo.
- Primeiro recuperar e validar as tabelas originais 1.17.0; depois catalogar o conteúdo e implementar o serviço local conforme o protocolo novo. Não substituir dados indisponíveis por tabelas antigas, valores inventados ou respostas vazias e chamar isso de atualização concluída.
- Acesso a todos os personagens e aprimoramentos exige identificação nos dados originais, implementação e validação de persistência/regras. Lobby aberto isoladamente não satisfaz o pedido.
- Registrar fatos, inferências, lacunas e critérios de sucesso em `docs/superpowers/plans/2026-11-02-opcao-a-117.md` e `docs/assessment/OPCAO-A-117-PROGRESSO.md`.

## Regra principal: testes sem controlar o PC

- Não controlar mouse, teclado, foco, janelas ou aplicativos do usuário para testar.
- Não usar Computer Use, Sky, CUA, SendInput, macros, CDP na sessão pessoal ou scripts equivalentes para testes.
- Não abrir, dirigir ou injetar comandos de interface no cliente Unity durante testes autônomos. Isso inclui harnesses Frida que acionem login, cenas, botões ou capturas do jogo.
- Preferir testes automáticos de código, protocolo, arquivos, API e CLI. Para interface web, usar somente navegador headless isolado, sem perfil pessoal, extensão de conexão ou CDP externo.
- Quando um teste exigir o jogo ou interação no desktop, entregar ao usuário um roteiro com passos, resultado esperado e evidência necessária. Aguardar o resultado; não executar por conta própria.
- Playwright cobre a interface web do launcher e serviços HTTP; não controla o jogo Unity nem valida combate nativo.

## Graphify antes de trabalhar em arquivos

1. Consultar `list_repositories` e verificar o índice de `extrajogos6-ops/KOFAS` e seu commit.
2. Antes de alterar cada arquivo existente, consultar `graphify_file_neighbors` com seu caminho relativo. Para símbolos afetados, consultar `graphify_callers`/`graphify_impact` e `graphify_tests_for` conforme a mudança.
3. Conferir o código local e o diff desde o commit indexado. Ausência de resultados não prova ausência de dependências. Correspondências semânticas não são definições exatas.
4. Registrar em `docs/impact/` os arquivos, commit indexado, dependências, limitações do índice e testes escolhidos.
5. Se o Graphify não estiver autorizado, não estiver indexado ou não cobrir o arquivo, informar a limitação. Não declarar análise de impacto concluída nem alterar comportamento do jogo sem resolver o bloqueio ou receber orientação explícita do usuário. É permitido preparar documentação, configuração e importar fontes sem modificá-las para o primeiro índice.
6. Arquivos novos também exigem consulta sobre seus pontos de integração; eles naturalmente podem não existir no índice ainda.

## Backup e isolamento

- A instalação funcional 1.11.2 e seu save são referência. Não editar, substituir, atualizar ou testar sobre ela.
- Antes de modificar um arquivo fora do Git, criar cópia e registrar SHA-256, caminho e motivo. No Git, manter base identificada e diff revisável; backup de saves continua obrigatório.
- Alterações experimentais pertencem à cópia 1.17.0. Usar perfil separado e somente loopback 18775/18776; os serviços antigos usam 18765/18766.
- Não matar processos por nome. Encerrar apenas processos criados pelo próprio teste, com identidade verificada, e limpar os serviços em `finally`.
- Não aplicar patches de uma versão em outra por semelhança de nome. Validar hashes, metadata, offsets, protocolo e assets.

## Versionamento e dados

- Versionar fontes, configurações sem credenciais, testes, scripts e documentação. Preservar a procedência das fontes importadas.
- Não adicionar clientes, executáveis, DLLs, assets Unity, caches, dumps/decompilações, runtimes, ferramentas instaladas ou backups ao Git.
- Não adicionar saves, perfis, tokens, senhas, arquivos `.env`, histórico de chat ou logs pessoais. Chaves sintéticas de tabelas são fixtures, não credenciais de contas.
- Conferir `git diff --cached` e arquivos incluídos antes de cada commit/push. Não usar force-push nem alterar histórico remoto sem solicitação específica.
- Não apresentar stubs HTTP, índice de assets ou lobby renderizado como prova de conteúdo novo, combate ou migração completa.

## Fluxo de mudança

1. Ler estas regras, estado do Git, documentação e Graphify.
2. Definir problema, impacto e validação; preservar uma referência antes de editar.
3. Fazer a menor mudança coerente. Não portar mods antigos indiscriminadamente.
4. Executar testes relevantes sem controle do PC; registrar comandos e resultados reais, incluindo testes pendentes ou impossíveis.
5. Revisar diff, dados excluídos e regressões. Commit descritivo e atualização do status da migração.
6. Se Graphify precisar de atualização após o push, aguardar o índice ou documentar seu atraso antes da próxima alteração de comportamento.

## Mapa das fontes

- `server/`: snapshot do servidor local adaptado às portas experimentais, dados reconstruídos e testes Python.
- `launcher/`: fontes originais do launcher funcional 1.11.2 (TypeScript/Tauri/Rust), sem assets ou build.
- `migration/1.17.0/tools/`: snapshot do inicializador e ponte de compatibilidade experimentais. A árvore de execução e os clientes continuam fora do repositório.
- As três partes ainda não formam uma distribuição unificada. Consultar `docs/STATUS.md` antes de integrar.
