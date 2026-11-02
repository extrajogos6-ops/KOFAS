# KOF ALLSTAR — diferenças, esforço e alternativas 1.11.2 → 1.17.0

**Data:** 2 de novembro de 2026. **Escopo:** análise comparativa; nenhuma implementação de atualização está aprovada por este relatório.

## 1. Resposta à decisão que precisa ser tomada

Há dois projetos diferentes:

| Caminho | O que significa | Parecer atual |
|---|---|---|
| **A — reparar a 1.17.0 para uso local** | Manter cliente, motor, código nativo, assets e dados próprios da 1.17; implementar/adaptar os serviços de que ela depende | É o candidato tecnicamente mais coerente para preservar o conteúdo recente, **mas a viabilidade completa ainda é condicional**, principalmente ao acesso aos dados corretos e ao mapeamento dos contratos do servidor |
| **B — acrescentar funções da 1.17 à 1.11.2** | Manter o motor e o código do cliente antigo e portar recursos específicos, incluindo suas dependências | Pode ser estudado para recortes pequenos. **Não há evidência para prometer paridade completa**: a troca de geração do Unity e a ausência de implementações novas no cliente antigo aumentam muito o esforço |

**Não recomendo escolher uma implementação completa agora.** A recomendação é avaliar primeiro a disponibilidade dos dados originais da 1.17 e delimitar quais funções precisam existir no resultado. Se a intenção for preservar amplamente a 1.17, A apresenta menos retrabalho estrutural. Se forem apenas alguns recursos que cabem nas estruturas antigas, B pode ter interesse, mas exige avaliação por recurso.

Não é uma simples troca de pasta, atualização de launcher ou cópia de bundles. Também não é correto classificar uma execução com tabelas antigas como implementação das funções novas.

## 2. Referências separadas e método

Foram consideradas quatro categorias, sem confundi-las:

1. **Cliente original 1.11.2:** pasta `kofg/kofg`. É a referência de código/metadados antigos antes das adaptações locais.
2. **Projeto local funcional 1.11.2:** referência congelada em `backup-local-1.11.2`, criada antes dos experimentos. Mostra o servidor, as tabelas reconstruídas e as adaptações existentes.
3. **Cliente original 1.17.0:** pasta `kofg2/kofg`. É o alvo da comparação de código/metadados e do inventário de arquivos novos.
4. **Experimento híbrido anterior:** cliente 1.17 com tabelas reconstruídas antigas e uma cópia de perfil antigo. **Está suspenso e excluído como prova de viabilidade da atualização.** Seus resultados servem apenas como histórico de uma experiência limitada.

Nesta revisão foram refeitas as extrações de metadados diretamente dos binários originais de `kofg` e `kofg2`, com Il2CppDumper 6.7.46. Os dumps obtidos conferiram com os anteriores por SHA-256. Foram comparados nomes e tipos de campos declarados no assembly do jogo, respeitando a ordem diferente dos assemblies entre versões.

Também foram lidos os arquivos de tabelas originais preservados, comparados seus nomes/bytes e repetido o teste negativo com a chave das tabelas locais reconstruídas. Isso não envolveu abrir o jogo, carregar saves, conectar ao servidor oficial ou substituir dados.

**Limites importantes:** comparar declarações não prova igualdade dos números de campo do serializador, dos valores padrão, do significado dos dados ou do comportamento em combate. A inspeção não certifica que o pacote fornecido seja a última distribuição oficial; certifica as versões identificadas nos arquivos presentes.

## 3. Motor, código e organização dos arquivos

| Item | 1.11.2 | 1.17.0 | Consequência |
|---|---:|---:|---|
| Unity | 2018.4.30f1 | 2021.3.12f1 | Motor e formatos de recursos de gerações diferentes |
| Cabeçalho de metadata IL2CPP | 24, interpretado pelo extrator como 24.1 | 29 | Exige interpretar separadamente as estruturas de cada build |
| `GameAssembly.dll` | 57.354.752 bytes | 66.566.144 bytes | Código nativo diferente; endereços/hooks antigos não podem ser presumidos válidos |
| `global-metadata.dat` | 19.925.640 bytes | 17.165.224 bytes | Tamanho não mede quantidade de funcionalidades; o formato também mudou |
| Arquivos no inventário do cliente local/novo | 8.203 | 9.803 | Há diferenças de empacotamento, cache e conteúdo |
| Bundles no cache inventariado | 7.103 | 8.213 | Presença física não equivale a integridade de dependências ou conteúdo jogável |

