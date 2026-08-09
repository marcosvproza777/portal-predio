# Design System Pred.IO — Etapa 2

> Data: 2026-08-07 | Fonte única de verdade: `ui.py` | Sem sidebar, sem GUT, sem alteração de regra de negócio

Este documento descreve o Design System do Portal Pred.IO: os tokens de cor, os componentes reutilizáveis e os padrões de status já centralizados em `ui.py`, para que qualquer página nova (cliente ou supervisão) reuse a mesma base em vez de recriar estilos.

## 1. Cores / tokens

Definidos no topo de `ui.py`.

**Paleta base** (já existia, mantida):
| Token | Hex | Uso |
|---|---|---|
| `COLOR_NAVY` | `#0F1F3D` | Títulos, marca, texto de destaque |
| `COLOR_BLUE` | `#2563EB` | Botão primário, links, acentos |
| `COLOR_CYAN` | `#38BDF8` | Marca secundária, destaques claros |
| `COLOR_BG` | `#F1F5F9` | Fundo da página |
| `COLOR_CARD` | `#FFFFFF` | Fundo de cards |
| `COLOR_BORDER` | `#E2E8F0` | Bordas |
| `COLOR_MUTED` | `#64748B` | Texto secundário |

**Tokens semânticos de status** (novos — Etapa 2):
| Token | Hex | Significado |
|---|---|---|
| `COLOR_SUCCESS` | `#10B981` | Bom / Em dia / Publicado / Indexado / Concluído |
| `COLOR_WARNING` | `#F59E0B` | Atenção / Próxima / Em revisão / Processando |
| `COLOR_DANGER` | `#EF4444` | Crítico / Vencida / Falhou |
| `COLOR_URGENT` | `#7C3AED` | Urgente (nível acima de Crítico) |
| `COLOR_INFO` | `#3B82F6` | Aberto / Em análise (chamado) |
| `COLOR_ACCENT` | `#8B5CF6` | Em análise / Por condição |
| `COLOR_NEUTRAL` | `#94A3B8` | Rascunho / Não indexado / Cancelado / Arquivado |

Regra: **qualquer cor de status nova usa um destes tokens — nunca um hex solto**.

## 2. Status padronizados — `STATUS_REGISTRY`

`ui.py` define `STATUS_REGISTRY`, um dicionário único `domínio → label → (cor_fundo, cor_texto)` cobrindo os 6 domínios do portal, e a função `status_badge(label, dominio)` que já resolve a cor e devolve o HTML do badge pronto:

```python
from ui import status_badge
st.markdown(status_badge("Crítico", "saude_ativo"), unsafe_allow_html=True)
```

| Domínio | Labels |
|---|---|
| `saude_ativo` | Bom, Atenção, Crítico, Urgente |
| `manutencao` | Em dia, Próxima, Vencida, Concluída, Por condição |
| `relatorio` | Publicado, Rascunho, Em revisão, Arquivado |
| `chamado` | Aberto, Em análise, Em andamento, Aguardando cliente, Respondido, Concluído, Cancelado, Reaberto |
| `indexacao` | Não indexado, Processando, Indexado, Falhou |
| `prioridade` | Baixa, Média, Alta, Crítica |

`STATUS_CFG` (chamados) e `PRIORIDADE_CFG` (prioridade) — os dicts que já existiam antes desta etapa — foram mantidos intactos por compatibilidade; `STATUS_REGISTRY` é a versão completa e é o que deve ser usado em código novo.

Regra de negócio inalterada: cliente continua só vendo relatório com status **Publicado**; rascunho, em revisão e observações internas nunca aparecem para o cliente (`security.py` já garante isso — não foi tocado).

## 3. Componentes (AppX)

Streamlit não é baseado em componentes React — os "AppX" abaixo são funções Python em `ui.py` ou padrões de uso dos widgets nativos já estilizados globalmente via CSS (`inject_global_css`/`inject_mobile_css`).

