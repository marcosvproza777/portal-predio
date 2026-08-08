# Experiência Mobile / PWA Premium — Etapa 9

> Data: 2026-08-08 | Escopo: CSS responsivo, menu mobile, PWA, cache seguro | Sem sidebar, sem alteração de cliente_id

## 0. Contexto — o que já existia vs. o que foi feito nesta etapa

Ao investigar antes de codar, a maior parte da infraestrutura pedida nesta etapa **já estava implementada** em `pwa.py` e `ui.py`, construída incrementalmente nas Etapas 2–8 (Design System, GUT, layout do portal). O trabalho real desta etapa foi: **auditar** o que existe contra os 15 itens do pedido, **verificar** em navegador real (não só leitura de código), e **corrigir bugs reais encontrados durante essa verificação** — dois deles graves o suficiente para quebrar a tela de Ativos para todos os clientes (ver §7).

## 1. Rotas revisadas

Todas as rotas do portal do cliente (`dashboard`, `ativos`, `ativos/[id]`, `manutencao`, `relatorios`, `chamados`, `alertas`, `biblioteca`, `notificacoes`) já herdam o CSS responsivo global e o bottom nav injetados uma única vez em `app.py::_render_portal` via `pwa.inject_all()`. Não há necessidade de ajuste por tela — o layout de cada página já usa `st.columns()`, que o CSS mobile (`pwa._MOBILE_CSS`) reorganiza automaticamente por breakpoint.

Supervisão (`/supervisao/*`) não recebeu ajuste mobile dedicado — o pedido dizia "se for simples", e a Supervisão é usada majoritariamente em desktop pela equipe Pred.IO; não há bottom nav nem CSS mobile específico lá, mantendo o escopo como estava.

## 2. Menu mobile

**Já implementado, sem sidebar**: menu inferior fixo (`pwa.inject_bottom_nav`) com 5 itens — Home, Ativos, Manutenção, Chamados, e "Mais" (abre drawer com Avisos, Alertas, Relatórios, Biblioteca, Config.). Visível apenas em telas ≤768px (`@media(min-width:769px){display:none}`), com `env(safe-area-inset-bottom)` para aparelhos com notch/gesture bar. Confirmado via inspeção do DOM que os elementos do bottom nav existem e são corretamente ocultados/exibidos por media query.

## 3. Cards e tabelas no mobile

CSS global (`pwa._MOBILE_CSS`) já cobre:
- Botões com altura mínima de 44px (touch target)
- Inputs com `font-size:16px` (evita zoom automático no iOS)
- Colunas viram 2 por linha em ≤640px e 1 por linha em ≤480px — exceto o topnav, que permanece em uma linha só com scroll horizontal
- Tabs e topnav com scroll horizontal suave, sem quebrar
- Métricas (`st.metric`) com fonte reduzida para caber

## 4. Bug real encontrado e corrigido: cards de Ativos/Faróis vazando HTML cru no mobile e no desktop

Ao testar a tela de Ativos com dados reais (ver Etapa 10), os cards apareciam com HTML cru vazando na tela em vez de renderizar como cartão — **não é um problema exclusivo de mobile, mas afeta diretamente a legibilidade em telas pequenas**, onde o bug é mais visível por haver menos espaço.

**Causa raiz**: em `page_ativos.py::_render_card` e `page_farois.py`, o HTML do card é montado como uma f-string multi-linha passada a `st.markdown(..., unsafe_allow_html=True)`. Quando um campo opcional fica vazio (ex.: `{gut_badge_html}` sem GUT definido), a linha correspondente vira uma linha em branco no meio do HTML. O Markdown do Streamlit interpreta essa linha em branco como fim do bloco HTML e passa a tratar o restante como texto/código literal — daí o vazamento.

**Correção**: em ambos os arquivos, o HTML do card agora é montado em uma variável e filtrado (`"\n".join(line for line in html.splitlines() if line.strip())`) antes de ir para `st.markdown()`, removendo linhas em branco geradas por interpolações vazias. Testado visualmente no navegador antes e depois da correção — confirmado que os 3 cards de teste (antes quebrados) passaram a renderizar corretamente.

## 5. Assistente Técnico no mobile

Já implementado em `ui.py::inject_floating_assistant`, com media query dedicada (`@media(max-width:768px)`):
- Botão flutuante sobe para `bottom:72px` no mobile (acima do bottom nav de 58px, evitando sobreposição)
- Janela de chat vira `calc(100vw - 16px)` de largura, `bottom:140px`, `max-height:62vh` — cabe na tela sem cobrir o bottom nav
- Botão de fechar/minimizar sempre visível no cabeçalho do chat
- "Assistente Técnico Pred.IO" identificado no cabeçalho — fonte visível
- Não foi transformado em sidebar

