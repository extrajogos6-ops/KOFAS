# Substituição do fundo rejeitado por desfoque

O usuário rejeitou o fundo `Texture_Lobby_SS_Terry` após testá-lo no jogo: a imagem já tem desfoque no recurso original e a ampliação torna isso mais evidente. A seleção anterior usou uma imagem inadequada para a nitidez solicitada. Rank 500 e DIAMOND I aparecem funcionando na captura; não são objeto desta correção.

## Seleção e limite da validação

Foram comparados os recortes horizontais originais de cinco fundos, incluindo o rejeitado, com ampliações para 1920 × 1080 e recortes da imagem ampliada. Também foram inspecionadas 298 texturas do pacote Spine; elas tinham somente 512 × 512 e não ofereciam uma alternativa de maior resolução. Os dois pacotes de Collection Room consultados não estavam disponíveis nos caches 1.11 inspecionados.

Foi escolhido `Texture_Lobby_KOFXV`, presente no mesmo bundle original `prefabs_ui_data_ui_texture_backgroundstage`. A composição apresenta contornos e detalhes mais definidos que o fundo rejeitado. Mantido o recorte da metade superior, sem a composição girada. A resolução original continua sendo 1024 × 1024, com recorte horizontal de 1024 × 512: não houve ganho de resolução, geração de detalhes, sharpening nem alteração de pixels do asset usado pelo jogo.

A comparação visual realizada foi de arquivos estáticos, fora do jogo; não comprova automaticamente a aparência final do Unity. A prévia ampliada não é uma captura do jogo. O usuário continua responsável pela rodada manual da interface, conforme a regra principal do projeto.

## Mudança e preservação

`scripts/local_lobby_account_setup.py`: alterar somente a constante `BACKGROUND` de `Texture_Lobby_SS_Terry` para `Texture_Lobby_KOFXV`. O gerador continua reproduzindo os demais ajustes anteriormente autorizados.

Na instalação, foram aplicados somente `packs-claude/table.dat`, `table.kof` e `table-versions.json`. Dentro do pack, apenas `lobbybgsettingtable.bin` mudou; em suas linhas, somente os campos 3 e 7, referentes ao caminho do fundo. Posições de recorte, níveis da conta, efeitos normais e de Awaken permaneceram iguais. Todos os outros arquivos internos criptografados foram comparados byte a byte. `account-preset.json` também ficou idêntico e não foi reinstalado. Nenhum fonte do servidor, save, bundle, executável ou mod foi alterado.

Versão de tabela: 20587 → 20588. Idioma permanece 20586. O incremento permite recarregar a referência nova sem apagar o cache. O save ativo não foi editado nem substituído.

## Graphify e testes

Graphify autorizado e pronto, índice `d3c8df485d939db6dc17962272184b811688bf1e`, igual ao HEAD inicial. `graphify_file_neighbors(scripts/local_lobby_account_setup.py)` retornou o arquivo exato, dependências de codec e `server/tests/test_account_lobby.py`; `graphify_tests_for` confirmou esse teste. A consulta de `AGENTS.md` retornou `README.md`, sem cobertura exata das instruções. Imagens e packs privados não são cobertos pelo grafo.

63 testes existentes aprovados: `python -B -m unittest discover -s outputs/KOFAS/server/tests -v`. A mudança de referência não recebeu teste que apenas repetisse a nova string; foram executados os testes reais de configuração/recorte, preservação das tabelas, idempotência, manifests e das funções anteriores. Conferidos todos os MD5s dos protobufs do pack e CRCs dos ZIPs antes de instalar.

Backup verificado em `outputs/KOFAS-Lobby-Nitidez/backup-20261103-004551/`, incluindo os três arquivos anteriores, save atual e instruções externas. `deployment.json` registra os hashes instalados; `comparacao.png` e as prévias originais documentam a comparação. As instruções do projeto agora exigem inspecionar o recurso e o recorte na escala da tela, sem tratar miniaturas ou ampliação como prova de qualidade.

Para validar: fechar completamente jogo e launcher e abrir novamente pela instalação local. Conferir o cenário novo e sua nitidez. Nenhum processo foi iniciado/encerrado ou interface controlada durante o trabalho.
