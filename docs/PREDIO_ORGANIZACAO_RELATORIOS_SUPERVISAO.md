# Organização dos Relatórios Técnicos na Supervisão — Cliente → Tipo

## Objetivo

`/supervisao/relatorios` (`page_sv_relatorios.py`) deixou de listar todos os
relatórios técnicos numa lista só ordenada por data. Agora os relatórios são
agrupados primeiro por **Cliente**, depois por **Tipo (categoria)**, com
contadores, filtros e uma visão dedicada por cliente.

## Estrutura da lista principal

- Um `st.expander` por cliente (`👤 {Empresa} (N)`), **recolhido por
  padrão** — ver "Performance" abaixo.
- Dentro de cada cliente, `st.tabs`: "Todos" + uma aba por categoria
  presente naquele grupo, com contador (`Vibração (12)`).
- Dentro de cada aba, os relatórios são ordenados por:
  1. `Data_Relatorio` decrescente (nunca `Created_At`)
  2. Severidade (Urgente → Crítico → Atenção → Normal)
  3. `Ativo_Id`
- Botão "Ver cliente →" no cabeçalho de cada grupo abre a visão dedicada
  (`sv_view == "relatorios_cliente_detalhe"`).

## Categorias padronizadas

Definidas em `executive_summary.py` (`CATEGORIAS_RELATORIO` +
`categoria_relatorio()`) — fonte única reaproveitada tanto pela tela de
Relatórios quanto pelo filtro de tipo do Resumo Executivo, para as duas
nunca divergirem:

| Categoria | Aliases reconhecidos (normalizados, sem acento) |
|---|---|
| Vibração | vibracao |
| Termografia | termografia, termografico, termico |
| Ordem de Serviço | ordem de servico, os, ordem de assistencia, oat |
| Análise de Óleo | oleo |
| Alinhamento a Laser | alinhamento |
| Outros | qualquer valor não reconhecido |

**Importante**: `Tipo_Servico` nunca é reescrito. A categorização é só de
exibição/filtro — os valores reais gravados no relatório (incluindo os
valores livres vindos da integração do App Relatórios, ex.: `"Ordem de
Assistência (OAT)"`) permanecem intactos. `categoria_relatorio()` só
decide em qual aba/filtro aquele relatório aparece.

## Filtros disponíveis

Status, Severidade, Tipo (categoria), Cliente, e Período (data do
relatório) — presets de 7/30/90 dias, este mês, mês anterior ou
personalizado (mesmos presets do Resumo Executivo, `executive_summary.
PERIODOS_PRESET`/`resolver_periodo`).

## Visão dedicada por cliente

`_render_cliente_detalhe(client_id)` — mesmo padrão de navegação
lista↔detalhe já usado em `page_sv_clientes.py` (`st.session_state["sv_view"]`).
Mostra métricas (total + contagem por categoria), filtros de status/tipo
escopados a esse cliente, e a lista de relatórios agrupada por categoria
(reaproveita `_render_grupo_por_categoria`).

## Integração com o Assistente Técnico

Nenhuma mudança necessária — `assistant_lookup.localizar_relatorios()` e
`rotear_pergunta()` (implementados numa etapa anterior) já resolvem tipo
por valores REAIS de `Tipo_Servico` (não um enum fixo), já filtram por
cliente e período, e só usam relatórios `Status=="Publicado"`. A nova
organização visual da Supervisão não afeta esse caminho.

## Integração com o Resumo Executivo

Novo seletor "Tipo de relatório" no diálogo de geração
(`resumo_executivo_ui.py`) — usa as mesmas `CATEGORIAS_RELATORIO`.
`executive_summary.generate_executive_summary(..., tipo_servico=...)` e
`_coletar_dados(..., tipo_servico=...)` filtram os relatórios que entram
no resumo por essa categoria antes de montar o texto.

## Performance — limitação conhecida

Uma paginação/lazy-loading de verdade exigiria mudar como os dados são
buscados (hoje `load_sheet()` traz a aba `TechnicalReports` inteira,
cacheada 30s — é assim que o resto do projeto funciona; mudar isso é um
projeto maior). Mitigação aplicada agora: os grupos por cliente nascem
**recolhidos por padrão**, então o HTML dos cards só é montado para o
cliente que a Supervisão realmente abrir.

## Segurança

Isolamento entre clientes é uma regra do Portal do Cliente
(`get_technical_reports(staff=False)`), não da Supervisão — aqui
`staff=True` traz todos os clientes de propósito (é o trabalho da tela).
Nenhuma mudança nas regras de acesso do cliente comum.
