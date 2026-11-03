# Awaken local 1.11 — efeitos adicionais lineares

## Pedido e regra adotada

O usuário confirmou que a correção anterior de Skill Up funcionou. Solicitou preservar os status anteriores ao despertar e, depois de escolher entre as curvas, aprovou explicitamente a proporção direta em todos os status de Awaken, níveis 1 a 6. A opção A/1.17 permanece pausada.

Regra: `poder = base × awakeBuffLevel`, com teto no nível 6. O nível da opção não é a quantidade de estrelas: a quinta estrela permite evoluir a opção até 6 por Skill Up. A sequência existente de aprimoramento continua válida; este balanceamento não pula níveis nem cobra materiais para atualizar efeitos já adquiridos. É uma personalização autorizada da instalação local reconstruída, não um balanceamento oficial recuperado.

## Investigação e preservação

O save preservava `Stat`, EXP, índices e níveis dos passivos da carta despertada. A análise estática do executável instalado (`GameAssembly.dll` SHA-256 `f110ae6b45b384e0f074f9837762bc3062484b9271ad4d58e779615524f314cc`) mostrou:

- `BattleCardStatCalculator.TotalAttack`, RVA `0x127D920`: mantém atributos próprios e crescimento pelo nível normal da carta.
- `CharacterData.BattleCard.CreateBuff`, RVA `0x11C09E0`: acrescenta o buff de despertar, o buff de evolução quando aplicável e os passivos normais; não substitui os anteriores.
- `BuffProto.Description`, RVA `0x1C65410`: configura o nível da opção no `StringProvider` e executa o formatador sobre a descrição localizada.
- `StringFormatter.InternalFormat`, RVA `0x10756B0`, e `AddFormatted`, RVA `0x1075C60`: aceitam tokens entre chaves, incluindo o conversor `buffPower`. `StringProvider.ConverBuffPower`, RVA `0x53B370`, calcula base + incremento × (nível − 1) e aceita multiplicação para a exibição percentual.

Portanto, a perda dos atributos anteriores não foi reproduzida; o painel `Current Awaken Skill` apresenta o bônus de despertar, não uma lista de todos os atributos da carta. O valor fixo exibido foi confirmado: a tradução de `Buff.910044.Desc` era literalmente `ATK +80`, embora a tabela numérica previsse incremento 8 por nível. A análise inicial parcial sugeriu uma referência ausente; a leitura completa confirmou que as nove referências existiam. Não houve alteração para tratar uma referência inexistente.

## Implementação

Gerador: `scripts/local_awaken_balance.py`. Lê somente os packs reconstruídos da 1.11, reconhecidos pelas nove opções 9320–9322, 9330–9332 e 9340–9342. Não usa material da 1.17.

Cada opção aponta agora para um efeito exclusivo (`9900000 + índice da opção`). Os nove efeitos antigos são preservados, pois podem ser reutilizados por cartas normais. Os clones mantêm todas as propriedades exceto identidade, tags de localização, incremento (igual à base) e teto (seis vezes a base). As definições das cartas, buffs normais e demais entradas de tabela são preservados. Nenhuma alteração do servidor de perfil ou do cliente foi necessária.

As descrições novas usam `{buffPower}` ou `{buffPower*100}%`, interpretados pelo formatador do cliente. O título do efeito passa a indicar o atributo, como `Awaken ATK`, para não exibir um número fixo incompatível com a descrição por nível. Não foram alteradas as descrições dos efeitos normais.

| Opção | Atributo | Lv.1 | Lv.2 | Lv.3 | Lv.4 | Lv.5 | Lv.6 |
|---|---|---:|---:|---:|---:|---:|---:|
| 9320 | HP | 900 | 1800 | 2700 | 3600 | 4500 | 5400 |
| 9321 | ATK | 80 | 160 | 240 | 320 | 400 | 480 |
| 9322 | DEF | 40 | 80 | 120 | 160 | 200 | 240 |
| 9330 | ATK | 120 | 240 | 360 | 480 | 600 | 720 |
| 9331 | Crítico | 3% | 6% | 9% | 12% | 15% | 18% |
| 9332 | Penetração | 150 | 300 | 450 | 600 | 750 | 900 |
| 9340 | HP | 1200 | 2400 | 3600 | 4800 | 6000 | 7200 |
| 9341 | DEF | 50 | 100 | 150 | 200 | 250 | 300 |
| 9342 | ATK | 100 | 200 | 300 | 400 | 500 | 600 |