Na comparação anterior integral dos 7.980 caminhos compartilhados entre o cliente local 1.11 e o novo, 251 eram idênticos e 7.729 diferiam por SHA-256. Esse inventário inclui cache e adaptações locais; ele não deve ser interpretado como uma lista de 7.729 funcionalidades alteradas.

A `kofg` e o cliente local funcional têm a mesma base 1.11.2. O `GameAssembly.dll` funcional difere do original antigo em apenas 12 bytes, em dois trechos. Isso distingue patches locais de uma recompilação com o conteúdo da 1.17.

Hashes de identificação do `GameAssembly.dll`:

| Referência | SHA-256 |
|---|---|
| Original 1.11.2 (`kofg`) | `f4c656941e3760278414b49bd34b59ad3c02fe1a117fde1c69159eb60c0730ba` |
| Funcional 1.11.2 | `f110ae6b45b384e0f074f9837762bc3062484b9271ad4d58e779615524f314cc` |
| Original 1.17.0 (`kofg2`) | `07beb870deee2a580d140041ad629e7149ed5a887d76323c36e63c9b532c03e2` |

**Não é um backport manter o nome da pasta antiga e substituir motor/código pelos novos.** Nesse caso o trabalho passa a ser uma migração para o cliente novo e continua exigindo os dados e serviços correspondentes.

## 4. Assets e implicações para o caminho B

O manifesto de nomes lógicos apresenta:

- 1.132 nomes adicionados;
- 22 nomes removidos;
- 7.081 nomes compartilhados com hash de manifesto diferente;
- arquivos de cache presentes para os 8.213 nomes do manifesto novo.

Nomes adicionais incluem famílias SF6, VF5, Soulcalibur VI, `tk2` e personagens com prefixo `ue`. São evidências da presença de recursos; não demonstram seus IDs de tabela, habilidades, desbloqueio, balanceamento nem suporte do servidor.

Uma amostra de bundle usa UnityFS/formato 6 e Unity 2018 no antigo, contra formato 8 e Unity 2021 no novo. Hashes diferentes dos bundles compartilhados podem refletir serialização, compressão e conversão de versão, além de alterações reais do conteúdo. Não é possível contar todo hash diferente como arte ou função nova.

