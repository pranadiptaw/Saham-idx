"""Chart TradingView asli (widget gratis) untuk saham IDX.

Catatan: data chart ini berasal dari TradingView, bukan dari database sendiri.
"""
import json
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components


def _tema() -> str:
    try:
        t = st.context.theme.type
        if t in ("light", "dark"):
            return t
    except Exception:
        pass
    return "light" if st.get_option("theme.base") == "light" else "dark"


def tampilkan_tv(kode: str, tinggi: int = 650, interval: str = "D", kunci: str = "tv"):
    """Tampilkan chart TradingView untuk satu kode saham IDX (contoh: BBCA)."""
    cfg = {
        "width": "100%", "height": tinggi,
        "symbol": f"IDX:{kode}", "interval": interval, "timezone": "Asia/Jakarta",
        "theme": _tema(), "style": "1", "locale": "id",
        "enable_publishing": False, "allow_symbol_change": True,
        "hide_side_toolbar": False, "withdateranges": True, "save_image": False,
        "studies": ["RSI@tv-basicstudies"], "container_id": f"tv_{kunci}",
    }
    components.html(
        f'<div id="tv_{kunci}" style="height:{tinggi}px;width:100%"></div>'
        '<script src="https://s3.tradingview.com/tv.js"></script>'
        f"<script>new TradingView.widget({json.dumps(cfg)});</script>",
        height=tinggi + 10,
    )
    st.link_button(f"Buka {kode} di TradingView", f"https://www.tradingview.com/chart/?symbol={quote('IDX:' + kode)}")
    st.caption("Data chart dari TradingView (bukan dari databasemu), jadi bisa berbeda tipis dari angka di tabel. "
               "Kalau chart kosong atau simbol tidak tersedia, pakai tombol di atas.")
