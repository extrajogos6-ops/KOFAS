# Estado da migração em 2026-11-02

## Correção de escopo solicitada pelo usuário

O experimento abaixo fica suspenso. Ele combinou cliente/assets 1.17.0 com tabelas reconstruídas antigas e uma cópia de perfil 1.11.2. Isso não corresponde à atualização completa solicitada e não será usado como prova de viabilidade do conteúdo novo.

O trabalho atual é uma análise estática das bases originais, com relatório comparando reparar a 1.17 e portar funções da nova para a 1.11. Não executar o roteiro de jogo abaixo nem continuar adaptações até o usuário escolher uma direção após a análise. A discussão anterior sobre testes manuais e correções de inicialização não amplia esse escopo.

Relatório vigente: [comparação 1.11.2 × 1.17.0](assessment/COMPARATIVO-1.11-1.17.md). A seção de preservação distingue o backup congelado do estado mutável atual da instalação em uso.

## Referências locais

A instalação da Área de Trabalho permaneceu inalterada durante a investigação. O backup completo e a cópia experimental estão em `../KOFAS-Migracao/` em relação a este checkout. Não copiar arquivos do repositório por cima da instalação funcional sem backup, análise de impacto e validação.

`docs/source-import.json` identifica os arquivos copiados, sua origem lógica e hash. `launcher/` vem da versão funcional 1.11.2. `server/` e `migration/1.17.0/tools/` vêm da cópia experimental. Os scripts de inicialização preservam o layout daquela cópia; não iniciar diretamente a partir deste snapshot de fontes.

## Evidência anterior à regra de não controlar o PC

- 43 testes do servidor na árvore experimental: 39 testes de progressão/cartas/idioma e quatro testes de migração/configuração/autenticação/asset.
- Cliente 1.17.0: configuração local, `pcAuth`, `session/start`, tabelas reconstruídas, perfil/lobby HTTP e conexão TCP observados.
- Lobby renderizado com personagem e menus. Um ajuste encerra a sobreposição de carregamento após a inicialização nativa do lobby.
- Preferências gerenciadas isoladas em arquivo; save experimental separado do save de referência.
- Testes anteriores usaram instrumentação Frida e acionamento de métodos de interface. Essa forma de testar fica suspensa pela nova instrução do usuário.

## Limitações

- Ainda são utilizadas tabelas reconstruídas a partir da base antiga. As tabelas novas completas e suas chaves originais não foram recuperadas.
- Assets recentes presentes no cache não equivalem a personagens, modos ou habilidades funcionais.
- Combate, progressão no cliente novo, entrada manual após reabertura e integridade completa do save ainda exigem validação.
- Os patches em memória dependem de hashes/offsets exatos e têm escopo experimental.
- Manter o manifesto completo de 8.213 entradas do cache. A tentativa de filtrá-lo foi revertida; o catálogo nativo tem 8.204 bundles e não descreve sozinho todas as entradas necessárias à inicialização.
- Launcher gráfico e runtime experimental não estão integrados neste checkout. Portas do launcher original e do experimento precisam ser conciliadas antes de uma distribuição.

## Roteiro anterior — suspenso

1. Encerrar outras sessões experimentais. Abrir o `.cmd` de início somente na cópia experimental completa.
2. Aguardar a introdução e o fluxo normal de login; não avançar antes da autenticação e do carregamento das tabelas.
3. Registrar se título, login, lobby e menus aparecem na janela visível.
4. Encerrar pelo `.cmd` de parada. Reabrir e confirmar que as preferências persistem e o lobby volta a carregar.
5. Relatar qualquer bloqueio com etapa, mensagem e horário. Não usar credenciais oficiais: o servidor é local e usa o perfil da cópia experimental.

Não solicitar nem executar esse roteiro automaticamente. Aguardar uma rodada de teste combinada com o usuário.
