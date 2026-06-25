"""PWA support — ícones e botão 'Baixe o app'.

Usa st.components.v1.html() (iframe real) para garantir execução de JS.
O script acessa parent.document para injetar o botão no body da página principal.

ARQUITETURA:
- _ppwaOpen / _ppwaClose são gravadas no parent window (persistem entre reruns).
- Handlers re-anexados via .onclick/.ontouchend a cada recarga do iframe.
- Botão posicionado em top:68px para ficar abaixo do header Streamlit (z-index alto,
  fundo transparente — interceptaria cliques se o botão estivesse em top:12px).
"""
import os
import streamlit as st
import streamlit.components.v1 as components

_BASE  = os.path.dirname(__file__)
_ICONS = os.path.join(_BASE, "static", "icons")
_I32   = os.path.join(_ICONS, "icon-32.png")
_I180  = os.path.join(_ICONS, "icon-180.png")
_I192  = os.path.join(_ICONS, "icon-192.png")
_I512  = os.path.join(_ICONS, "icon-512.png")

_ICON_SIZES = [(_I32, 32), (_I180, 180), (_I192, 192), (_I512, 512)]


def _ensure_icons() -> None:
    """Gera ícones a partir de logo.jpg se não existirem."""
    if all(os.path.exists(p) for p, _ in _ICON_SIZES):
        return
    os.makedirs(_ICONS, exist_ok=True)
    logo = os.path.join(_BASE, "logo.jpg")
    if not os.path.exists(logo):
        return
    try:
        from PIL import Image
        img  = Image.open(logo).convert("RGBA")
        w, h = img.size
        side = max(w, h)
        bg   = Image.new("RGBA", (side, side), (8, 20, 43, 255))
        bg.paste(img, ((side - w) // 2, (side - h) // 2))
        for path, size in _ICON_SIZES:
            bg.resize((size, size), Image.LANCZOS).save(path, "PNG")
    except Exception:
        pass


_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;overflow:hidden;background:transparent;">
<script>
(function () {
    var p = window.parent;
    if (!p || p === window) return;

    /* ── beforeinstallprompt: registra apenas uma vez no parent window ── */
    if (!p._ppwaListenerAdded) {
        p._ppwaDeferred = null;
        p.addEventListener('beforeinstallprompt', function (e) {
            e.preventDefault();
            p._ppwaDeferred = e;
        });
        p._ppwaListenerAdded = true;
    }

    /* ── Funções no parent window — sobrevivem a reruns do iframe ────── */
    /* Usando p.document (lookup dinâmico) em vez de pd capturado no closure,
       para garantir que sempre referenciam o documento pai atual.          */
    p._ppwaOpen = function () {
        if (p._ppwaDeferred) {
            p._ppwaDeferred.prompt();
            p._ppwaDeferred.userChoice.then(function () { p._ppwaDeferred = null; });
            return;
        }
        var ov = p.document.getElementById('ppwa-ov');
        if (ov) ov.classList.add('open');
    };
    p._ppwaClose = function () {
        var ov = p.document.getElementById('ppwa-ov');
        if (ov) ov.classList.remove('open');
    };

    var pd = p.document;

    /* ── Substitui manifest e favicons do Streamlit pelos nossos ──────── */
    /* Faz isso a cada recarga para garantir (Streamlit re-injeta no rerun) */
    (function () {
        /* Remove todos os <link rel="manifest"> existentes */
        pd.querySelectorAll('link[rel="manifest"]').forEach(function(el) {
            el.parentNode.removeChild(el);
        });
        var lnk = pd.createElement('link');
        lnk.rel = 'manifest'; lnk.href = '/app/static/manifest.json';
        pd.head.appendChild(lnk);

        /* Substitui favicons do Streamlit pelo nosso ícone */
        pd.querySelectorAll('link[rel~="icon"]').forEach(function(el) {
            el.parentNode.removeChild(el);
        });
        ['icon-32.png','icon-192.png'].forEach(function(name, i) {
            var fi = pd.createElement('link');
            fi.rel  = 'icon';
            fi.type = 'image/png';
            fi.sizes = i === 0 ? '32x32' : '192x192';
            fi.href = '/app/static/icons/' + name;
            pd.head.appendChild(fi);
        });
    })();

    /* ── Cria elementos DOM apenas uma vez ────────────────────────────── */
    if (!pd.getElementById('ppwa-fab')) {

        function addMeta(name, content) {
            var m = pd.createElement('meta'); m.name = name; m.content = content;
            pd.head.appendChild(m);
        }
        addMeta('apple-mobile-web-app-capable', 'yes');
        addMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');
        addMeta('apple-mobile-web-app-title', 'Pred.IO');
        addMeta('theme-color', '#0F1F3D');
        var ai = pd.createElement('link');
        ai.rel = 'apple-touch-icon'; ai.href = '/app/static/icons/icon-180.png';
        pd.head.appendChild(ai);

        var style = pd.createElement('style');
        style.textContent = [
            /* Posicionado abaixo do header Streamlit (~60px) para evitar que o
               header transparente de alto z-index intercepte os cliques.        */
            '#ppwa-fab{',
            'position:fixed;top:68px;right:14px;z-index:999990;',
            'background:linear-gradient(135deg,#1565C0 0%,#2563EB 100%);',
            'color:#fff;border:none;border-radius:22px;',
            'padding:10px 16px 10px 12px;font-size:0.8rem;font-weight:700;',
            'cursor:pointer;display:flex;align-items:center;gap:6px;',
            'box-shadow:0 4px 18px rgba(21,101,192,0.55);',
            'font-family:sans-serif;white-space:nowrap;',
            '-webkit-tap-highlight-color:rgba(0,0,0,0);',
            'touch-action:manipulation;user-select:none;}',

            '#ppwa-ov{',
            'display:none;position:fixed;inset:0;',
            'background:rgba(0,0,0,0.58);z-index:2147483647;',
            'align-items:flex-end;justify-content:center;}',
            '#ppwa-ov.open{display:flex;}',

            '#ppwa-modal{',
            'background:#fff;border-radius:20px 20px 0 0;',
            'padding:26px 22px 40px;',
            'max-width:480px;width:100%;}',
            '#ppwa-modal h3{margin:0 0 8px;color:#0F1F3D;font-size:1.05rem;font-weight:700;}',
            '#ppwa-modal .sub{margin:0 0 16px;color:#475569;font-size:.85rem;line-height:1.5;}',
            '.ps{display:flex;gap:10px;align-items:flex-start;margin-bottom:12px;}',
            '.ps-i{font-size:1.2rem;flex-shrink:0;line-height:1;}',
            '.ps-t{font-size:.84rem;color:#334155;line-height:1.45;}',
            '.ps-t b{color:#0F1F3D;}',
            'hr.phr{border:none;border-top:1px solid #E2E8F0;margin:14px 0;}',
            '#ppwa-close{',
            'margin-top:16px;width:100%;background:#0F1F3D;color:#fff;',
            'border:none;border-radius:10px;padding:13px;',
            'font-size:.9rem;font-weight:700;cursor:pointer;',
            '-webkit-tap-highlight-color:rgba(0,0,0,0);',
            'touch-action:manipulation;}'
        ].join('');
        pd.head.appendChild(style);

        var fab = pd.createElement('button');
        fab.id = 'ppwa-fab';
        fab.type = 'button';
        fab.innerHTML = '&#128242;&nbsp;Baixe o app';
        pd.body.appendChild(fab);

        var ov = pd.createElement('div');
        ov.id = 'ppwa-ov';
        ov.innerHTML = [
            '<div id="ppwa-modal">',
            '<h3>&#128242; Instalar Pred.IO</h3>',
            '<p class="sub">Adicione o portal à tela inicial do seu celular ',
            'para acessar sem abrir o navegador.</p>',

            '<div class="ps"><div class="ps-i">&#128241;</div>',
            '<div class="ps-t"><b>iPhone / iPad &mdash; Safari:</b></div></div>',
            '<div class="ps"><div class="ps-i">1&#65039;&#8419;</div>',
            '<div class="ps-t">Toque no &#128279; <b>Compartilhar</b> ',
            '(quadrado com seta &uarr;) na barra inferior do Safari</div></div>',
            '<div class="ps"><div class="ps-i">2&#65039;&#8419;</div>',
            '<div class="ps-t">Role e toque em <b>Adicionar &agrave; Tela de In&iacute;cio</b></div></div>',
            '<div class="ps"><div class="ps-i">3&#65039;&#8419;</div>',
            '<div class="ps-t">Toque em <b>Adicionar</b> &mdash; pronto!</div></div>',

            '<hr class="phr">',

            '<div class="ps"><div class="ps-i">&#129503;</div>',
            '<div class="ps-t"><b>Android &mdash; Chrome:</b></div></div>',
            '<div class="ps"><div class="ps-i">1&#65039;&#8419;</div>',
            '<div class="ps-t">Toque no menu <b>&vellip;</b> (tr&ecirc;s pontos) no Chrome</div></div>',
            '<div class="ps"><div class="ps-i">2&#65039;&#8419;</div>',
            '<div class="ps-t">Toque em <b>Adicionar &agrave; tela inicial</b> ',
            'ou <b>Instalar app</b> e confirme</div></div>',

            '<button id="ppwa-close" type="button">Entendi</button>',
            '</div>'
        ].join('');
        pd.body.appendChild(ov);
    }

    /* ── Re-anexa handlers a cada recarga do iframe ──────────────────── */
    /* Chamam p._ppwaOpen / p._ppwaClose que residem no parent window    */
    var _fab   = pd.getElementById('ppwa-fab');
    var _close = pd.getElementById('ppwa-close');
    var _ov    = pd.getElementById('ppwa-ov');

    if (_fab) {
        _fab.onclick    = function ()  { p._ppwaOpen(); };
        _fab.ontouchend = function (e) { e.preventDefault(); p._ppwaOpen(); };
    }
    if (_close) {
        _close.onclick    = function ()  { p._ppwaClose(); };
        _close.ontouchend = function (e) { e.preventDefault(); p._ppwaClose(); };
    }
    if (_ov) {
        _ov.onclick    = function (e)  { if (e.target === _ov) p._ppwaClose(); };
        _ov.ontouchend = function (e)  {
            if (e.target === _ov) { e.preventDefault(); p._ppwaClose(); }
        };
    }
})();
</script>
</body></html>"""


def inject_pwa() -> None:
    """Injeta manifest, ícones Apple e botão flutuante 'Baixe o app'."""
    _ensure_icons()
    components.html(_HTML, height=1)


# ─────────────────────────────────────────────────────────────────────────────
# CSS mobile responsivo global
# ─────────────────────────────────────────────────────────────────────────────

_MOBILE_CSS = """<style>
/* ── Viewport e texto ── */
html { -webkit-text-size-adjust: 100%; }

/* ── Sidebar suprimida no portal cliente ── */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarExpandButton"],
[data-testid="collapsedControl"],
.stSidebarResizeHandle { display: none !important; }

/* ── Toque responsivo ── */
* { -webkit-tap-highlight-color: transparent; scroll-behavior: smooth; }

/* ── MOBILE ── */
@media (max-width: 768px) {
  /* Botões com touch target mínimo 44px */
  .stButton > button {
    min-height: 44px !important;
    font-size: 0.88rem !important;
    border-radius: 10px !important;
    padding: 9px 14px !important;
    touch-action: manipulation;
  }
  /* Inputs sem zoom no iOS (mínimo 16px) */
  .stTextInput input,
  .stTextArea textarea,
  .stSelectbox select,
  [data-baseweb="select"] input {
    font-size: 16px !important;
    min-height: 44px !important;
  }
  /* Texto legível */
  .stMarkdown p, .stMarkdown li { font-size: 0.9rem !important; }
  /* Padding lateral compacto */
  [data-testid="stMainBlockContainer"] {
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
    padding-bottom: 72px !important;
  }
  /* Métricas menores */
  [data-testid="stMetric"] label { font-size: 0.7rem !important; }
  [data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.25rem !important; }
  /* Expanders touch-friendly */
  [data-testid="stExpander"] summary {
    padding: 12px 16px !important;
    font-size: 0.88rem !important;
    min-height: 44px;
  }
  /* Tabs scroll horizontal */
  [data-testid="stTabs"] [role="tablist"] {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none;
    flex-wrap: nowrap !important;
  }
  [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar { display: none; }
  [data-baseweb="tab"] {
    padding: 10px 14px !important;
    font-size: 0.82rem !important;
    white-space: nowrap;
  }
  /* Topnav scrollável */
  .portal-nav-marker + div,
  .portal-nav-marker ~ [data-testid="stHorizontalBlock"] {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    scrollbar-width: none !important;
    flex-wrap: nowrap !important;
  }
  .portal-nav-marker + div::-webkit-scrollbar,
  .portal-nav-marker ~ [data-testid="stHorizontalBlock"]::-webkit-scrollbar {
    display: none !important;
  }
  /* Colunas — mínimo legível */
  [data-testid="column"] { min-width: 130px; }
  /* Link buttons mobile */
  [data-testid="stLinkButton"] a {
    min-height: 44px !important;
    display: flex !important;
    align-items: center !important;
  }
}

/* ── Cards responsivos: 2 colunas no mobile ── */
@media (max-width: 640px) {
  /* Permite que colunas de conteúdo quebrem linha */
  [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 8px !important;
  }
  [data-testid="stMainBlockContainer"] [data-testid="column"] {
    flex: 1 1 calc(50% - 8px) !important;
    min-width: 140px !important;
  }
  /* Topnav: NÃO quebra, scrollável */
  div.portal-nav-marker ~ [data-testid="stHorizontalBlock"],
  div.portal-nav-marker + [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    gap: 4px !important;
  }
  div.portal-nav-marker ~ [data-testid="stHorizontalBlock"] [data-testid="column"],
  div.portal-nav-marker + [data-testid="stHorizontalBlock"] [data-testid="column"] {
    flex: 0 0 auto !important;
    min-width: 52px !important;
    max-width: 82px !important;
  }
}

/* ── MOBILE PEQUENO ── */
@media (max-width: 480px) {
  h1 { font-size: 1.25rem !important; }
  h2 { font-size: 1.1rem !important; }
  h3 { font-size: 0.95rem !important; }
  [data-testid="stMainBlockContainer"] {
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
  }
  /* Coluna única em telas muito pequenas */
  [data-testid="stMainBlockContainer"] [data-testid="column"] {
    flex: 1 1 100% !important;
    min-width: 100% !important;
  }
  /* Exceto topnav */
  div.portal-nav-marker ~ [data-testid="stHorizontalBlock"] [data-testid="column"],
  div.portal-nav-marker + [data-testid="stHorizontalBlock"] [data-testid="column"] {
    flex: 0 0 auto !important;
    min-width: 52px !important;
    max-width: 82px !important;
  }
}
</style>"""


# ─────────────────────────────────────────────────────────────────────────────
# Bottom nav mobile
# ─────────────────────────────────────────────────────────────────────────────

_BOTTOM_NAV_ITEMS = [
    ("dashboard",  "🏠", "Home"),
    ("ativos",     "⚙️",  "Ativos"),
    ("manutencao", "📅", "Manutenção"),
    ("chamados",   "🔧", "Chamados"),
    ("_more",      "⋯",  "Mais"),
]

_MORE_ITEMS = [
    ("notificacoes", "🔔", "Avisos"),
    ("alertas",      "⚠️",  "Alertas"),
    ("relatorios",   "📁", "Relatórios"),
    ("biblioteca",   "📚", "Biblioteca"),
    ("preferencias", "📱", "Config."),
]


def _bottom_nav_html(portal_page: str) -> str:
    import json
    nav_json  = json.dumps([[k, i, l] for k, i, l in _BOTTOM_NAV_ITEMS])
    more_json = json.dumps([[k, i, l] for k, i, l in _MORE_ITEMS])

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;overflow:hidden;background:transparent;">
<script>
(function() {{
  var p  = window.parent;
  if (!p || p === window) return;
  var pd = p.document;
  if (pd.getElementById('pred-bottom-nav')) return;   // evita duplicata

  var active   = "{portal_page}";
  var navItems = {nav_json};
  var moreItems= {more_json};

  // ── Estilos ──
  var sty = pd.createElement('style');
  sty.id = 'pred-bn-css';
  sty.textContent = [
    '@media(min-width:769px){{',
      '#pred-bottom-nav,#pred-more-menu{{display:none!important;}}',
    '}}',
    '#pred-bottom-nav{{',
      'position:fixed;bottom:0;left:0;right:0;height:58px;',
      'background:linear-gradient(180deg,#0A1830 0%,#071122 100%);',
      'border-top:1px solid rgba(30,58,138,.8);',
      'display:flex;align-items:stretch;',
      'z-index:999990;',
      'box-shadow:0 -2px 20px rgba(7,17,34,.65);',
      '-webkit-tap-highlight-color:transparent;',
      'padding-bottom:env(safe-area-inset-bottom,0px);',
    '}}',
    '.pred-bn-item{{',
      'flex:1;display:flex;flex-direction:column;align-items:center;',
      'justify-content:center;gap:2px;cursor:pointer;',
      'padding:6px 2px;border:none;background:transparent;',
      'position:relative;transition:background .12s;',
      '-webkit-tap-highlight-color:transparent;touch-action:manipulation;',
    '}}',
    '.pred-bn-item:active{{background:rgba(56,189,248,.1);}}',
    '.pred-bn-item.pred-active::before{{',
      'content:"";position:absolute;top:0;left:50%;transform:translateX(-50%);',
      'width:36px;height:2px;background:#38BDF8;border-radius:0 0 3px 3px;',
    '}}',
    '.pred-bn-icon{{font-size:1.2rem;line-height:1;}}',
    '.pred-bn-label{{font-size:.58rem;font-weight:600;letter-spacing:.04em;white-space:nowrap;}}',
    '.pred-bn-label,.pred-bn-item .pred-bn-label{{color:#64748B;-webkit-text-fill-color:#64748B;}}',
    '.pred-bn-item.pred-active .pred-bn-label{{color:#38BDF8;-webkit-text-fill-color:#38BDF8;}}',
    '#pred-more-menu{{',
      'position:fixed;bottom:58px;left:0;right:0;',
      'background:#0D1A38;border-top:1px solid rgba(30,58,138,.7);',
      'padding:6px 0;z-index:999991;display:none;',
      'box-shadow:0 -6px 32px rgba(7,17,34,.7);',
      'padding-bottom:env(safe-area-inset-bottom,0px);',
    '}}',
    '#pred-more-menu.pred-open{{display:block;}}',
    '.pred-more-item{{',
      'display:flex;align-items:center;gap:14px;',
      'padding:13px 20px;cursor:pointer;',
      'transition:background .1s;',
      '-webkit-tap-highlight-color:transparent;touch-action:manipulation;',
    '}}',
    '.pred-more-item:active{{background:rgba(56,189,248,.1);}}',
    '.pred-more-icon{{font-size:1.1rem;width:26px;text-align:center;flex-shrink:0;}}',
    '.pred-more-label{{font-size:.9rem;color:#CBD5E1;-webkit-text-fill-color:#CBD5E1;font-weight:500;}}',
  ].join('');
  pd.head.appendChild(sty);

  // ── Nav bar ──
  var nav = pd.createElement('div');
  nav.id  = 'pred-bottom-nav';
  nav.setAttribute('role','navigation');
  nav.setAttribute('aria-label','Menu principal mobile');

  navItems.forEach(function(item) {{
    var key = item[0], icon = item[1], label = item[2];
    var btn = pd.createElement('button');
    btn.className = 'pred-bn-item' + (key === active ? ' pred-active' : '');
    btn.setAttribute('aria-label', label);
    btn.innerHTML = '<span class="pred-bn-icon">' + icon + '</span>' +
                    '<span class="pred-bn-label">' + label + '</span>';
    btn.onclick = function(e) {{
      e.preventDefault();
      if (key === '_more') {{
        var mm = pd.getElementById('pred-more-menu');
        if (mm) mm.classList.toggle('pred-open');
        return;
      }}
      var mm = pd.getElementById('pred-more-menu');
      if (mm) mm.classList.remove('pred-open');
      _navTo(key);
    }};
    nav.appendChild(btn);
  }});
  pd.body.appendChild(nav);

  // ── Menu "Mais" ──
  var moreDiv = pd.createElement('div');
  moreDiv.id  = 'pred-more-menu';
  moreItems.forEach(function(item) {{
    var key = item[0], icon = item[1], label = item[2];
    var row = pd.createElement('div');
    row.className = 'pred-more-item';
    row.setAttribute('role','button');
    row.setAttribute('tabindex','0');
    row.innerHTML = '<span class="pred-more-icon">' + icon + '</span>' +
                    '<span class="pred-more-label">' + label + '</span>';
    row.onclick = function() {{
      moreDiv.classList.remove('pred-open');
      _navTo(key);
    }};
    moreDiv.appendChild(row);
  }});
  pd.body.appendChild(moreDiv);

  // ── Fecha menu ao clicar fora ──
  pd.addEventListener('click', function(e) {{
    var mm = pd.getElementById('pred-more-menu');
    var bn = pd.getElementById('pred-bottom-nav');
    if (mm && bn && !bn.contains(e.target) && !mm.contains(e.target)) {{
      mm.classList.remove('pred-open');
    }}
  }});

  function _navTo(page) {{
    if (p.predNavTo) {{ p.predNavTo(page); return; }}
    var btns = pd.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {{
      if (btns[i].textContent.trim() === '\\u25b8' + page) {{ btns[i].click(); return; }}
    }}
  }}
}})();
</script>
</body></html>"""


def inject_mobile_css() -> None:
    """Injeta CSS responsivo global para mobile. Chamar no início do render do portal."""
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)


def inject_bottom_nav(portal_page: str = "dashboard") -> None:
    """
    Injeta o menu inferior fixo para mobile (escondido em desktop via CSS).
    Chamar uma vez por render, após o topnav.
    """
    _ensure_icons()
    components.html(_bottom_nav_html(portal_page), height=0, scrolling=False)


def remove_bottom_nav() -> None:
    """Remove o menu inferior do DOM (chamado na tela de login / logout)."""
    components.html("""<!DOCTYPE html><html><head></head><body style="margin:0">
<script>
(function(){
  var p=window.parent; if(!p||p===window)return;
  var pd=p.document;
  ['pred-bottom-nav','pred-more-menu','pred-bn-css'].forEach(function(id){
    var el=pd.getElementById(id); if(el)el.remove();
  });
})();
</script>
</body></html>""", height=0)


def inject_all(portal_page: str = "dashboard") -> None:
    """
    Injeta tudo de uma vez: manifest/ícones, CSS mobile e bottom nav.
    Chamado no início de _render_portal em app.py.
    """
    inject_mobile_css()
    inject_pwa()
    inject_bottom_nav(portal_page)
