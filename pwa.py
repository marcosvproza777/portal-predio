"""PWA support — ícones, manifest e botão 'Baixe o app'.

Injeta o botão via JavaScript puro (appended ao document.body),
evitando conflitos com o React/Streamlit e problemas de touch no Safari iOS.
"""
import os
import streamlit as st

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


_JS = """
<script>
(function () {
    /* guard: executa apenas uma vez por carregamento de página */
    if (window.__predPWA) return;
    window.__predPWA = true;

    function boot() {
        if (!document.body) { setTimeout(boot, 30); return; }

        /* ── manifest + meta tags Apple no <head> ─────────────────── */
        var link = document.createElement('link');
        link.rel  = 'manifest';
        link.href = '/app/static/manifest.json';
        document.head.appendChild(link);

        [['apple-mobile-web-app-capable','yes'],
         ['apple-mobile-web-app-status-bar-style','black-translucent'],
         ['apple-mobile-web-app-title','Pred.IO'],
         ['theme-color','#1565C0']
        ].forEach(function(m){
            var el = document.createElement('meta');
            el.name = m[0]; el.content = m[1];
            document.head.appendChild(el);
        });
        var ai = document.createElement('link');
        ai.rel  = 'apple-touch-icon';
        ai.href = '/app/static/icons/icon-180.png';
        document.head.appendChild(ai);

        /* ── estilos ──────────────────────────────────────────────── */
        var css = document.createElement('style');
        css.textContent =
            '#ppwa-fab{'
            + 'position:fixed;bottom:28px;right:18px;z-index:2147483647;'
            + 'background:linear-gradient(135deg,#1565C0 0%,#2563EB 100%);'
            + 'color:#fff !important;border:none;border-radius:22px;'
            + 'padding:10px 16px 10px 12px;font-size:0.8rem;font-weight:700;'
            + 'cursor:pointer;display:flex;align-items:center;gap:6px;'
            + 'box-shadow:0 4px 18px rgba(21,101,192,0.55);'
            + 'font-family:sans-serif;white-space:nowrap;'
            + '-webkit-tap-highlight-color:rgba(0,0,0,0);'
            + 'touch-action:manipulation;user-select:none;}'

            + '#ppwa-overlay{'
            + 'display:none;position:fixed;inset:0;'
            + 'background:rgba(0,0,0,0.58);z-index:2147483647;'
            + 'align-items:flex-end;justify-content:center;'
            + '-webkit-tap-highlight-color:rgba(0,0,0,0);}'
            + '#ppwa-overlay.open{display:flex;}'

            + '#ppwa-modal{'
            + 'background:#fff;border-radius:20px 20px 0 0;'
            + 'padding:28px 22px 40px;max-width:480px;width:100%;'
            + 'padding-bottom:calc(40px + env(safe-area-inset-bottom,0px));}'
            + '#ppwa-modal h3{margin:0 0 8px;color:#0F1F3D;font-size:1.05rem;font-weight:700;}'
            + '#ppwa-modal .sub{margin:0 0 18px;color:#475569;font-size:.85rem;line-height:1.5;}'

            + '.pst{display:flex;gap:12px;align-items:flex-start;margin-bottom:14px;}'
            + '.pst-i{font-size:1.3rem;flex-shrink:0;line-height:1;}'
            + '.pst-t{font-size:.84rem;color:#334155;line-height:1.45;}'
            + '.pst-t b{color:#0F1F3D;}'

            + '#ppwa-close{'
            + 'margin-top:16px;width:100%;background:#0F1F3D;color:#fff;'
            + 'border:none;border-radius:10px;padding:13px;'
            + 'font-size:.9rem;font-weight:700;cursor:pointer;'
            + '-webkit-tap-highlight-color:rgba(0,0,0,0);'
            + 'touch-action:manipulation;}';
        document.head.appendChild(css);

        /* ── botão FAB ────────────────────────────────────────────── */
        var fab = document.createElement('button');
        fab.id = 'ppwa-fab';
        fab.setAttribute('type','button');
        fab.innerHTML = '&#128242;&nbsp;Baixe o app';
        document.body.appendChild(fab);

        /* ── modal ────────────────────────────────────────────────── */
        var ov = document.createElement('div');
        ov.id = 'ppwa-overlay';
        ov.innerHTML =
            '<div id="ppwa-modal">'
            + '<h3>&#128242; Instalar Pred.IO</h3>'
            + '<p class="sub">Adicione o portal à tela inicial do seu celular para acessar sem abrir o navegador.</p>'
            + '<div id="ppwa-steps"></div>'
            + '<button id="ppwa-close" type="button">Entendi</button>'
            + '</div>';
        document.body.appendChild(ov);

        /* ── lógica PWA ───────────────────────────────────────────── */
        var deferred = null;
        window.addEventListener('beforeinstallprompt', function (e) {
            e.preventDefault();
            deferred = e;
        });

        function st(icon, txt) {
            return '<div class="pst"><div class="pst-i">'
                 + icon + '</div><div class="pst-t">' + txt + '</div></div>';
        }

        function getSteps() {
            var ua = navigator.userAgent;
            if (/iPad|iPhone|iPod/.test(ua)) {
                return st('1&#65039;&#8419;', 'Toque no ícone <b>Compartilhar</b> &#128279; (quadrado com seta ↑) na barra inferior do Safari')
                     + st('2&#65039;&#8419;', 'Role a lista e toque em <b>Adicionar à Tela de Início</b>')
                     + st('3&#65039;&#8419;', 'Toque em <b>Adicionar</b> no canto superior direito — pronto!');
            }
            if (/Android/.test(ua)) {
                return st('1&#65039;&#8419;', 'Toque no menu <b>⋮</b> (três pontos) no canto superior do Chrome')
                     + st('2&#65039;&#8419;', 'Toque em <b>Adicionar à tela inicial</b> ou <b>Instalar app</b>')
                     + st('3&#65039;&#8419;', 'Confirme tocando em <b>Instalar</b>');
            }
            return st('&#128187;', 'No Chrome ou Edge, clique no ícone <b>&#8853;</b> na barra de endereço para instalar')
                 + st('&#128241;', 'No celular use Chrome (Android) ou Safari (iPhone) e acesse este portal');
        }

        function openModal() {
            if (deferred) {
                deferred.prompt();
                deferred.userChoice.then(function () { deferred = null; });
                return;
            }
            document.getElementById('ppwa-steps').innerHTML = getSteps();
            ov.classList.add('open');
        }

        function closeModal() { ov.classList.remove('open'); }

        /* click funciona no desktop; touchend para iOS sem delay */
        function addTap(el, fn) {
            el.addEventListener('touchend', function (e) {
                e.preventDefault();
                fn();
            }, {passive: false});
            el.addEventListener('click', fn);
        }

        addTap(fab, openModal);
        addTap(document.getElementById('ppwa-close'), closeModal);
        ov.addEventListener('touchend', function (e) {
            if (e.target === ov) { e.preventDefault(); closeModal(); }
        }, {passive: false});
        ov.addEventListener('click', function (e) {
            if (e.target === ov) closeModal();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
</script>
"""


def inject_pwa() -> None:
    """Injeta suporte PWA: manifest, ícones Apple e botão flutuante 'Baixe o app'."""
    _ensure_icons()
    st.markdown(_JS, unsafe_allow_html=True)
