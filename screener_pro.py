"""Tab "Screener Pro": filter bergaya TradingView dengan PERIODE BEBAS.

Tiap syarat filter = Indikator + Periode (angka bebas) + Operator + Nilai.
Contoh: RSI periode 10 > 45, ATR % periode 14 > 3, Jarak ke SMA % periode 200 > 0.

Dipanggil dari app.py:
    from screener_pro import tampilkan_screener_pro
    with tab5:
        tampilkan_screener_pro(sql)
"""
import operator

import numpy as np
import pandas as pd
import streamlit as st

from indikator import atr, ema, rsi, sma

# Indikator: nama -> periode bawaan (None = tidak butuh periode)
JENIS = {
    "Harga": None, "Volume": None, "Nilai transaksi": None,
    "Volume relatif": 10, "Perubahan %": 5, "RSI": 14,
    "ATR %": 14, "ATR (nominal)": 14, "ADR %": 20, "ADR (nominal)": 20,
    "Jarak ke SMA %": 20, "Jarak ke EMA %": 20, "SMA": 20, "EMA": 20,
    "Harga di atas SMA": 20, "Harga di bawah SMA": 20, "Harga di atas EMA": 20, "Harga di bawah EMA": 20,
}
# Posisi harga terhadap MA: nama -> (jenis MA, arah). Nilai = jarak minimal dalam % (0 = cukup di atas/bawah)
POSISI = {
    "Harga di atas SMA": ("SMA", 1), "Harga di bawah SMA": ("SMA", -1),
    "Harga di atas EMA": ("EMA", 1), "Harga di bawah EMA": ("EMA", -1),
}
FORMAT_JENIS = {
    "Harga": "a0", "Volume": "ringkas", "Nilai transaksi": "ringkas", "Volume relatif": "a2",
    "Perubahan %": "pct", "RSI": "a1", "ATR %": "a2", "ATR (nominal)": "a1", "ADR %": "a2",
    "ADR (nominal)": "a1", "Jarak ke SMA %": "pct", "Jarak ke EMA %": "pct", "SMA": "a0", "EMA": "a0",
}
OPERATOR = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le}
PERIODE_UBAH = {"1 hari": 1, "1 minggu": 5, "1 bulan": 21, "3 bulan": 63, "6 bulan": 126, "1 tahun": 252}
MAKS_PERIODE = 300

# Syarat awal: sama dengan filter di screenshot TradingView
SYARAT_AWAL = pd.DataFrame([
    {"Indikator": "Harga", "Periode": None, "Operator": ">", "Nilai": 70.0},
    {"Indikator": "Volume", "Periode": None, "Operator": ">", "Nilai": 7_000_000.0},
    {"Indikator": "ATR %", "Periode": 14.0, "Operator": ">", "Nilai": 3.0},
    {"Indikator": "ADR %", "Periode": 20.0, "Operator": ">", "Nilai": 3.0},
    {"Indikator": "RSI", "Periode": 14.0, "Operator": ">", "Nilai": 45.0},
    {"Indikator": "Harga di atas SMA", "Periode": 200.0, "Operator": None, "Nilai": 0.0},
    {"Indikator": "Harga di atas SMA", "Periode": 20.0, "Operator": None, "Nilai": 0.0},
])


# ---------- Perhitungan ----------
def nilai_terakhir(g: pd.DataFrame, jenis: str, n):
    """Nilai indikator pada bar terakhir untuk SATU saham (g: kolom high, low, close, volume)."""
    c, h, l, v = g["close"], g["high"], g["low"], g["volume"]
    ada = len(c)
    if jenis == "Harga":
        return c.iloc[-1]
    if jenis == "Volume":
        return v.iloc[-1]
    if jenis == "Nilai transaksi":
        return c.iloc[-1] * v.iloc[-1]
    if jenis == "Volume relatif":
        rata = v.tail(n).mean()
        return v.iloc[-1] / rata if ada >= n and rata > 0 else np.nan
    if jenis == "Perubahan %":
        return (c.iloc[-1] / c.iloc[-1 - n] - 1) * 100 if ada > n else np.nan
    if jenis == "RSI":
        return rsi(c, n).iloc[-1]
    if jenis == "ATR %":
        return atr(h, l, c, n).iloc[-1] / c.iloc[-1] * 100
    if jenis == "ATR (nominal)":
        return atr(h, l, c, n).iloc[-1]
    if jenis == "ADR %":
        return (sma(h / l, n).iloc[-1] - 1) * 100
    if jenis == "ADR (nominal)":
        return sma(h - l, n).iloc[-1]
    ma = (sma(c, n) if "SMA" in jenis else ema(c, n)).iloc[-1]
    return (c.iloc[-1] / ma - 1) * 100 if jenis.startswith("Jarak") else ma


