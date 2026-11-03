# Conta local: rank 500, DIAMOND I e lobby correto

**Objetivo autorizado:** rank da conta 500; classificação DIAMOND I; fundo próprio do cliente 1.11, com orientação correta. A 1.17 continua pausada. Não controlar a interface em testes nem editar o perfil enquanto o jogo está aberto.

**Evidência:** a tabela local de níveis termina em 100, com requisitos `100 × nível` e EXP acumulada triangular. `GetAccountLevel` (RVA 0x722A70) retorna a primeira linha cujo limite de EXP acumulada ainda não foi alcançado; `GetAccountMaxLevel` (0x722E90) lê a última linha. É necessário estender a tabela e limitar a EXP no rank máximo para não ultrapassar o último intervalo. DIAMOND I corresponde à faixa 25/3400 pontos de Absolute War, usada pelo bônus da conta através de `mode209Tier`.

**Fundo:** `Texture_Lobby_SS_Terry`, original do bundle `prefabs_ui_data_ui_texture_backgroundstage`, presente no cliente local 1.11. A textura combina paisagem e composição vertical. `UIView_Lobby.SetLobbyBg` (0x4C2630) usa metade superior quando `BGThumbnailPosition = 1`; o valor atual 0 seleciona a metade com composição girada. Alterar referências e posições na tabela, sem editar assets/binários.

## Arquivos e etapas

- [x] `scripts/local_lobby_account_setup.py`: gerar três arquivos de tabela/manifest/versão e configuração `account-preset.json`; preservar todos os outros dados, inclusive Awaken linear. Reutilizar codec/criptografia do gerador anterior sem modificá-lo.
- [x] `server/local_account_preset.py`: aplicar rank/EXP e promoção uma vez somente à conta configurada; limitar EXP ao intervalo de rank 500 em gravações futuras. Desabilitado quando não há configuração.
- [x] `server/local_player.py`: integrar o preset na leitura/gravação normal do perfil; sem editar save ativo por script externo.
- [x] `server/tests/test_account_lobby.py`: regressões de nível, limites, tier real, persistência, não duplicar promoções, outros perfis, preservação do inventário/recursos e tabelas não relacionadas.
- [x] Backup verificado de fontes/dados alterados e save; testar numa cópia do perfil e ler os packs instalados para conferir hashes.
- [x] Instalar os fontes e packs. Não reiniciar processos; usuário reinicia jogo/launcher e valida rank, insígnia e enquadramento.
- [x] Registrar impacto e versionar somente fontes/testes/documentação. Manter perfis, packs e previews derivados fora do Git.

**Progressão e bônus:** criar linhas 101–500 coerentes com a curva local; não reconstruir valores oficiais. Rank 500 começa em EXP 12.475.000 e termina em 12.524.999. A promoção define Rating/Best pelo menos 3400 e PrevGrade 25, preservando contadores e progresso do modo. Bônus esperados da tabela existente: HP +1000, ATK +100, DEF +50, PEN +100. A promoção não é reaplicada após o marcador de revisão; partidas posteriores seguem as regras do modo.

**Limites:** testes de arquivo/API não comprovam o visual do Unity. Essa validação continua manual. Índice Graphify inicial igual ao HEAD: `aeb82dc3b3cf655ee05a2a68fbd16020d8d7d0ff`; consultar integrações e registrar ausência de cobertura dos novos arquivos, JSON e binários.

Instalação concluída em 03/11/2026; 63 testes aprovados. Validação visual permanece manual e pendente.