| Componente pedido | Como usar hoje |
|---|---|
| **AppPageHeader** | `page_header(title, subtitle, back_label="", back_view="")` — título + subtítulo + divisor, com botão "← voltar" opcional (usado na Supervisão). `sv_page_header` virou um alias fino de `page_header` (era código duplicado). |
| **AppSectionTitle** | `app_section_title(text, icon="")` — subtítulo de seção dentro de uma página (ex: "Chamados em Andamento"). |
| **AppBadge** | `badge(label, color, text_color="#fff")` — pílula genérica. Para status/prioridade, prefira `status_badge(label, dominio)`. |
| **AppCard** | `card_html(inner_html, accent="", accent_side="top")` — moldura padrão (radius 14px, padding, sombra) para HTML pronto. Para cards com widgets Streamlit interativos dentro (inputs, botões), use `st.container(border=True)` — recurso nativo do Streamlit 1.58 (a versão instalada), mais simples que qualquer wrapper. |
| **AppEmptyState** | `empty_state(message, icon="📭")` (alias `app_empty_state`) — usar sempre no lugar de `st.info()`/texto solto quando uma lista está vazia. |
| **AppAlert** | `app_alert(message, kind="info")` — `kind`: info/success/warning/danger. Alternativa consistente a `st.info/warning/error` para alertas dentro do conteúdo do portal. |
| **AppButton** | Não precisa de wrapper — `st.button(..., type="primary"|"secondary", use_container_width=True)` já é estilizado globalmente em `inject_global_css()` (gradiente azul no primário, contorno neutro no secundário, hover vermelho no "Sair"). |
| **AppInput / AppSelect** | Idem — `st.text_input`/`st.selectbox`/`st.text_area` já recebem `border-radius:8px` e, no mobile, `font-size:16px` (evita zoom automático do iOS) via `inject_mobile_css()`. Não é necessário wrapper. |
| **AppModal** | O Streamlit instalado (1.58) tem `st.dialog` nativo — use-o para modais novos em vez de HTML customizado: `@st.dialog("Título")` decorando a função que renderiza o conteúdo. Não havia uso de modal customizado no portal antes desta etapa. |
| **AppLoading** | `st.spinner("Carregando...")` (nativo) — já é o padrão usado no portal, não precisa de wrapper. |
| **AppTable** | O portal **não usa `st.dataframe`/`st.table` em nenhuma página** — toda listagem tabular já é renderizada como cards, que são naturalmente mobile-friendly (a alternativa que a Etapa 1 pediu para tabelas). Se uma tabela nativa for necessária no futuro, usar `st.dataframe(df, use_container_width=True, hide_index=True)`. |

## 4. Layout base

- Largura de página: controlada pelo `layout="wide"` do Streamlit (já era o padrão) + `page_header()` para título/subtítulo/divisor consistentes.
- Espaçamento entre cards: os cards do portal usam `margin-bottom: 6–8px` e o padrão de `card_html()` é `padding:1.25rem 1.5rem` / `radius:14px` / sombra `0 1px 4px rgba(15,31,61,0.06)`.
- Navegação: **sem sidebar** — topnav horizontal no cliente (`render_client_topnav`) e pill-nav horizontal na Supervisão (`render_sv_topnav`), como já era. Nada disso foi alterado nesta etapa.
- Assistente Técnico: continua botão flutuante (`inject_floating_assistant`), inalterado.

## 5. Mobile

CSS responsivo global já existente em `pwa.py` (`_MOBILE_CSS`) cobre: botões/inputs com toque mínimo de 44px, `st.columns()` colapsando para 2 depois 1 coluna em telas pequenas, tabs e topnav com scroll horizontal, bottom nav fixo com menu "Mais". Nenhum ajuste foi necessário nesta etapa — os novos componentes (`card_html`, `app_alert`, `status_badge`) herdam esse comportamento automaticamente por serem HTML simples dentro do fluxo normal da página.

## 6. Correções de cor aplicadas nesta etapa

A Etapa 1 (auditoria) já tinha identificado que cada página definia sua própria paleta local de status/prioridade, às vezes conflitando entre si. Nesta etapa, essas paletas locais foram normalizadas para os tokens acima (mesma cor, em vez de recriar o dict) nos arquivos abaixo. Nenhuma lógica ou regra de negócio foi alterada — só os valores de cor.

