# Serviços experimentais que permaneciam abertos

## Evidência

O usuário recebeu erro de porta 18776 ocupada antes da abertura do jogo. As portas 18775/18776 pertenciam aos PIDs 31808/612. Executável e linha de comando identificaram exatamente o Python portátil desta cópia e os scripts `server.py`/`lobby_tcp.py`; o supervisor pai 24396 não estava ativo. Esses dois serviços órfãos foram encerrados após essa verificação. Nenhum processo foi escolhido apenas pelo nome e nenhum serviço original 18765/18766 foi alterado.

A parada antiga só escrevia uma flag para o supervisor, que já não existia. O encerramento dos filhos dependia do `finally` desse processo e não cobria saída abrupta do supervisor.

## Consulta de impacto

Graphify consultado para `migration/1.17.0/tools/run_experimental.py`; ainda refletia `898b783`, enquanto o HEAD local era `b9fb5a6`. A diferença local era a correção de identificação de processos já encerrados, seu teste e registro de impacto. O código atual foi lido diretamente antes da mudança de lifecycle.

Pontos afetados: criação e encerramento dos serviços em `main()`, novo helper `service_job.py` e testes CLI. Não houve mudança de protocolo, autenticação, assets, save ou interface Unity.

## Correção

Somente serviços recém-criados pelo inicializador são associados a um Windows Job Object com `KILL_ON_JOB_CLOSE`. O fechamento do handle ou a saída do supervisor encerra esses serviços. Processos e serviços existentes não são associados. As verificações de portas e de identidade do jogo continuam ativas.

Referência: https://learn.microsoft.com/windows/win32/procthread/job-objects.

## Validação

Quatro testes reais de lifecycle em Windows, usando exclusivamente filhos Python CLI descartáveis: fechar o job encerra o filho associado; preserva um filho não associado; fechar duas vezes é seguro; saída abrupta com `os._exit` também encerra o filho associado. Os oito testes anteriores de identidade continuam passando: 12 no total.

Os arquivos instalados foram comparados por SHA-256 com as fontes. O inicializador anterior foi protegido por backup local. As portas experimentais foram conferidas livres antes de pedir nova validação manual. O jogo não foi aberto nem controlado nos testes.
