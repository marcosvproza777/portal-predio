"""Persistência de sessão no navegador — Portal Pred.IO.

O projeto usa autenticação PRÓPRIA (não Supabase/Firebase/NextAuth):
token opaco (secrets.token_urlsafe) validado contra a aba "Sessions" do
Google Sheets (sheets.get_session/save_session/delete_session — já com
expiração de 7 dias e revogação via coluna "Ativo"). Até aqui, esse token
só vivia na URL (?sid=...), então fechar o navegador e reabrir numa aba
nova (sem esse parâmetro) perdia a sessão mesmo com o token ainda válido
no servidor.

Este módulo NÃO cria autenticação paralela — só estende a persistência do
MESMO token para o localStorage do navegador, para sobreviver ao fechar/
reabrir no mesmo dispositivo. A validação de validade/expiração/revogação
continua 100% no servidor (get_session); o localStorage só guarda o
identificador opaco, nunca senha nem dado sensível.

SEGURANÇA:
- Só grava o token opaco (mesmo já exposto na URL) — nunca senha.
- Nenhuma lógica de "lembrar senha".
- Logout limpa o localStorage.
- client_id nunca é lido do localStorage — sempre vem de get_session()
  no servidor, a partir do token.

Usa st.components.v1.html (iframe) + window.parent, mesmo padrão já usado
em pwa.py para garantir execução confiável do JS.
"""
import json
import streamlit as st
import streamlit.components.v1 as components

_LS_KEY = "predio_sid"


def inject_session_restore_check() -> None:
    """Chamado quando NÃO há sessão ativa e a URL não tem ?sid= nem
    ?nosess=. Verifica o localStorage no navegador; se houver um token
    salvo, recarrega a página com ?sid=<token> (o fluxo Python existente
    then valida contra o servidor). Se não houver, recarrega com
    ?nosess=1 para não tentar de novo e cair direto na tela de login.

    O iframe do components.html do Streamlit é sandboxed SEM
    allow-top-navigation — chamar parent.location.replace() diretamente
    daqui é silenciosamente bloqueado pelo navegador (localStorage
    funciona porque isso é regido por allow-same-origin, não pela
    restrição de navegação). Contorno: cria um <script> dentro do
    parent.document (não do iframe) — esse script roda no contexto do
    documento pai, sem nenhuma restrição de sandbox, e aí sim pode navegar.
    """
    inner_js = f"""
    (function() {{
        try {{
            var url = new URL(window.location.href);
            if (url.searchParams.has('sid') || url.searchParams.has('nosess')) return;
            var token = window.localStorage.getItem('{_LS_KEY}');
            if (token) {{
                url.searchParams.set('sid', token);
            }} else {{
                url.searchParams.set('nosess', '1');
            }}
            window.location.replace(url.toString());
        }} catch (e) {{}}
    }})();
    """
    inner_js_json = json.dumps(inner_js)
    components.html(
        f"""
        <script>
        try {{
            var pd = window.parent.document;
            var s = pd.createElement('script');
            s.textContent = {inner_js_json};
            pd.head.appendChild(s);
        }} catch (e) {{}}
        </script>
        """,
        height=0,
    )


def inject_session_save(sid: str) -> None:
    """Chamado em toda renderização autenticada — mantém o localStorage
    sincronizado com o token de sessão válido atual. Idempotente."""
    if not sid:
        return
    sid_js = json.dumps(sid)
    components.html(
        f"""
        <script>
        try {{
            if (window.parent.localStorage.getItem('{_LS_KEY}') !== {sid_js}) {{
                window.parent.localStorage.setItem('{_LS_KEY}', {sid_js});
            }}
        }} catch (e) {{}}
        </script>
        """,
        height=0,
    )


def inject_session_clear() -> None:
    """Chamado após logout (ou quando um token salvo se mostra inválido/
    expirado/revogado no servidor) — remove o token do localStorage para
    impedir entrada automática depois."""
    components.html(
        f"""
        <script>
        try {{ window.parent.localStorage.removeItem('{_LS_KEY}'); }} catch (e) {{}}
        </script>
        """,
        height=0,
    )


def render_loading_screen() -> None:
    """Loading curto exibido só enquanto o token salvo no navegador está
    sendo validado — evita o flash da tela de login para quem já tem
    sessão válida."""
    st.markdown(
        """
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;height:70vh;gap:0.75rem;">
            <div style="width:38px;height:38px;border-radius:50%;
                        border:3px solid #E2E8F0;border-top-color:#2563EB;
                        animation:predio-spin 0.8s linear infinite;"></div>
            <p style="color:#64748B;font-size:0.85rem;">Verificando sessão…</p>
        </div>
        <style>
        @keyframes predio-spin { to { transform: rotate(360deg); } }
        </style>
        """,
        unsafe_allow_html=True,
    )