| Arquivo | O que mudou |
|---|---|
| `page_dashboard.py` | `_score_cor`, `_PRIO_COR`, `_CHAM_ST_COR`, `_SEV_COR` — hex normalizados para os tokens. |
| `page_farois.py` | `_EXEC_COR` e as duas cópias locais de prioridade/status de chamado (`PRIO_COR`, `PRIO_CFG`/`ST_CFG`) — "Aberto" era laranja num lugar e não existia consistentemente em outro; agora é sempre azul (`COLOR_INFO`), igual à Supervisão. |
| `page_ativos.py` | `_PM_PRIO_COLOR["baixa"]` alinhado a `COLOR_MUTED` (era um cinza ligeiramente diferente do resto do portal). |
| `page_manutencao.py` | Badge de prioridade das tarefas era cinza fixo para Alta/Média/Baixa (sem diferenciação); agora usa a cor correspondente de prioridade. |
| `page_relatorios.py` | `_SEV_COLOR` normalizado; badge "Disponível" do modo legado usava um verde diferente (`#22c55e`) do resto do portal (`#10B981`) — agora é o mesmo verde em toda a página. |
| `page_chamados.py` | **Principal correção da etapa.** `_STATUS_CFG2`/`_PRIO_CFG2` tinham cores diferentes das usadas no resto do portal para os mesmos status (ex: "Aberto" era vermelho aqui e azul em `ui.STATUS_CFG`; prioridade "Alta" era vermelha aqui, igual à "Crítica", em vez de laranja). O emoji de prioridade no título do card (🔴/🟡/🔵) também não batia com a cor do badge logo abaixo dele. Corrigido: cores alinhadas ao registry central, e o emoji agora vem de uma tabela (`_PRIO_EMOJI`) coerente com o badge. Três constantes mortas (`_STATUS_ABERTO_BADGE` etc., nunca usadas) foram removidas. |
| `page_alertas.py` | Prioridade "Alta" era vermelha (igual a "Crítico" em outras telas); agora é laranja, coerente com `prioridade.alta` em todo o portal. Dois blocos de "nenhum alerta" escritos à mão foram trocados por `empty_state()`. |

Páginas de Supervisão auditadas (`page_sv_ativos`, `page_sv_manutencao`, `page_sv_biblioteca`, `page_sv_relatorios`, `page_sv_relatorio_executivo`, `page_sv_chamados`, `page_sv_chamado_detalhe`, `page_sv_dashboard`): já usavam cores consistentes com o registry central (a maior parte dos chamados/status da Supervisão já importava `STATUS_CFG`/`PRIORIDADE_CFG` diretamente de `ui.py`) — nenhuma mudança necessária.

## 7. O que não foi mexido (por decisão de escopo)

- Padding/raio/sombra de cada card individual não foi uniformizado em todas as páginas — isso é cosmético (não gera confusão para o usuário) e envolveria reescrever HTML em ~15 arquivos para ganho visual pequeno. `card_html()` já existe para quem quiser adotar aos poucos.
- `page_sv_biblioteca.py` usa uma paleta "chip translúcido" (ex: `#DCFCE722`) diferente da paleta "pílula sólida" do resto — internamente consistente, semanticamente correta (verde=indexado, vermelho=falhou), só num estilo visual diferente. Não forcei a migração porque não é um bug, é uma variação de estilo já coerente dentro do próprio arquivo.
- A pendência crítica já registrada na Etapa 1 (Visão Executiva com dados de ativo fictício em 4 blocos) continua em aberto — é problema de dados, não de Design System.

## 8. Checks técnicos

Sem lint/typecheck/build configurados no projeto (mesma situação da Etapa 1 — sem `pyproject.toml`/`flake8`/`pytest`). Executado `py -m py_compile` em todos os arquivos `.py` do projeto (Streamlit 1.58.0 instalado) — **sem erros**.

## 9. Confirmações pedidas

- Não foi criada sidebar.
- Sistema GUT não foi iniciado.
- WhatsApp e e-mail não foram tocados.
- Login e permissões não foram alterados.
- Nenhuma função nova fora do visual foi criada (todas as adições em `ui.py` são helpers de renderização).

## 10. Próxima etapa recomendada

1. Aplicar o Design System nas ~7 telas restantes que ainda não foram tocadas por nenhuma das duas etapas (ex: `page_notificacoes_portal.py`, `page_preferencias_notificacao.py`, `page_assistente.py`, `page_sv_assistente.py`, `page_sv_homologacao.py`) — mesmo padrão de normalização de cor, se houver conflitos.
2. Resolver a pendência crítica da Visão Executiva (Etapa 1) antes de subir novos clientes reais — é a prioridade mais alta do portal hoje, mais do que qualquer ajuste visual.
3. Se o portal crescer, migrar `card_html()`/`status_badge()` para as páginas que ainda usam HTML de card totalmente manual, para reduzir duplicação de estilo.

