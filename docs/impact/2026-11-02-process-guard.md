# Correção da verificação de sessão anterior

## Problema observado

O usuário abriu o CMD e recebeu `Não foi possível verificar a identidade do processo experimental` antes da criação de uma nova sessão.

A leitura de `active-probe.json` apontou PID 18832. A consulta nativa somente de leitura confirmou: `OpenProcess` teve sucesso; `GetExitCodeProcess` retornou 3489660927 (processo encerrado); `QueryFullProcessImageNameW` falhou com erro Windows 31. Logo, abrir um handle não demonstrava que o jogo ainda estivesse ativo.

## Graphify e impacto

Índice consultado: `898b7837682cf530f9d8c0de69893c10cfc388f9`.

- Arquivo exato: `migration/1.17.0/tools/run_experimental.py`.
- `graphify_callers(running_experimental_game)` encontrou `main()` como chamador direto.
- `graphify_tests_for` não encontrou testes relacionados; foram adicionados testes sem interface ou jogo.
- O vizinho inferido `server/lobby_tcp.py` não foi tratado como dependência exata da WinAPI. O fluxo local foi lido diretamente.
- Nenhuma mudança em assets, hashes permitidos, autenticação, save ou instalação funcional 1.11.2.

## Alteração e validação

Consultar o código de saída antes da identidade. Processos já encerrados não bloqueiam a abertura. Se a consulta de identidade falhar, verificar novamente se houve encerramento entre as duas chamadas. Processos ativos com identidade desconhecida continuam bloqueados.

O teste do erro original falhou antes da correção. Oito testes passaram depois: processo encerrado com handle existente, saída durante a consulta, identidade correspondente, PID reutilizado por outro executável, identidade ativa desconhecida, estado de saída desconhecido, PID ausente e marcador ausente.

A cópia instalada foi protegida por backup com SHA-256 antes da substituição. O arquivo corrigido instalado é idêntico à fonte versionada. A chamada real à verificação retornou `False` com o marcador que causava o erro, sem abrir jogo ou Frida. A validação da interface continua manual.