**Limitação conhecida, não testada**: comportamento exato quando o teclado virtual do celular abre (iOS/Android tratam `position:fixed` de formas diferentes ao redimensionar a viewport pelo teclado). Não há tratamento via `visualViewport` API. Recomendação: validar em dispositivo físico antes de considerar 100% resolvido — não foi possível emular teclado mobile real nas ferramentas de navegador disponíveis nesta sessão.

## 6. PWA

Manifest (`static/manifest.json`) já configurado: nome "Pred.IO", `display: standalone`, `theme_color`/`background_color` definidos, ícones 192/512/180px, `orientation: portrait`. `start_url` está como `"/"` (não `/portal/dashboard` como o pedido sugeria) — mantido assim de propósito: o Streamlit não tem roteamento de URL real por página, e `/` já cai direto no dashboard após login, tornando os dois equivalentes na prática.

Botão "Baixe o app" (`pwa.inject_pwa`) já cobre o fluxo de instalação: usa `beforeinstallprompt` no Android/Chrome, e mostra passo-a-passo manual para iOS/Safari (que não suporta o prompt nativo). Banner de atualização (`version.txt` com polling a cada 3 min) também já existe.

## 7. Cache seguro

Service worker (`static/sw.js`) já implementa exatamente a regra pedida — **verificado por leitura, não alterado**:
- **Cacheável**: apenas `.png`, `.svg`, `.ico`, `manifest.json` dentro de `/app/static/`
- **Nunca cacheável**: qualquer coisa em `/api/`, `.pdf`, e URLs contendo `token`, `session`, `client_id`, `sid=`, `relatorio`, `chamado`, `ativo`, `alerta`, `documento`, `_stcore/`, `stream`, `websocket`
- Apenas requisições `GET` são interceptadas — POST/PUT/DELETE sempre passam direto
- Fora do escopo `/app/static/`, nada é interceptado

## 8. Segurança

Nenhuma mudança nesta etapa tocou `client_id`, login ou permissões. O bug de HTML corrigido em §4 é puramente de apresentação (CSS/render) — não altera nenhuma consulta a dados nem exposição de campo.

## 9. Testes

| # | Teste | Resultado |
|---|---|---|
| 1 | Login | ✅ testado no navegador com o cliente de teste (Etapa 10) |
| 2 | Dashboard | ✅ carrega sem erro, sem tela branca, métricas corretas |
| 3 | Lista de ativos | ✅ após correção do bug de HTML — 3 cards renderizando corretamente |
| 4 | Detalhe do ativo | ⚠️ não testado visualmente nesta etapa (verificado só a lista) |
| 5 | Manutenção com GUT | ⚠️ não testado visualmente nesta etapa (coberto por testes automatizados em etapas anteriores) |
| 6-9 | Relatórios / Chamados / Alertas / Biblioteca | ⚠️ não testados visualmente nesta etapa — dados corretos confirmados via script (Etapa 10 §testes de segurança) |
| 10 | Assistente Técnico | ✅ testado via script com perguntas reais (Etapa 10) |
| 11 | PWA instalável | ✅ verificado por leitura de código (manifest + sw.js corretos); **não testado em dispositivo físico real** |
| 12 | Cliente A não vê Cliente B | ✅ testado e confirmado (Etapa 10) |

**Limitação da verificação mobile**: as ferramentas de automação de navegador disponíveis nesta sessão não conseguiram emular um viewport mobile real (a tentativa de redimensionar a janela para 390×844px não alterou o layout renderizado) — a verificação mobile foi feita por **leitura cuidadosa do CSS/media queries** (confirmando breakpoints, z-index, posicionamento) e pela **presença confirmada dos elementos de bottom nav no DOM**, não por captura de tela em resolução mobile real. Recomendo um teste manual num celular real antes de liberar para cliente.

## 10. O que ficou de fora (com motivo)

- **Supervisão mobile**: não ajustada — uso é majoritariamente desktop, e o pedido permitia pular se não fosse simples.
- **Teste em dispositivo físico (iOS/Android)**: não possível nesta sessão (sem acesso a hardware real); infraestrutura de instalação já existe e foi revisada por código.
- **`visualViewport` API para o teclado mobile**: não implementado — risco baixo-médio, mas não verificado.

## 11. Arquivos alterados

`page_ativos.py`, `page_farois.py` (correção do bug de HTML vazando — não exclusivo de mobile, mas corrigido nesta etapa por ter sido encontrado durante a verificação mobile).

## 12. Arquivos criados

`docs/PREDIO_MOBILE_PWA.md`

## 13. Confirmações pedidas

- Não foi criada sidebar.
- WhatsApp e e-mail não foram tocados.
- Login e permissões não foram alterados.
- `client_id` não foi tocado.
- Nenhum comando remoto foi criado.
