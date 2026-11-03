# Rank 500, DIAMOND I e fundo do lobby local

## Escopo autorizado

O usuário confirmou o funcionamento do Awaken linear e pediu três ajustes na instalação funcional 1.11.2: rank 500, classificação DIAMOND I e um fundo apropriado do próprio jogo. A investigação da 1.17 continua pausada. A instalação foi concluída em 03/11/2026 sem iniciar/encerrar processos ou controlar a interface.

## Rank

A tabela reconstruída `AccountLevelingTable` tinha 100 linhas. A análise estática do cliente instalado confirmou que `GetAccountLevel` (RVA 0x722A70) procura a primeira linha com EXP acumulada maior que a EXP atual e que `GetAccountMaxLevel` (0x722E90) lê a última linha. Colocar EXP muito alta sem estender a tabela não representa rank 500; ultrapassar todos os intervalos pode retornar 1.

O gerador `scripts/local_lobby_account_setup.py` preserva as primeiras 100 linhas e acrescenta 101–500 segundo a curva local existente: requisito de EXP igual a 100 × nível, EXP acumulada pela soma e custo de equipe continuando a progressão anterior. Não se trata de uma tabela oficial recuperada. O intervalo válido do rank 500 é 12.475.000–12.524.999 de EXP.

`server/local_account_preset.py` lê uma configuração opcional do runtime. Ela identifica a conta local e aplica a promoção pela leitura/gravação normal do perfil. A integração em `local_player.load/save` mantém a EXP no intervalo de rank 500 e `LastAccountLevel` em 500. Sem configuração ou em outra conta, não altera nada. O perfil ativo não foi substituído por uma cópia ou editado externamente.

## DIAMOND I

A classificação do bônus da conta deriva do modo Absolute War e de `AccountExtraList.mode209Tier`, não do rank da conta nem das divisões de outros modos. A faixa 25 do `AllOutFightGradeTable` tem limite 3400 e referência `/Diamond1`. O `AccountTierBonusTable` existente confere HP +1000, ATK +100, DEF +50 e PEN +100, correspondendo ao exemplo do usuário.

O preset promove `AllOut.Rating` e `Best` para pelo menos 3400 e `PrevGrade` para 25. Preserva vitórias, personagens usados, tentativas e demais contadores. Um marcador de revisão impede reaplicar a promoção após partidas posteriores; as regras de temporada permanecem existentes. Não foi alterada a classificação de League, Colosseum ou outros modos.

## Fundo

Foram lidas 129 texturas de bundles do próprio cliente 1.11, sem iniciar o Unity. A textura atual contém duas composições na mesma imagem quadrada; a metade inferior inclui a vista girada que aparece na captura. A análise de `UIView_Lobby.SetLobbyBg` (0x4C2630) confirmou o recorte UV `(0, 0.5, 1, 0.5)` quando `BGThumbnailPosition = 1`; com 0, selecionava a metade inferior. O modo de ocultar interface usa a posição vertical análoga.

Foi escolhida `Texture_Lobby_SS_Terry`, uma paisagem urbana com a arena e letreiros de KOF, presente no bundle `prefabs_ui_data_ui_texture_backgroundstage`. O container original confirmou o asset `assets/resources_assetbundles/prefabs/ui_data/ui_texture/backgroundstage/texture_lobby_ss_terry.png`.

Todas as linhas locais de `LobbyBGSettingTable` apontam agora para esse recurso, com posições horizontal e vertical em 1. O executável, os bundles, as texturas e os mods não foram modificados. A prévia do recorte foi extraída apenas para inspeção; o jogo utiliza o recurso original.

## Graphify e impacto

Índice inicial e HEAD: `aeb82dc3b3cf655ee05a2a68fbd16020d8d7d0ff`. `list_repositories` confirmou autorização e prontidão. Cobertura exata de arquivos: `server/local_player.py` e `scripts/local_awaken_balance.py`. Consultados impacto de `account_profile_response`, `save()` e `load()`, e testes ligados a `local_player.py`.

`save()` resolveu corretamente para o jogador, mas o resultado foi truncado; seus muitos consumidores podem observar a configuração opcional. `load()` resolveu inicialmente para o launcher e também listou o jogador entre sementes: isso não constitui um mapa exato dos consumidores da leitura do jogador. As funções locais e o uso pelo handler HTTP foram conferidos no código. Os testes exercitam a configuração ativa e inativa, persistência e os fluxos anteriores de cartas/progressão.

Arquivos novos, dados criptografados, perfil e imagens não têm cobertura anterior. A consulta de `AGENTS.md` retornou `README.md`, sem cobertura exata das instruções. A autorização para dados e perfil vem do pedido explícito do usuário; a limitação do índice foi mantida no registro, sem inferir ausência de dependências.

## Testes e instalação

Antes da implementação, cinco testes falharam por nível máximo 100, fundo/recorte incorreto, ausência da configuração de promoção e EXP/rank ainda antigos. Depois: **63 testes aprovados**, por `python -B -m unittest discover -s outputs/KOFAS/server/tests -v`. Incluem fronteiras de EXP usando o comportamento nativo, DIAMOND I e bônus reais, aplicação/releitura do preset, não repetição da promoção, outras contas, tabelas e níveis anteriores intactos, MD5, recorte, idempotência e composição com o Awaken linear. A suíte anterior de Skill Up/Awaken também passou.

Simulação com cópia do save mais recente: apenas seis caminhos mudaram — `PlayerAccount.Exp`, `LastAccountLevel`, `AllOut.Rating`, `AllOut.Best`, `AllOut.PrevGrade` e o marcador novo. Cartas, personagens, itens, dinheiro e todos os demais campos permaneceram iguais. As respostas de bônus indicaram a faixa 25. O save usado para simulação permanece privado fora do Git.

Runtime instalado: fontes `local_player.py` e `local_account_preset.py`; `account-preset.json`; `packs-claude/table.dat`, `table.kof` e `table-versions.json`. A versão de tabela passou de 20586 para 20587. Idioma permanece em 20586, mantendo as descrições dinâmicas do Awaken. Somente duas tabelas foram alteradas neste pacote: rank e configuração do lobby; os buffs normais e de Awaken permaneceram byte a byte iguais aos dados anteriores.

Backup final verificado: `outputs/KOFAS-Lobby-Conta/backup-final-20261103-002930/`. Inclui código anterior, packs/manifests/versão e save mais recente; novos arquivos foram registrados como anteriormente ausentes. Há também backup anterior das instruções e o registro `deployment.json` com hashes dos seis arquivos instalados. Não restaurar um save anterior sobre progresso posterior sem comparação.

Os perfis e packs modificados não são versionados. O repositório mantém o gerador, a lógica do preset, testes e documentação; as fixtures criptografadas antigas continuam sendo a referência de regressão, não uma distribuição a copiar de volta sobre o runtime.

Validação visual pendente: fechar completamente o jogo/launcher e abrir novamente pela instalação local. Conferir rank 500, insígnia e painel DIAMOND I e fundo urbano orientado corretamente, inclusive ao ocultar a interface. Nenhum teste de desktop foi executado; não se afirma que a interface foi validada automaticamente.