Foram substituídos somente cinco arquivos da instalação: `packs-claude/table.dat`, `table.kof`, `lang_global.dat`, `lang_en.kof` e `table-versions.json`. Manifests criptografados recalculados com MD5 dos protobufs em claro. Versões `table` e `lang_global`: 20585 → 20586; versões de banners e proibidos inalteradas. A versão é publicada por último. O script é idempotente: uma segunda execução não duplica efeitos nem incrementa versões.

## Graphify

Repositório pronto e autorizado, índice `7d7f287eda2f2bafeeae3218687c5743fef31d0a`, igual ao HEAD inicial. Consultados `server/local_player.py`, `server/server.py`, `server/tests/test_card_skills.py` e impacto de `card_awaken`. Fluxo identificado: `route_overrides` → `card_awaken` e entrega dos packs por `Handler.do_GET`. `graphify_tests_for(server/server.py)` relacionou testes de cartas, progressão, idioma e o experimento 1.17; os testes de 1.17 não foram executados, pois esse trabalho está pausado e não integra a mudança.

O índice não possui cobertura exata do gerador novo nem de `server/table-versions.json`; a consulta de `AGENTS.md` retornou `README.md`. Dados binários e save não são indexados. Não foi declarada análise de chamadas desses artefatos; seu impacto foi conferido pela leitura do handler, validação dos arquivos, preservação de entradas e HTTP isolado. A alteração das tabelas locais é a exceção diretamente autorizada pelo usuário ao escolher a regra e pedir sua aplicação a todos os status. Nenhum arquivo ou símbolo de código de entrega/perfil existente foi alterado.

## Testes e instalação

Antes da implementação, quatro regressões falharam, incluindo cálculo 88 em vez de 160 no nível 2, reutilização do buff normal, descrição fixa e ausência de mudança das versões. Depois: **52 testes aprovados** com Python portátil, `-B -m unittest discover -s outputs/KOFAS/server/tests -v`.

Cobertura nova: nove efeitos × seis níveis, porcentagem, ausência de alteração dos efeitos normais/definições das cartas, conteúdo criptografado inalterado das outras entradas, manifests MD5, ZIP/CRC, idempotência, backup verificado, perfil preservado, HTTP isolado com aliases de idioma, preservação dos campos da carta ao despertar/manter/trocar bônus. A suíte anterior de Skill Up e progressão também passou.

Os packs instalados antes da mudança coincidiam byte a byte com as fixtures usadas nos testes. Após instalar, foram lidos novamente todos os manifests e verificadas as tabelas internas, MD5 e CRCs. O save ativo continuou byte a byte igual ao backup durante essa conferência. Cliente, mods e fonte do servidor não foram alterados; a correção anterior de Skill Up permanece.

Backup e registros locais: `outputs/KOFAS-Awaken-Linear-20261102-221903/`, incluindo `backup/manifest.json`, save anterior, arquivos criptografados anteriores, SHA-256 instalados e log dos testes. Não restaurar o save antigo automaticamente sobre progresso posterior. As instruções externas ao Git foram preservadas antes de ampliar a exceção de escopo.

As fixtures ignoradas de `server/packs-claude` permanecem como base anterior para reproduzir a regressão; não copiá-las de volta sobre a instalação corrigida. O gerador reproduz a mudança e incrementa as versões do destino, sem exigir dados modificados no Git.

Nenhum processo do jogo/launcher foi encerrado ou iniciado e nenhuma interface foi controlada. A validação visual do texto dinâmico e a comparação em combate dos atributos totais continuam pendentes do usuário após reiniciar o jogo/launcher. Os testes automáticos não equivalem a uma rodada visual do cliente Unity.