A documentação da Unity descreve bundles como dados/recursos, cujas definições de classes permanecem compiladas no cliente. Portanto, copiar um prefab não fornece ao cliente antigo a implementação de uma classe nova. Ver [manual Unity 2021.3](https://docs.unity3d.com/2021.3/Documentation/Manual/AssetBundlesIntro.html). A Unity também não oferece suporte geral ao carregamento de bundles produzidos por um Unity mais novo em um player antigo; ver [documentação oficial de compatibilidade](https://docs.unity.com/en-us/engine/6000.3/manual/assets-and-media/assets-managing-runtime/assetbundles-section/asset-bundles-intro).

**Esforço do backport de um personagem:** identificar dados, modelo, materiais/shaders, rig, animações, efeitos, sons, habilidades, comportamento de IA, ícones, dependências e mecanismos utilizados; verificar quais já existem na 1.11; converter/reconstruir recursos quando necessário; implementar o que falta; validar integração. Apenas a existência de um arquivo com o nome do personagem não resolve esse conjunto.

Não foi demonstrada nesta análise uma conversão funcional de bundles 2021 para 2018. Também não há projeto-fonte Unity completo identificado que permita simplesmente recompilar tudo para o motor antigo.

## 5. Tabelas: diferença de arquivos e diferença de estrutura

### 5.1 Arquivos originais preservados

| Grupo | Original antigo | Original novo | Adicionais | Compartilhados com bytes idênticos |
|---|---:|---:|---:|---:|
| Comuns | 384 | 430 | 46 | 0 de 384 |
| Idioma inglês | 152 | 168 | 16 | 0 de 152 |
| Proibições | 2 | 2 | 0 | Não reavaliado nesta revisão |

Nenhum nome anterior desapareceu nos grupos comuns/idioma. Porém, os bytes criptografados de todos os arquivos compartilhados desses dois grupos diferem. **Isso não prova sozinho que todos os dados legíveis mudaram**, pois a criptografia/chave também pode alterar os bytes. Prova que não se pode tratá-los como arquivos idênticos.

As chaves sintéticas do projeto local antigo produziram zero ZIPs legíveis nos 430 arquivos comuns e nos 168 arquivos de idioma novos. Trata-se apenas de um teste negativo dessas chaves. Não prova que os dados sejam irrecuperáveis nem estabelece sozinho o algoritmo exato usado no acervo novo.

### 5.2 Esquemas extraídos do código original

| Medida em `NEO.Table.Protocol` | Resultado |
|---|---:|
| Classes de dados no antigo | 431 |
| Classes de dados no novo | 479 |
| Classes compartilhadas | 431 |
| Classes novas | 48 |
| Compartilhadas com diferença nos campos privados `_...` declarados | 61 |
| Compartilhadas sem diferença nessa comparação restrita | 370 |

Essas classes não correspondem uma a uma aos arquivos de tabelas comuns; há classes de outros grupos e estruturas auxiliares. Não somar 48 classes novas às 46 tabelas como se fossem 94 sistemas distintos.

Exemplos concretos:

| Estrutura | Diferença declarada | Revisão exigida |
|---|---|---|
| `CharacterProto` | Novo `_weakTypeIndex` | Relação entre personagens e o novo sistema de fraquezas |
| `SkillProto` | 13 campos adicionais, incluindo `_switchingSkillIndex1`, `_awakenCorePtDmgPerLv`, `_accPTGBase` e dez campos `_phantomSkillDamageRLv...` | Definições de habilidades e interação com mecanismos adicionais |
| `AwakenLevelProto` | Novo `_reqAccumulatedExp6` | Progressão/curvas de despertar e custos |
| `AwakenCore*`, `CharacterSkillSet*`, `Buff*`, `Monster*`, `Stage*` | Constam entre as 61 classes alteradas | Ver o delta completo antes de reutilizar cada família de dados |

Uma declaração com campos iguais ainda pode ter regras diferentes no código ou valores diferentes nas linhas. A tabela antiga carregar no parser novo não comprova que expresse as regras da 1.17.

### 5.3 Famílias novas e dependências

| Família identificada | Novas tabelas comuns | Dependências a levantar |
|---|---:|---|
| Equipamentos | 14 `equipment*` | Inventário, presets, custos, opções, atributos, recompensa e fases |
| Artefatos | 4 `artifact*` | Catálogo, níveis, preparação de fase e relação com lutadores |
| Desafio de chefe | 3 `bosschallenge*` | Fases, penalidades, recompensas e estados do modo |
| Memória | 4 `memorygame*`/`memorysynastry*` | Fases, cartas e regras de alteração de afinidade |
| Puzzle | 3 `puzzle*` | Catálogo, subfases e recompensas |
| Runner | 3 `runnermode*` | Definição do modo, obstáculos e spawns |
| Outras | 15 | Fraquezas, penalidades de fase, controle de animação de skill, agrupamento de cores, coleção, crafting e outros |

Os números são famílias de nomes encontrados, não uma classificação oficial completa das funcionalidades. A lista dos 46 arquivos consta nos dados anexos.

## 6. Protocolo e servidor local

Na comparação de declarações públicas de `NEO.Kof.Api.Protocol`:

- 688 classes no antigo e 698 no novo;
- 687 compartilhadas, 11 novas e uma removida;
- 48 compartilhadas apresentam diferença de campos públicos declarados;
- 639 não apresentam diferença nessa comparação restrita.

Esse namespace contém requisições, respostas e estruturas auxiliares. Não são 698 endpoints.

Entre os 221 tipos de resposta usados em `api-defaults.json`, os nomes continuam presentes no cliente novo; 18 desses tipos apresentam diferenças de declaração entre versões. **Quinze templates do servidor local não incluem pelo menos um dos campos adicionais identificados.** Isso é uma lacuna para revisão, não uma prova de que todos esses campos sejam obrigatórios nem autorização para preencher tudo com zero ou listas vazias.

Exemplos:

| Tipo | Diferenças relevantes |
|---|---|
| `SessionStartResponse` | Novo `Withdraw` |
| `AccountProfileResponse` | Equipamentos, tamanho de inventário, itens de sala e badge; `RouletteEventList` sai dessa declaração |
| `LobbyResponse` | Artefato, bingo adicional, avisos de eventos/puzzle e data de dispensa de anúncios |
| `CharacterLikeResponse` | Campos antigos dão lugar a listas/tipo de preferência |
| `ItemOpenBoxResponse` e `PostReadResponse` | Recompensas de presets passam a listas na declaração nova |
| `SmashEndResponse` | Novo `artifactPoint` |

Classes novas de API incluem seleção de grupo de personagem, reinício de gacha, compra por cupom e estruturas de roleta adicional. A presença de classes não demonstra que as rotas correspondentes já estejam implementadas localmente.

O código local separa algumas implementações de regras de respostas de fallback. Há caminhos que devolvem templates tipados ou stubs de sucesso. **Uma resposta HTTP 200/JSON sem erro pode ser apenas esse fallback, sem implementar a função.** Logo, reaproveitar o servidor exige auditar fluxo por fluxo: requisição, resposta, alteração de estado, persistência e efeito observado.

### Impacto no save

Um perfil antigo não passa automaticamente a ser um perfil nativo da 1.17. Equipamentos, artefatos, presets, progressão e inventários exigem mapear estruturas e invariantes antes de definir uma conversão. A análise não aprovou nem implementou conversor de save. As cópias de save utilizadas no experimento anterior não validam essa migração.

## 7. Dimensionamento do caminho A: reparar a 1.17

| Frente | Trabalho necessário | Esforço/risco atual | Condição para avançar |
|---|---|---|---|
| Dados da 1.17 | Tornar tabelas legíveis e verificar que os grupos pertencem ao mesmo acervo | **Bloqueador / incerteza alta** | Dados legíveis/chaves compatíveis, com origem identificada |
| Serializadores e contratos | Conferir campos, tags, tipos, valores padrão e rotas realmente utilizadas | **Alto** | Mapa verificável de sessões, perfil, lobby e fluxos de jogo |
| Servidor local | Reutilizar implementações compatíveis e implementar sistemas ausentes | **Alto**, por família | Testes de estado e persistência, sem stubs contados como função pronta |
| Bootstrap/SDK/serviços desligados | Definir um fluxo local compatível com o cliente novo | **Médio a alto** | Configuração e sessão verificadas sem dados antigos mascarando lacunas |
| Assets | Validar catálogo e dependências no próprio cliente 1.17 | **Médio**, sem prova de integridade total | Referências e recursos necessários completos |
| Mods existentes | Remapear endereços/campos e rever os patches | **Alto**, varia por mod | Build/hash exato e teste individual |
| Save | Projetar conversão explícita ou criar perfil nativo novo, conforme decisão | **Alto** | Esquema e regras novos compreendidos antes de transportar dados |
| Validação | Entrada, combate, habilidades, recompensas, progressão, persistência e recortes novos | **Alto** | Critérios por função; interface validada pelo usuário |

**Dependência principal:** resolver os dados. Se for possível obter tabelas legíveis coerentes, a implementação passa a ter um escopo mais delimitável. Se for necessário reconstruir extensivamente dados de 430 tabelas comuns mais idioma, o projeto muda de tamanho. Ainda não foi feita uma contagem de linhas e relações legíveis para estimar esse trabalho.

## 8. Dimensionamento do caminho B: portar funções para a 1.11

| Recorte pretendido | O que pode ser reaproveitado | Trabalho adicional | Parecer |
|---|---|---|---|
| Ajuste de regra já representável na 1.11 | Estruturas e código existentes | Compreender valores/regras novos e adaptar servidor/tabelas | **Potencialmente viável**, dependendo do recorte |
| Personagem cujas mecânicas já existam na 1.11 | Parte do pipeline antigo | Conversão de recursos, montagem de dados, dependências e validação | **Condicional**, não demonstrado |
| Personagem/habilidade com mecanismos novos | Arte pode ter aproveitamento parcial | Implementar comportamento que não existe no código antigo | **Muito alto**, sem garantia de fidelidade |
| Equipamentos/artefatos/modo novo completo | Infraestrutura genérica limitada | UI, estado, regras, serialização, código e recursos | **Muito alto**; tratar como implementação de subsistema |
| Todas as funções/conteúdo da 1.17 na 1.11 | Parte da infraestrutura local | Portar uma parcela ampla da evolução do cliente e de seus dados | **Não demonstrado e desfavorável como atualização geral** sem fontes/ferramentas de reconstrução suficientes |

O maior obstáculo de B não é só criptografia: é transportar para um cliente antigo recursos e comportamentos associados a código e motor mais novos. Mesmo com tabelas legíveis, isso não fornece automaticamente as implementações faltantes da 1.11.

## 9. Esforço total e limites da estimativa

Seria especulativo apresentar agora um prazo fechado de horas ou meses. Ainda faltam: quantidade de dados legíveis, cobertura real do backend, lista priorizada de funções e demonstração de um recorte de conversão de assets. Não há base para prometer equivalência completa em qualquer dos caminhos.

O esforço relativo é:

- **A, preservação ampla da 1.17:** alto, com bloqueio inicial nos dados e depois implementação/validação de servidor. Aproveita o código novo já compilado.
- **B, poucos recursos compatíveis com mecanismos antigos:** pode ser menor que A, caso a avaliação daquele recurso confirme compatibilidade.
- **B, paridade ampla com a 1.17:** esforço e incerteza maiores; pode exigir reengenharia sem uma rota praticável para reconstruir fielmente o cliente antigo.

Para obter uma estimativa numérica defensável, a próxima etapa teria que ser uma investigação limitada e acordada — **não a atualização** — com três entregas: disponibilidade/procedência das tabelas; contratos de um fluxo completo; e dependências/conversão possível de um recurso escolhido. Se uma investigação não conseguir produzir sua evidência, o resultado correto é registrar o bloqueio, não substituir os dados por outra versão para dar aparência de progresso.

## 10. Evidências que faltam para decidir definitivamente

1. Dados originais 1.17 legíveis, ou viabilidade documentada da sua reconstrução sem usar as tabelas antigas como resultado final.
2. Números/tipos dos campos serializados e regras dos fluxos críticos; igualdade de nome de classe não basta.
3. Lista das funções novas que o usuário realmente pretende ter. “Atualizar tudo” e “portar três personagens” são escopos diferentes.
4. Para B, teste de viabilidade de conversão de um recurso representativo e identificação do código necessário. Nenhum desses testes está aprovado/executado por esta análise.
5. Para A, definição de perfil de dados nativo e cobertura de servidor necessária, antes de pensar em conversão de save.

**Decisão sugerida:** considerar A como candidato preferencial se o objetivo é a versão recente de forma ampla, mas somente depois do diagnóstico de dados/contratos. Considerar B apenas por recortes definidos, sem assumir que os 1.132 assets adicionais possam virar automaticamente conteúdo da 1.11.

## 11. Estado do trabalho anterior e preservação

O experimento híbrido fica suspenso. Nenhum resultado dele é apresentado aqui como prova de atualização concluída ou de suporte ao conteúdo novo. Nesta revisão não foram alterados cliente, tabelas, servidor em execução ou save; foram produzidos documentos e evidências de leitura.

O backup congelado mantém o ponto de referência original da instalação local: 17.936 arquivos e 11.098.474.923 bytes copiados com conferência de SHA-256 na criação.

Uma nova conferência da pasta funcional em uso encontrou **55 arquivos diferentes do backup**, concentrados em save, logs, PID/sessão, preferências e cache WebView; nenhum arquivo novo. Isso significa que não é correto continuar afirmando que a pasta inteira em uso permanece idêntica ao backup. A origem de cada alteração de estado não foi atribuída sem evidência. Não houve restauração, exclusão ou nova cópia de save nesta análise. As referências de código/metadados originais e o backup congelado foram mantidos separados desse estado mutável.

## 12. Evidências anexas e cobertura do Graphify

- `esquemas-originais.json`: comparação completa de declarações das classes, com hashes dos dumps.
- `tabelas-originais.json`: nomes adicionados/removidos, comparação de bytes e teste negativo de chave.
- `lacunas-templates.json`: quinze templates com campos adicionais da declaração nova ausentes.
- `identificacao-binarios.json`: tamanhos e hashes dos arquivos críticos das três referências.
- `referencia-mutavel.json`: resultado da conferência atual da instalação em uso contra o backup.
- Inventários prévios de arquivos e assets permanecem nos relatórios locais; não foram substituídos pelo estado do experimento.

Graphify consultado no índice do commit `0315909`. A análise de `server/local_player.py` retornou o arquivo exato e relações com progressão/cartas/poll e servidor. Consultas de documentos/AGENTS resolveram para README ou não tiveram cobertura, então foram conferidos os arquivos locais. O índice contém fontes publicadas, não os clientes Unity originais nem todos os dados binários; portanto não substitui esta comparação estática.

**Estado final desta entrega: relatório de avaliação, não implementação.** Qualquer continuidade depende da escolha explícita do usuário sobre caminho e recorte.
