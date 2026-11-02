# Correção do escopo e entrega da análise comparativa

O usuário esclareceu que solicitou mapear diferenças e avaliar esforço antes de escolher entre reparar 1.17 e portar funções para 1.11. A implementação híbrida anterior não corresponde a esse objetivo. Ela fica suspensa; não é evidência de conteúdo novo funcional.

Arquivos alterados nesta entrega: instruções `AGENTS.md`, README/STATUS para indicar suspensão e novos documentos/dados em `docs/assessment`. Nenhum cliente, runtime, servidor, tabela ou save foi alterado. Nenhum jogo foi aberto ou controlado nesta revisão.

Graphify: índice `0315909bdf1e6549e5235b29a5b03a0b6d2b39c4`, igual ao HEAD antes da entrega. `server/local_player.py` teve correspondência exata; AGENTS/STATUS resolveram semanticamente para README, o que não foi aceito como análise exata desses arquivos. README foi consultado pelo seu próprio caminho; documentos e regras foram lidos localmente. Os binários não estão no índice, portanto foram examinados separadamente, somente em leitura.

Verificações: extração nova de ambos os clientes originais, SHA-256 dos dumps, comparação de campos, comparação de arquivos cifrados, teste negativo de chaves antigas e cruzamento de números do relatório com os JSONs anexos. As contagens foram conferidas sem tratar nomes iguais ou esquemas iguais como prova de equivalência funcional.

Rechecagem da instalação funcional contra o backup: 55 arquivos mutáveis divergentes (save/logs/PID/preferências/cache); nenhum arquivo novo. A origem dessas mudanças não foi atribuída. O relatório não repete a afirmação de que toda a instalação em uso continua idêntica ao backup. O backup congelado segue sendo a referência.

Pendências de configuração/documentação do Playwright anteriores a esta entrega permanecem separadas. Nenhuma nova implementação de migração será iniciada sem a escolha explícita do usuário após esta análise.