---

## 11. Etapa 3 (2026-08-09) — polimento visual da Supervisão

Pedido do usuário: "deixar o visual da Supervisão mais bonito e apresentável", sem novas features nem mudança de regra de negócio. Ao contrário das Etapas 1-2 (só cor), esta etapa também consolidou estrutura (badges duplicados, cards de métrica, empty states) nas páginas que a auditoria desta sessão mostrou como realmente inconsistentes — não só entre páginas, mas às vezes dentro do mesmo card.

### 11.1 Header da Supervisão — bug de alinhamento corrigido

`render_sv_topnav()` (`ui.py`): "Supervisão" (bloco HTML plano) e o bloco usuário/Sair (`st.columns([3,1])` aninhado + `st.button()` nativo) tinham profundidade de DOM diferente, então `align-items:center` na linha não bastava — cada lado ficava com uma altura intrínseca diferente. Corrigido fazendo **cada coluna** (não só a linha) virar um flex container com `align-items:center` e `min-height` fixa, e zerando a margem nativa do botão "Sair". Validado com um mockup HTML reproduzindo o DOM real do Streamlit (`stHorizontalBlock`/`column`/`stButton`) antes e depois da correção — captura de tela confirmou o alinhamento.

CSS mobile (`pwa.py`, breakpoints 640px/480px): as regras que quebram colunas em 2/1 por linha só tinham exceção para `.portal-nav-marker` (cliente) — adicionada a mesma exceção para `.sv-topnav-marker`/`.sv-topnav-user-marker`, senão o header da Supervisão herdava regras pensadas pro portal do cliente.

### 11.2 Badges/pills consolidados

| Arquivo | O que mudou |
|---|---|
| `ui.py` | `STATUS_REGISTRY["saude_ativo"]` ganhou "em acompanhamento" (ciano) e as 4 faixas de criticidade (baixa/média/alta/crítica — mesma escala de cor de bom/atenção/crítico/urgente, vocabulário diferente). `STATUS_REGISTRY["manutencao"]` ganhou "cancelada". `STATUS_REGISTRY["relatorio"]` ganhou "disponível" (era um verde `#22c55e` fora do padrão em `page_sv_clientes.py`, virou `COLOR_SUCCESS`). Nova função `status_color(label, dominio)` — mesma resolução de `status_badge()`, mas devolve só o hex, para acentos de borda sem montar o badge inteiro. |
| `page_sv_ativos.py` | `_STATUS`/`_CRITICIDADE` (10 campos de cor à mão) → `status_badge()`/`status_color()`. Ícone do status mantido só onde já era usado (cards de métrica do detalhe), badge da lista sem ícone (padrão do resto do portal). |
| `page_sv_manutencao.py` | `_STATUS_BADGE`/`_PRIO_COLOR` → `status_badge(..., "manutencao")`/`status_badge(..., "prioridade")`. |
| `page_sv_chamados.py` | Import direto de `STATUS_CFG`/`PRIORIDADE_CFG` (legado) → `status_badge()`. Isso corrigiu uma cor real fora do padrão: "Em análise" e "Aguardando cliente" tinham hex diferente do resto do portal (`STATUS_CFG` nunca tinha sido sincronizado com `STATUS_REGISTRY`). |
| `page_sv_chamado_detalhe.py` | Mesmo `STATUS_CFG`/`PRIORIDADE_CFG` legado (closure `pill()`) → `status_badge()`/`badge()`. |
| `page_sv_clientes.py` | Mesmo padrão no card-resumo de chamado (`_render_chamado_mini`); card-resumo de relatório tinha uma variável local chamada `status_color` que colidia com a nova função importada de `ui.py` — renomeado/removido o conflito ao migrar para `status_badge()`. |
| `page_sv_alertas.py` | **Bug real corrigido**: badge de prioridade usava estilo translúcido (`{cor}22`/`{cor}55`) enquanto o badge de cliente ao lado, no mesmo card, era sólido — inconsistência dentro do próprio card, não só entre páginas. Agora os dois são sólidos (`status_badge`), como no resto da Supervisão. |

