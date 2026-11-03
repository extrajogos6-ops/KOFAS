# Recuperação da 1.17.0 — opção A

## Objetivo autorizado

Preservar o conteúdo mais recente, disponibilizar os personagens e implementar as mecânicas de aprimoramento da própria 1.17.0. Não importar arquivos, tabelas, saves ou mods da 1.11.2. Criar perfil novo quando houver dados suficientes para implementar o serviço fielmente.

O experimento híbrido anterior permanece suspenso. Esta investigação não aplicou patches ao cliente, não iniciou o jogo nem alterou as instalações originais. Ainda não existe uma distribuição nativa 1.17 pronta para jogar.

## Evidência obtida nesta etapa

Fonte: `Desktop/Projeto Codex/kofg2/kofg`, original 1.17.0. SHA-256 de `GameAssembly.dll`: `07beb870deee2a580d140041ad629e7149ed5a887d76323c36e63c9b532c03e2`.

1. **Índice local de tabelas lido.** `tablepacks.info` contém mensagens protobuf delimitadas pelo campo 7, coerentes com `TableUpdateManager.kPackDelimiter = 58`. Foram identificados os pacotes `table`, versão 10613, com 430 entradas; `lang_global`, versão 10270, com 168; e `prohibited`, versão 1, com 2. As 600 tabelas estão presentes e seus tamanhos correspondem ao índice. As entradas lidas não contêm o campo de hash: esta conferência de tamanho não comprova integridade criptográfica nem validade do conteúdo. O pacote de banners não faz parte dessa conferência.

2. **Preferências originais descriptografadas.** A rotina `NMRestApi.PlayerPrefs.Load`, RVA `0x9876B0`, usa duas strings de 16 bytes do próprio metadata, conversão para hexadecimal e AES-CBC/PKCS7. A implementação reproduzida fora do jogo produziu JSON válido com 1.311 entradas. Não foram encontradas propriedades com nomes referentes a cipher, security, token, session ou encryption. O conteúdo privado fica fora do Git e não será convertido em save da nova distribuição. A ausência desses nomes não exclui informação codificada sob outro nome.

3. **Origem das chaves das tabelas confirmada no código.** `NetworkManagerWEB.TakeTableSecureKey`, RVA `0x186F220`, copia os campos da resposta `SessionStartResponse.SecurityDataTable` e `SecurityLocalizing` para as estruturas em memória do gerenciador de rede. Isso explica a dependência da resposta de servidor; essa função não deriva as chaves a partir dos assets.

4. **Cadeia de leitura das tabelas mapeada.** `SecureKey.CreateCrypto`, RVA `0x18A9350`, interpreta chave e IV como hexadecimal e configura AES-CBC/PKCS7. `BaseTable.DecryptAndLoadTable`, RVA `0xD07020`, descriptografa, chama `DecompressAndOptimize`, RVA `0xD070E0`, que abre um ZIP com Ionic.Zip, e valida MD5 antes de entregar os bytes ao leitor de tabela. Contornar o login ou a verificação não recupera os dados criptografados.

5. **Sondagem limitada de constantes originais.** Foram testados 937 candidatos de chave e 473 de IV extraídos exclusivamente de literais imprimíveis e hexadecimais do metadata 1.17, contra a assinatura inicial comprimida de uma tabela (`accountlevelingtable.bin`). Nenhum par produziu a assinatura ZIP/GZIP esperada. É uma busca restrita: não prova que não exista chave recuperável, derivada ou armazenada em outro formato. Não foi uma quebra do AES nem validação de todas as tabelas.

6. **Busca limitada por resposta preservada.** Foram lidos 8.227 arquivos de até 2 MiB da base 1.17, excluindo PNG, DLL e EXE, totalizando 2.667.536.330 bytes. Nenhuma ocorrência ASCII literal de `SecurityDataTable`, `SecurityLocalizing` ou `EncryptionKey`. Respostas comprimidas, binárias ou criptografadas podem não apresentar esses nomes. O usuário informou que só possui os clientes fornecidos, sem captura de login, servidor ou tabelas em claro.

7. **Pacote embutido inspecionado.** `resourcesassets_builtintable` contém 16 TextAssets: traduções `BuildSystemTable_*`, conjuntos de caracteres permitidos e caracteres proibidos. Não contém as tabelas de personagens ou aprimoramentos buscadas. Outros 16 arquivos iniciais de assets foram lidos sem erros; os TextAssets encontrados são configuração de URL/faturamento, lista de sons e dados visuais Spine. Isso não equivale a inspecionar semanticamente todos os bundles de conteúdo do cache.

## Situação e critério de avanço

A recuperação das tabelas originais continua pendente. **Nenhuma das 430 tabelas de gameplay foi declarada descriptografada ou substituída.** Não há evidência suficiente para prometer que todos os personagens e aprimoramentos possam ser reconstruídos fielmente apenas com os materiais atuais.

O bloqueio imediato é obter as chaves originais correspondentes ou outra cópia válida dos mesmos dados 1.17. Rotas ainda possíveis incluem outra representação nos materiais originais e material de preservação com procedência verificável. Não tratar o tempo de investigação como garantia de recuperação. Criar um servidor com dados antigos ou inventados não resolve este bloqueio e viola o escopo escolhido.

Depois da recuperação, ainda será necessário: validar ZIP/CRC/protobuf e referências; catalogar o conteúdo; implementar o protocolo e perfil novos; implementar regras e persistência; validar combate e aprimoramentos com testes automáticos e rodada manual do usuário. O [plano](../superpowers/plans/2026-11-02-opcao-a-117.md) separa esses critérios.

## Preservação e reprodução

- Manifesto local: `outputs/KOFAS-117-Nativo/procedencia-original-117.json`, com SHA-256 das 600 tabelas e seis arquivos de referência. Não é uma cópia executável do jogo.
- Ferramentas novas: UnityPy 1.25.4 e dependências em `work/tools/option-a-pythonlibs`; wheels conferidos contra SHA-256 publicado no PyPI. O pacote `tpk_ar` foi extraído do fonte, sem instalar no sistema. O registro de wheels não inclui esse fonte nem representa um lockfile completo.
- Python portátil e biblioteca criptográfica genérica preexistentes foram usados como ferramentas de análise. Nenhum dado do jogo antigo foi importado.
- Decompilações e preferências descriptografadas permanecem em `work/`, fora do repositório. Não publicar seu conteúdo.
- Evidências não privadas: [índice de tabelas](opcao-a-evidencias/tablepack-check.json), [sondagem de literais](opcao-a-evidencias/literal-probe.json), [busca limitada](opcao-a-evidencias/security-scan.json), [pacote embutido](opcao-a-evidencias/builtin.json), [assets iniciais](opcao-a-evidencias/initial-assets.json).
- Graphify: consultado em `f596b0c97ba305b480d3fd74fa955a4d4a0e931b`, igual ao HEAD inicial. As consultas de instruções/status retornaram `README.md`; documentos novos não têm definição exata. Não declarar cobertura desses arquivos ou dos binários. Registro em `docs/impact/2026-11-02-opcao-a.md`.
