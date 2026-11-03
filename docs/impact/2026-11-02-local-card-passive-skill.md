# Skill Up de cartas passivas na instalação local 1.11.2

## Escopo e causa

O usuário pausou a opção A e autorizou corrigir a instalação funcional `KOF ALLSTAR Local`. Esta é uma exceção explícita à regra anterior de manter essa instalação intocada. A correção não participa da migração 1.17, que continua pausada.

O servidor normal incrementava apenas `SkillLevel`. Cartas sem skill ativa usam os níveis passivos para exibição e efeitos. A tentativa capturada para a carta 1259, índice 60491, consumiu dez materiais; o save ficou com `SkillLevel: 10`, `PassiveLevel1: 1` e `PassiveLevel2: 1`. `SkillExp: 0` também foi observado, mas a correção não altera a fórmula anterior de skill normal nem depende desse campo.

Análise estática do binário local, SHA-256 `f110ae6b45b384e0f074f9837762bc3062484b9271ad4d58e779615524f314cc`: `CharacterData.BattleCard.get_CombineSkillLevel`, RVA `0x11BE490`, distingue o buff despertado, a skill ativa e o primeiro efeito passivo para tipos 2/4. Isso confirma que responder somente com `SkillLevel` não avança o nível exibido nessas cartas. Decompilação feita em Ghidra sem iniciar/instrumentar o jogo.

## Graphify e impacto

Índice e HEAD inicial iguais: `a81a604332300dd9a838d4277a12de55cfb049e6`. `list_repositories` confirmou autorização e índice pronto. `graphify_file_neighbors` retornou os arquivos exatos `server/local_player.py`, `server/local_card_progression.py` e `server/tests/test_card_skills.py`. Fontes locais de progressão e jogador coincidiam com os fontes instalados antes da correção.

`graphify_impact(card_route)` identificou a chamada de `route_overrides` e dependências `consume_cards`, `card_defs`, `card_max_exp`, `lc_card` e `save`. `graphify_impact(battle_cards)` identificou `account_profile_response`, que monta a coleção no login. `graphify_tests_for(server/local_player.py)` relacionou `test_card_skills.py` e `test_progression.py`; ambos foram executados. O índice não cobre o save privado nem a decompilação. A consulta de `AGENTS.md` retornou `README.md`, sem cobertura exata; a autorização de escopo vem diretamente do usuário.

## Mudança

- `server/local_player.py`: sincroniza níveis de slots passivos existentes, somente em cartas sem skill ativa; não reduz níveis nem altera slots ausentes ou buffs de despertar. O upgrade atualiza a resposta camelCase e a persistência. A leitura da coleção recupera níveis anteriormente pagos usando o `SkillLevel` já registrado, sem cobrar novamente. Skill normal no limite é rejeitada antes de consumir materiais/ouro.
- `server/tests/test_card_skills.py`: reprodução da falha, persistência, reconciliação idempotente, cobrança no limite e resposta HTTP criptografada compatível com o cliente.
- Instruções do projeto: registrar pausa da 1.17 e exceção autorizada para esta correção local.

Não foram alterados o cliente, binários, tabelas, mods, fórmulas gerais de ganho de skill ou economia. A progressão da skill de despertar mantém seu ramo próprio.

## Evidência e instalação

Antes da implementação, os três novos testes de unidade falharam pelos comportamentos esperados: passivos permaneceram em 1, perfil não foi reconciliado e skill no limite ainda consumiu. Após a correção, 43 testes unitários/HTTP passaram, incluindo os testes anteriores de despertar e progressão. A fixture de migração foi completada com os slots zerados já existentes em materiais reais; isso evitou confundir a inicialização anterior desses campos com uma cobrança ou mudança de inventário.

Comando: Python portátil da instalação, `-B -m unittest discover -s outputs/KOFAS/server/tests -v`. Perfis temporários e HTTP em porta efêmera; nenhuma requisição de teste ao servidor do jogador.

Simulação sobre cópia do save atual: somente cinco campos de nível passivo em três cartas (1065, 1259 e 1260) passaram de 1 a 10, correspondendo ao `SkillLevel` já registrado. Todos os demais campos permaneceram iguais, incluindo ouro, quantidades de materiais e personagens. Uma segunda leitura não fez nova gravação.

Backup verificado: `outputs/KOFAS-CardSkill-Fix-20261102-215138/backup-manifest.json`. Inclui fonte anterior, save e instruções externas ao Git. Nesse diretório também ficam o resultado da simulação, perfil privado simulado, log dos testes e manifesto da instalação; não versionar dados privados.

Somente `local_player.py` foi substituído no servidor instalado, por cópia idêntica ao fonte testado. O save ativo não foi editado diretamente; a reconciliação ocorrerá na montagem normal da coleção no próximo login pelo servidor novo. A sessão aberta não foi encerrada e seu servidor continua com o código antigo em memória até o usuário fechar e reabrir o launcher/jogo. Não basta trocar a aba dentro da sessão atual.

Validação visual pendente do usuário: fechar completamente jogo e launcher, abrir novamente pela instalação local, acessar as três cartas e conferir o nível dos efeitos na aba Skill Up. As cartas já pagas devem mostrar nível 10 sem novos materiais; para uma carta ainda abaixo do limite, confirmar avanço após upgrade e persistência ao reabrir. Conferir a disponibilidade de Awaken conforme os demais requisitos normais da carta. Nenhum teste autônomo controlou o PC.
