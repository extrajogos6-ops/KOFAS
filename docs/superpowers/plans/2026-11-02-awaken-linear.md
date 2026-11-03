# Awaken local — bônus aditivo proporcional do nível 1 ao 6

**Objetivo aprovado:** preservar status e opções normais, e aplicar a proporção direta escolhida pelo usuário a todos os status de despertar: valor do nível = base do nível 1 × nível da opção de despertar, de 1 a 6. A skill da opção pode chegar a 6 depois da quinta estrela.

**Arquitetura:** criar nove efeitos exclusivos de despertar nas tabelas locais reconstruídas da 1.11.2, preservando os efeitos normais existentes. Atualizar somente as referências das nove opções de despertar, seus nomes/descrições, manifests MD5 e versões de tabela/idioma. Não editar save, cliente, mods ou dados 1.17.

**Evidência:** o save preserva `Stat`, `Exp`, `PassiveIndex*` e `PassiveLevel*`. A rotina nativa `CreateBuff` acrescenta o bônus de despertar e depois os passivos normais; `TotalAttack` mantém os atributos próprios da carta. A perda de atributos não foi reproduzida. As descrições locais atuais são textos fixos, embora as propriedades numéricas prevejam 10% por nível. A curva nova de 100% por nível é uma personalização solicitada, não restauração de valores oficiais.

## Implementação e validação

- [x] Criar `scripts/local_awaken_balance.py`: gerar patch em memória, conferir dados/CRC/MD5, fazer backup verificado e instalar cinco arquivos, publicando a versão por último. Nenhum perfil será alterado.
- [x] Criar `server/tests/test_awaken_balance.py`: regressão da curva atual, nove opções × seis níveis, porcentagens, efeitos normais intactos, arquivos não relacionados intactos, manifests e idempotência.
- [x] Testar respostas de tabela/idioma em HTTP isolado e manter a suíte de Skill Up aprovada pelo usuário.
- [x] Gerar em cópia e revisar antes de aplicar. Backup de packs, manifests, versões, instruções externas e save; conferir hashes.
- [x] Instalar as tabelas geradas e aumentar as versões para o cliente recarregar no próximo início manual.
- [x] Versionar o gerador, testes, regras e impacto; excluir dados binários e perfis do Git.

## Critérios

ATK base 80: 80/160/240/320/400/480; crítico base 3%: 3/6/9/12/15/18%. O nível usado é `awakeBuffLevel`, exibido como Option Lv.; a estrela autoriza a progressão da opção, sem pular o Skill Up exigido pelo jogo. Nenhuma alteração dos buffs normais, suas descrições, status base ou inventário. Nenhuma cobrança para aplicar o balanceamento a cartas já despertadas.

Graphify consultado em `7d7f287eda2f2bafeeae3218687c5743fef31d0a`, igual ao HEAD inicial. Pontos de integração cobertos: `server/server.py` e `server/local_player.py`; arquivos novos e JSON de versões não têm cobertura exata. Registrar limites e arquivos em `docs/impact/2026-11-02-awaken-linear.md`.

Teste visual manual pendente: reiniciar jogo/launcher e conferir os detalhes da opção em diferentes níveis e os atributos totais da carta/personagem antes/depois. Não controlar o desktop em testes.

Execução: 52 testes aprovados; arquivos instalados com backup e verificação independente. Validação visual permanece manual e pendente.
