# Auditoria Visual — Etapa 1

> Data: 2026-08-07 | Escopo: Portal do Cliente + Supervisão Pred.IO | Sem sidebar, sem GUT, sem refatoração grande

## O que foi feito

Auditoria de código (não de tela renderizada — ambiente sem acesso a browser/Render nesta sessão) nas 11 páginas do Portal do Cliente e leitura direcionada da Supervisão, focada em achar problemas **reais** (bugs visíveis ao cliente, dados falsos aparecendo como reais, mensagens técnicas cruas) em vez de listar toda variação cosmética de padding/cor entre arquivos. Corrigido o que era seguro e contido; o resto está documentado abaixo como pendência.

## Correções aplicadas

| Arquivo | Problema | Correção |
|---|---|---|
| `page_ativos.py` | Campo vazio na planilha (ex: Modelo, Nº de Série, Planta) virava literalmente a palavra **"nan"** na tela do cliente, porque `str(NaN) or "—"` nunca cai no fallback (NaN vira `"nan"`, string não-vazia). Afetava `modelo`, `numero_serie`, `mb`, `Planta`, `criticidade`, `inversor_frequencia`, `Ultima_Atualizacao` (este último nem tinha fallback). | Adicionada função `_clean()` que trata `""`/`"nan"`/`None` como ausente e usa "—" em todos os 7 campos. |
| `page_farois.py` | Qualquer erro ao carregar ou renderizar o painel do cliente mostrava a mensagem de exceção Python crua (`Erro ao carregar ativos: {e}`) e, em um caso, **o traceback completo** (`st.exception(e)`) diretamente na tela do cliente. | Trocado por mensagens genéricas e amigáveis ("Não foi possível carregar... tente novamente"), sem vazar detalhe técnico. |
| `page_farois.py` | Empty state de ativos dizia "Adicione equipamentos na aba 'Ativos' **da planilha**" — instrução de backend interna exposta ao cliente final. | Reescrito para linguagem voltada ao cliente ("assim que a equipe Pred.IO cadastrar..."). |
| `page_farois.py` | O card "Chamados em Andamento" da Visão Executiva (aba Faróis) é alimentado por `_EXEC_MOCK` e **nunca era substituído por dado real** — todo cliente real (incluindo RJR em produção) via permanentemente 1 chamado fictício ("Acompanhamento da Bomba de Óleo M60P", Em análise/Alta) que não é dele. | Criada `_build_chamados_abertos(client_id)`, que busca chamados reais via `get_chamados_v2()` (mesma função usada em `page_chamados.py`) e substitui os campos mock. Se não houver chamados reais, mostra corretamente "Nenhum chamado em aberto". |

Todos os 44 arquivos `.py` do projeto foram recompilados (`py -m py_compile`) após as mudanças — sem erro de sintaxe.

## Pendência crítica — RESOLVIDA em 2026-08-07 (pós Etapa 2)

~~Visão Executiva (aba Faróis) ainda mostra dados de um ativo fictício para todo cliente real~~ — corrigido. As quatro partes que liam de `page_ativos._MOCK` (uma "Unidade Compressora Parafuso 200 VLD" fictícia) foram reescritas para usar dados reais do cliente logado:

| Bloco | Fonte antiga | Fonte nova |
|---|---|---|
| `status_geral` / `status_geral_desc` | `page_ativos._MOCK[0]` | Pior status entre os ativos reais já carregados em `render()` via `get_ativos(client_id)` |
| `resumo_tecnico` | `page_ativos._MOCK` | Um parágrafo por ativo real, agrupado por Tag/Nº de série (mesmo agrupamento já usado no resto da página) |
| `proximas_acoes` | `page_ativos._PLANO_MOCK_COMPRESSOR` | `sheets.get_maintenance_tasks(client_id, staff=False)` — mesma fonte que `page_manutencao.py` já usa |
| `componentes_alarme` | `page_ativos._MOCK[...]["componentes"]` | Linhas reais do DataFrame de ativos com status Crítico/Atenção |

`_EXEC_MOCK` (o dicionário-base fictício, incluindo o `client_id: "coca-cola"` hardcoded e o chamado fictício sobre a "Bomba de Óleo M60P") foi removido do arquivo. Testado com um DataFrame sintético reproduzindo o formato real da planilha (`Tag`/`Equipamentos`/`Status`/`Ns`/`Detalhes`, incluindo células vazias/"nan") — sem vazamento de "nan" no resumo, sem erro em ativos vazios. `py -m py_compile` e `import page_farois` continuam passando nos 44 arquivos do projeto.

