# Graphify

Repositório: `extrajogos6-ops/KOFAS`.

O plugin hospedado consulta índices já promovidos. As ferramentas disponíveis nesta sessão não adicionam repositórios nem iniciam builds de indexação. O primeiro `list_repositories` retornou HTTP 403 `no_authorized_repositories` no workspace conectado. A conexão do plugin, isoladamente, não prova que o repositório esteja habilitado/indexado.

Após publicar o primeiro commit, no painel Graphify:

1. Conectar/selecionar o repositório `extrajogos6-ops/KOFAS` no workspace usado pelo plugin.
2. Autorizar somente esse repositório quando o GitHub solicitar acesso.
3. Iniciar a indexação disponível no painel e aguardar `Indexed`.
4. Habilitar o repositório para agentes, se houver essa opção.
5. Consultar novamente `list_repositories`, depois `graph_stats`. Confirmar o commit indexado contra `git rev-parse HEAD`.

Antes de cada alteração seguir o protocolo de `AGENTS.md`, registrando vizinhos, chamadores e testes relacionados. Se o índice estiver atrasado, examinar também `git diff <commit-indexado>..HEAD`.

Este bootstrap importou fontes sem modificá-las e criou documentação/configuração para tornar o primeiro índice possível. Nenhuma consulta de impacto sem índice deve ser descrita como análise concluída.

Referência oficial: https://graphify.com/mcp e https://github.com/Graphify-Labs/docs/blob/main/integrations/chatgpt.mdx.
