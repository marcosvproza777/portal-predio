"""PWA support — ícones, manifest e botão 'Baixe o app'."""
import os
import streamlit as st

_BASE    = os.path.dirname(__file__)
_ICONS   = os.path.join(_BASE, "static", "icons")
_I192    = os.path.join(_ICONS, "icon-192.png")
_I512    = os.path.join(_ICONS, "icon-512.png")
_I180    = os.path.join(_ICONS, "icon-180.png")


def _ensure_icons() -> None:
    if all(os.path.exists(p) for p in (_I192, _I512, _I180)):
        return
    os.makedirs(_ICONS, exist_ok=True)
    logo = os.path.join(_BASE, "logo.jpg")
    if not os.path.exists(logo):
        return
    try:
        from PIL import Image
        img = Image.open(logo).convert("RGBA")
        w, h = img.size
        side = max(w, h)
        bg = Image.new("RGBA", (side, side), (8, 20, 43, 255))
        bg.paste(img, ((side - w) // 2, (side - h) // 2))
        for path, size in ((_I192, 192), (_I512, 512), (_I180, 180)):
            bg.resize((size, size), Image.LANCZOS).save(path, "PNG")
    except Exception:
        pass


def inject_pwa() -> None:
    """Chama uma vez por sessão: registra manifest, meta tags Apple e botão fixo."""
    _ensure_icons()

    st.markdown(
        "<link rel='manifest' href='/app/static/manifest.json'>"
        "<meta name='apple-mobile-web-app-capable' content='yes'>"
        "<meta name='apple-mobile-web-app-status-bar-style' content='black-translucent'>"
        "<meta name='apple-mobile-web-app-title' content='Pred.IO'>"
        "<link rel='apple-touch-icon' href='/app/static/icons/icon-180.png'>"
        "<meta name='theme-color' content='#1565C0'>",
        unsafe_allow_html=True,
    )

    st.markdown("""
<style>
#pwa-fab {
    position:fixed;top:14px;right:16px;z-index:99999;
    background:linear-gradient(135deg,#1565C0 0%,#2563EB 100%);
    color:#fff;border:none;border-radius:22px;
    padding:7px 15px 7px 12px;
    font-size:0.75rem;font-weight:700;cursor:pointer;
    display:flex;align-items:center;gap:5px;
    box-shadow:0 2px 14px rgba(21,101,192,0.5);
    font-family:sans-serif;white-space:nowrap;
    transition:transform .15s,box-shadow .15s;
}
#pwa-fab:hover{transform:translateY(-1px);box-shadow:0 4px 20px rgba(21,101,192,0.65);}
#pwa-overlay{
    display:none;position:fixed;inset:0;
    background:rgba(0,0,0,0.55);z-index:100000;
    align-items:flex-end;justify-content:center;
}
#pwa-overlay.open{display:flex;}
#pwa-modal{
    background:#fff;border-radius:20px 20px 0 0;
    padding:28px 24px 40px;max-width:480px;width:100%;
}
#pwa-modal h3{margin:0 0 6px;color:#0F1F3D;font-size:1.1rem;}
#pwa-modal p{margin:0 0 18px;color:#475569;font-size:.875rem;line-height:1.5;}
.pwa-step{display:flex;gap:12px;align-items:flex-start;margin-bottom:14px;}
.pwa-step-icon{font-size:1.3rem;flex-shrink:0;line-height:1;}
.pwa-step-text{font-size:.85rem;color:#334155;line-height:1.45;}
.pwa-step-text b{color:#0F1F3D;}
#pwa-close{
    margin-top:18px;width:100%;background:#0F1F3D;color:#fff;
    border:none;border-radius:10px;padding:12px;
    font-size:.9rem;font-weight:700;cursor:pointer;
}
</style>

<button id="pwa-fab" onclick="pwaBtnClick()">📲 Baixe o app</button>

<div id="pwa-overlay" onclick="pwaOverlayClick(event)">
  <div id="pwa-modal">
    <h3>📲 Instalar Pred.IO</h3>
    <p>Adicione o portal à tela inicial para acesso rápido, sem abrir o navegador toda vez.</p>
    <div id="pwa-steps"></div>
    <button id="pwa-close" onclick="closePwa()">Entendi</button>
  </div>
</div>

<script>
(function(){
  var deferred = null;

  window.addEventListener('beforeinstallprompt', function(e){
    e.preventDefault();
    deferred = e;
  });

  window.pwaBtnClick = function(){
    if(deferred){ deferred.prompt(); deferred.userChoice.then(function(){ deferred=null; }); return; }
    showPwa();
  };

  window.pwaOverlayClick = function(e){
    if(e.target===document.getElementById('pwa-overlay')) closePwa();
  };

  window.closePwa = function(){
    document.getElementById('pwa-overlay').classList.remove('open');
  };

  function steps(){
    var ua = navigator.userAgent;
    if(/iPad|iPhone|iPod/.test(ua)){
      return '<div class="pwa-step"><div class="pwa-step-icon">1️⃣</div><div class="pwa-step-text">Toque no ícone <b>Compartilhar</b> (quadrado com seta ↑) na barra do Safari</div></div>'
           + '<div class="pwa-step"><div class="pwa-step-icon">2️⃣</div><div class="pwa-step-text">Role e toque em <b>Adicionar à Tela de Início</b></div></div>'
           + '<div class="pwa-step"><div class="pwa-step-icon">3️⃣</div><div class="pwa-step-text">Toque em <b>Adicionar</b> no canto superior direito</div></div>';
    }
    if(/Android/.test(ua)){
      return '<div class="pwa-step"><div class="pwa-step-icon">1️⃣</div><div class="pwa-step-text">Toque no menu <b>⋮</b> (três pontos) no Chrome</div></div>'
           + '<div class="pwa-step"><div class="pwa-step-icon">2️⃣</div><div class="pwa-step-text">Toque em <b>Adicionar à tela inicial</b> ou <b>Instalar app</b></div></div>'
           + '<div class="pwa-step"><div class="pwa-step-icon">3️⃣</div><div class="pwa-step-text">Confirme tocando em <b>Instalar</b></div></div>';
    }
    return '<div class="pwa-step"><div class="pwa-step-icon">💻</div><div class="pwa-step-text">No Chrome/Edge, clique no ícone <b>⊕</b> na barra de endereço para instalar</div></div>'
         + '<div class="pwa-step"><div class="pwa-step-icon">📱</div><div class="pwa-step-text">No celular, use Chrome (Android) ou Safari (iPhone) e acesse este portal</div></div>';
  }

  function showPwa(){
    document.getElementById('pwa-steps').innerHTML = steps();
    document.getElementById('pwa-overlay').classList.add('open');
  }
})();
</script>
""", unsafe_allow_html=True)