**Não mexido**: `page_sv_biblioteca.py` mantém o estilo "chip translúcido" (mesma decisão da Etapa 2 — é uma variação de estilo intencional, não um bug) — só os empty states dessa página foram tocados (§11.4). `page_sv_assistente.py` e `page_sv_notificacoes.py` mantêm suas paletas locais de badge (conceitos muito específicos — confiança da IA, canal de notificação, avaliação de resposta — que não mapeiam 1:1 nos domínios existentes do registry); só os cards de métrica e os empty states dessas duas páginas foram migrados (§11.3/§11.4), não os badges.

### 11.3 Cards de métrica consolidados em `sv_metric_card()`

Substituídos tiles de métrica feitos à mão (`page_sv_chamados.py`, `page_sv_manutencao.py`) e widgets nativos `st.metric()`/`.metric()` (`page_sv_assistente.py`, `page_sv_notificacoes.py`) por `sv_metric_card()` — mesmo visual (ícone + label + valor + acento de cor) em vez de 3 estilos diferentes de "card de número" convivendo na mesma área.

### 11.4 Empty states e alertas

`st.info("Nenhum ... encontrado")` → `empty_state(mensagem, icon)` em `page_sv_clientes.py`, `page_sv_ativos.py`, `page_sv_manutencao.py`, `page_sv_chamados.py`, `page_sv_chamado_detalhe.py`, `page_sv_biblioteca.py`, `page_sv_assistente.py`, `page_sv_alertas.py`, `page_sv_notificacoes.py` — só nos casos de "lista vazia"; mensagens de validação de formulário (ex.: "Preencha pergunta e resposta antes de salvar") continuam nativas (`st.warning`/`st.error`), porque são feedback transitório de uma ação, não um estado de tela. Dois avisos persistentes de conteúdo viraram `app_alert()`: o banner de "Modo Teste Ativo" (bloqueio de envio externo, `page_sv_notificacoes.py`) e a nota sobre senha em branco no cadastro de cliente (`page_sv_clientes.py`).

### 11.5 Hierarquia de botões

`page_sv_chamados.py::_render_card`: "👁️ Ver chamado" e "✅ Confirmar" (exclusão) apareciam lado a lado como `type="primary"` quando o card entrava em modo de confirmação de exclusão — "Ver chamado" agora vira `secondary` nesse estado. `page_sv_chamado_detalhe.py`: o botão "💾 Salvar" do painel de edição virou `primary` (era o único `secondary` entre os 3 formulários principais da página, sem motivo aparente).

### 11.6 O que não foi mexido (decisão de escopo desta etapa)

- Estrutura/HTML de cada card não foi reescrita — só as chamadas de cor/badge/métrica/empty-state trocaram de fonte. Mesma filosofia da Etapa 2 (§7).
- `page_sv_homologacao.py` e `page_sv_relatorio_executivo.py` ficaram de fora (uso interno raro / já auditadas antes). `page_sv_relatorios.py` também ficou de fora — foi mexida horas antes nesta mesma sessão por outro pedido (correção de bug de navegação + lixeira de relatórios).
- A pendência crítica da Visão Executiva (Etapa 1) e as duplicatas de dados de clientes reais (RJR, Vigor Alimentos) continuam em aberto — não fazem parte de ajuste visual.

### 11.7 Checks técnicos

`py -m py_compile` + `import` real de todos os módulos tocados (11 arquivos `.py`) — sem erro. Sem lint/typecheck/build configurado (mesma situação das etapas anteriores). Verificação visual do header feita via mockup HTML estático reproduzindo o DOM do Streamlit (ver §11.1) — não foi feito login real na Supervisão para captura de tela das páginas, porque isso exigiria credenciais de um usuário real da planilha de produção.

### 11.8 Confirmações

- Não foi criada sidebar.
- WhatsApp e e-mail não foram tocados (só o texto/estilo do aviso de bloqueio de envio, não a lógica).
- Login, permissões e `client_id` não foram alterados.
- GUT (cálculo/regra) não foi alterado — só o badge visual de prioridade GUT, que já existia.
- Nenhuma feature nova — todas as adições (`status_color()` em `ui.py`, `delete_technical_report_full()` em `sheets.py` de um pedido anterior nesta mesma sessão) são helpers, não regras de negócio novas.
