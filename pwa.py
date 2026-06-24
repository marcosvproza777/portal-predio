"""PWA support — ícones e botão 'Baixe o app'.

Usa st.components.v1.html() (iframe real) para garantir execução de JS.
O script acessa parent.document para injetar o botão no body da página principal.

ARQUITETURA: funções e estado no parent window (persistem entre reruns Streamlit).
Os event listeners são re-anexados via .onclick/.ontouchend a cada recarga do iframe.
"""
import os
import streamlit as st
import streamlit.components.v1 as components

_BASE  = os.path.dirname(__file__)
_ICONS = os.path.join(_BASE, "static", "icons")
_I192  = os.path.join(_ICONS, "icon-192.png")
_I512  = os.path.join(_ICONS, "icon-512.png")
_I180  = os.path.join(_ICONS, "icon-180.png")


def _ensure_icons() -> None:
    if all(os.path.exists(p) for p in (_I192, _I512, _I180)):
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
        for path, size in ((_I192, 192), (_I512, 512), (_I180, 180)):
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
    var pd = p.document;

    /* ── beforeinstallprompt: registra apenas uma vez no parent window ── */
    if (!p._ppwaListenerAdded) {
        p._ppwaDeferred = null;
        p.addEventListener('beforeinstallprompt', function (e) {
            e.preventDefault();
            p._ppwaDeferred = e;
        });
        p._ppwaListenerAdded = true;
    }

    /* ── Funções de modal: referenciam o DOM via getElementById (resilientes) ── */
    function openModal() {
        if (p._ppwaDeferred) {
            p._ppwaDeferred.prompt();
            p._ppwaDeferred.userChoice.then(function () { p._ppwaDeferred = null; });
            return;
        }
        var ov = pd.getElementById('ppwa-ov');
        if (ov) ov.classList.add('open');
    }

    function closeModal() {
        var ov = pd.getElementById('ppwa-ov');
        if (ov) ov.classList.remove('open');
    }

    /* ── Cria elementos DOM apenas uma vez ────────────────────────── */
    if (!pd.getElementById('ppwa-fab')) {

        function addMeta(name, content) {
            var m = pd.createElement('meta'); m.name = name; m.content = content;
            pd.head.appendChild(m);
        }
        var lnk = pd.createElement('link');
        lnk.rel = 'manifest'; lnk.href = '/app/static/manifest.json';
        pd.head.appendChild(lnk);
        addMeta('apple-mobile-web-app-capable', 'yes');
        addMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');
        addMeta('apple-mobile-web-app-title', 'Portal de Confiabilidade Pred.IO');
        addMeta('theme-color', '#1565C0');
        var ai = pd.createElement('link');
        ai.rel = 'apple-touch-icon'; ai.href = '/app/static/icons/icon-180.png';
        pd.head.appendChild(ai);

        var style = pd.createElement('style');
        style.textContent = [
            '#ppwa-fab{',
            'position:fixed;top:12px;right:14px;z-index:9990;',
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

    /* ── Re-anexa handlers a cada recarga do iframe (via .onclick/.ontouchend) ── */
    var _fab   = pd.getElementById('ppwa-fab');
    var _close = pd.getElementById('ppwa-close');
    var _ov    = pd.getElementById('ppwa-ov');

    if (_fab) {
        _fab.onclick = function () { openModal(); };
        _fab.ontouchend = function (e) { e.preventDefault(); openModal(); };
    }
    if (_close) {
        _close.onclick = function () { closeModal(); };
        _close.ontouchend = function (e) { e.preventDefault(); closeModal(); };
    }
    if (_ov) {
        _ov.onclick = function (e) { if (e.target === _ov) closeModal(); };
        _ov.ontouchend = function (e) {
            if (e.target === _ov) { e.preventDefault(); closeModal(); }
        };
    }
})();
</script>
</body></html>"""


def inject_pwa() -> None:
    """Injeta manifest, ícones Apple e botão flutuante 'Baixe o app'."""
    _ensure_icons()
    components.html(_HTML, height=0)