**Achado colateral (não corrigido — código morto, não afeta cliente):** duas funções em `page_farois.py` — `_render_alertas_importantes()` (lê `page_alertas._ALERTAS_MOCK` direto, sem filtrar por cliente) e `_render_proximas_manutencoes()` (lê `page_ativos._PLANO_MOCK_COMPRESSOR`) — também referenciam dado fictício, mas **nunca são chamadas em lugar nenhum do código** (confirmado por busca no projeto inteiro). Não representam risco hoje; se alguém vier a "ativá-las" no futuro, precisam do mesmo tratamento acima antes disso.

## Outras observações (não corrigidas — funcionalidade não implementada, não é regressão visual)

- `page_alertas.py` — a página inteira roda sobre `_ALERTAS_MOCK` com `client_id` fixo `"coca-cola"` e um `# TODO: substituir pela consulta real ao banco`. Para qualquer cliente real, isso já resulta em lista vazia (comportamento seguro — não mostra dado de outro cliente), só que a funcionalidade "Alertas Preditivos" ainda não está de fato ligada a dado real. Não é bug de exposição, é feature pendente.
- `page_manutencao.py` — tem um modo de fallback (`_render_mock_mode`) quando a planilha de tarefas está vazia, mas ele **já se identifica honestamente** como "Exibindo plano de demonstração" — está correto como está, não precisa de ajuste.
- Lado Supervisão: `page_sv_ativos.py` (`_MOCK_ATIVOS`, cliente fixo "coca-cola") e `page_sv_manutencao.py` (`_PLANO_MOCK_COMPRESSOR`) também caem para dados fictícios quando a planilha do cliente está vazia/em formato antigo — isso é interno (só a equipe Pred.IO vê), então o risco é a equipe achar que um cliente tem dados carregados quando na verdade a aba dele está vazia. Não mexi por ser área de homologação/staff e por prudência de escopo — mas vale confirmar se é comportamento desejado.

## Inconsistência de cores de status (não corrigida — cosmética, não crítica)

Cada página do portal define sua própria paleta local de cores para status de chamado e prioridade (chamado "aberto" aparece azul em `ui.py`, vermelho em `page_chamados.py`, laranja em `page_dashboard.py`), em vez de todas usarem os dicts centrais `STATUS_CFG`/`PRIORIDADE_CFG`/`badge()` já existentes em `ui.py`. Isso é real e bate com o pedido original de "cores mais fáceis de entender", mas envolve tocar em ~10 arquivos para um ganho puramente cosmético — não fiz isso nesta etapa por não ser um bug nem afetar uso do portal. Fica como sugestão para a Etapa 2 (Design System): consolidar tudo em `ui.STATUS_CFG`/`PRIORIDADE_CFG` e remover os dicts locais duplicados.

## Checks técnicos

Não há lint, typecheck, test suite ou build configurados no projeto (`requirements.txt` não inclui flake8/ruff/mypy/pytest; sem `pyproject.toml`/`tox.ini`/pasta `tests/`). Único check disponível e executado: `py -m py_compile` em todos os 44 arquivos `.py` — **passou sem erros**.

## Confirmações pedidas

- Não foi criada sidebar.
- Sistema GUT não foi iniciado.
- Nenhuma mensagem de WhatsApp ou e-mail foi enviada/alterada.
- Login e permissões não foram alterados.
- Assistente Técnico continua como botão flutuante (nenhuma mudança nele).
- `client_id` continua vindo exclusivamente da sessão — nenhuma regra de segurança tocada.

## Próxima etapa recomendada

1. ~~Resolver a pendência crítica da Visão Executiva~~ — feito em 2026-08-07.
2. ~~Decidir se a consolidação de cores de status entra na Etapa 2~~ — feito (Etapa 2, `docs/PREDIO_DESIGN_SYSTEM.md`).
3. Confirmar com a equipe se os fallbacks mock da Supervisão (`page_sv_ativos.py`, `page_sv_manutencao.py`) são intencionais para homologação ou devem virar um empty state explícito como o de `page_manutencao.py` — ainda em aberto.
4. Ativar a Central de Alertas Preditivos com dado real (`page_alertas.py` ainda roda sobre mock, `# TODO` explícito) — feature pendente, não é regressão.