@st.cache_resource(ttl=3600, show_spinner="Memuat data semua saham...")
def muat_grup(_sql):
    d = _sql("select kode, tanggal, high, low, close, volume from harga_harian "
             "where tanggal >= current_date - 1200 order by kode, tanggal")
    d = d.dropna(subset=["close"])
    grup = {k: g[["high", "low", "close", "volume"]].astype(float).reset_index(drop=True)
            for k, g in d.groupby("kode", sort=True)}
    return grup, (str(d["tanggal"].max()) if len(d) else "-"), len(d)


@st.cache_data(ttl=3600, show_spinner=False)
def hitung_kolom(_grup, versi, jenis, n):
    """Nilai satu indikator untuk semua saham. 'versi' hanya penanda agar cache ikut berganti saat data baru."""
    hasil = {}
    for k, g in _grup.items():
        try:
            hasil[k] = nilai_terakhir(g, jenis, n)
        except Exception:
            hasil[k] = np.nan
    return pd.Series(hasil, dtype=float).replace([np.inf, -np.inf], np.nan)


def periode_efektif(jenis, n):
    bawaan = JENIS[jenis]
    if bawaan is None:
        return None
    if n is None or pd.isna(n) or n < 1:
        return bawaan
    return int(min(n, MAKS_PERIODE))


def label(jenis, n):
    return jenis if n is None else f"{jenis} ({n})"


def saring(grup, versi, syarat):
    """Mask saham yang memenuhi SEMUA syarat, plus kolom nilai tiap syarat untuk ditampilkan."""
    m = pd.Series(True, index=pd.Index(list(grup)))
    kolom = {}
    for _, r in syarat.iterrows():
        jenis = r.get("Indikator")
        if jenis not in JENIS:
            continue
        n = periode_efektif(jenis, r.get("Periode"))
        if jenis in POSISI:                      # harga di atas / di bawah MA
            dasar, arah = POSISI[jenis]
            s = hitung_kolom(grup, versi, f"Jarak ke {dasar} %", n)
            batas = 0.0 if pd.isna(r.get("Nilai")) else float(r["Nilai"])
            m &= (s > batas) if arah > 0 else (s < -batas)
            kolom[label(f"Jarak ke {dasar} %", n)] = (s, "pct")
            continue
        if r.get("Operator") not in OPERATOR or pd.isna(r.get("Nilai")):
            continue
        s = hitung_kolom(grup, versi, jenis, n)
        m &= OPERATOR[r["Operator"]](s, float(r["Nilai"]))
        kolom[label(jenis, n)] = (s, FORMAT_JENIS[jenis])
    return m, kolom


# ---------- Tampilan ----------
def ringkas(v):
    if pd.isna(v):
        return "—"
    for batas, s in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(v) >= batas:
            return f"{v / batas:,.2f} {s}"
    return f"{v:,.0f}"


FORMAT = {"a0": "{:,.0f}", "a1": "{:,.1f}", "a2": "{:,.2f}", "pct": "{:+,.2f}%", "ringkas": ringkas}


def warna(v):
    if pd.isna(v) or v == 0:
        return ""
    return "color: #089981" if v > 0 else "color: #f23645"


def tampilkan_screener_pro(sql):
    grup, versi, baris = muat_grup(sql)
    if not grup:
        st.info("Belum ada data.")
        return
    st.caption(f"Data per {versi} | {len(grup)} saham | sumber: Yahoo Finance")

    with st.expander("Filter: pilih indikator, isi periode bebas, operator, dan nilai", expanded=True):
        syarat = st.data_editor(
            SYARAT_AWAL, num_rows="dynamic", hide_index=True, use_container_width=True, key="syarat_pro",
            column_config={
                "Indikator": st.column_config.SelectboxColumn(options=list(JENIS), required=True, width="medium"),
                "Periode": st.column_config.NumberColumn(min_value=1, max_value=MAKS_PERIODE, step=1, format="%d",
                                                         help="Jumlah bar (hari bursa). Kosongkan untuk periode bawaan."),
                "Operator": st.column_config.SelectboxColumn(options=list(OPERATOR),
                                                             help="Tidak dipakai untuk 'Harga di atas/bawah SMA/EMA'."),
                "Nilai": st.column_config.NumberColumn(format="%.2f",
                                                       help="Untuk 'Harga di atas/bawah SMA/EMA': jarak minimal dalam % "
                                                            "(0 = cukup di atas/bawah)."),
            })
        st.caption("Contoh: RSI periode 10 lebih dari 45. 'Harga di atas SMA' periode 200 nilai 0 = harga di atas SMA 200; "
                   "nilai 5 = minimal 5% di atas. 'Harga di bawah SMA' kebalikannya (operator tidak dipakai). "
                   "ATR % dan ADR % adalah persen dari harga. "
                   "Tambah baris dengan tanda + di bawah tabel; hapus dengan memilih baris lalu tekan Delete.")

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    tampilan = c1.radio("Tampilan", ["Kustom", "Kinerja"], horizontal=True)
    ubah = c2.selectbox("Periode perubahan", list(PERIODE_UBAH), index=1)
    cari = c3.text_input("Cari kode").strip().upper()
    arah = c4.radio("Urutan", ["Menurun", "Menaik"], horizontal=True)

    with st.spinner("Menghitung indikator..."):
        m, kolom_syarat = saring(grup, versi, syarat)
        if cari:
            m &= m.index.str.contains(cari, regex=False)

        if tampilan == "Kinerja":
            kolom = {"Harga": (hitung_kolom(grup, versi, "Harga", None), "a0")}
            for nama, n in PERIODE_UBAH.items():
                kolom[nama] = (hitung_kolom(grup, versi, "Perubahan %", n), "pct")
        else:
            kolom = {
                "Harga": (hitung_kolom(grup, versi, "Harga", None), "a0"),
                f"Ubah % ({ubah})": (hitung_kolom(grup, versi, "Perubahan %", PERIODE_UBAH[ubah]), "pct"),
                "Vol": (hitung_kolom(grup, versi, "Volume", None), "ringkas"),
                "Vol relatif (10)": (hitung_kolom(grup, versi, "Volume relatif", 10), "a2"),
                "Nilai transaksi": (hitung_kolom(grup, versi, "Nilai transaksi", None), "ringkas"),
            }
            for nama, isi in kolom_syarat.items():     # kolom dari syarat filter
                if nama not in kolom and nama not in ("Harga", "Volume", "Nilai transaksi"):
                    kolom[nama] = isi

    tabel = pd.DataFrame({j: s[m] for j, (s, _) in kolom.items()})
    tabel.index.name = "Simbol"
    if tabel.empty:
        st.write(f"**0** dari {len(grup)} saham memenuhi syarat")
        return
    urut = st.selectbox("Urutkan berdasarkan", list(tabel.columns), index=1 if len(tabel.columns) > 1 else 0)
    tabel = tabel.sort_values(urut, ascending=(arah == "Menaik"), na_position="last")

    st.write(f"**{len(tabel)}** dari {len(grup)} saham memenuhi syarat")
    gaya = tabel.style.format({j: FORMAT[f] for j, (_, f) in kolom.items()}, na_rep="—")
    pct = [j for j, (_, f) in kolom.items() if f == "pct"]
    if pct:
        gaya = gaya.map(warna, subset=pct)
    st.dataframe(gaya, use_container_width=True, height=620)
