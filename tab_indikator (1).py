"""Isi tab "Indikator" untuk dashboard (dipanggil dari app.py)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from indikator import baris_terakhir, hitung_indikator


@st.cache_data(ttl=3600, show_spinner="Menghitung indikator semua saham...")
def tabel_indikator(_sql):
    d = _sql("select kode, tanggal, open, high, low, close, volume from harga_harian "
             "where tanggal >= current_date - 1200 order by kode, tanggal")
    return baris_terakhir(d)


def posisi(v):
    return "-" if pd.isna(v) else ("Di atas" if v else "Di bawah")


def tampilkan_tab_indikator(sql, kode_list, hari):
    st.subheader("Indikator satu saham")
    k4 = st.selectbox("Saham", kode_list, key="ind_saham")
    df4 = sql("select * from harga_harian where kode = :p0 order by tanggal", (k4,))
    if df4.empty:
        st.info("Tidak ada data.")
    else:
        ind = hitung_indikator(df4)
        t = ind.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Harga", f"{t['close']:,.0f}", f"{t['perubahan_pct']:.2f}%")
        c2.metric("RSI 14", f"{t['rsi_14']:.1f}")
        c3.metric("ATR 14", f"{t['atr_14']:,.1f}", f"{t['atr_14_pct']:.2f}% dari harga", delta_color="off")
        c4.metric("Rasio volume (vs rata2 20 hari)", f"{t['rasio_volume_20']:.2f}x")

        baris = []
        for n in (3, 5, 10, 20, 60, 100, 200):
            baris.append({"MA": n,
                          "SMA": t[f"sma_{n}"], "Jarak SMA %": t[f"jarak_sma_{n}_pct"],
                          "Posisi vs SMA": posisi(t[f"di_atas_sma_{n}"]),
                          "EMA": t[f"ema_{n}"], "Jarak EMA %": t[f"jarak_ema_{n}_pct"],
                          "Posisi vs EMA": posisi(t[f"di_atas_ema_{n}"])})
        st.dataframe(pd.DataFrame(baris).set_index("MA").round(2), use_container_width=True)
        st.caption(f"ADR 20 hari: {t['adr_20']:,.1f} ({t['adr_20_pct']:.2f}%) | "
                   f"RSI 10: {t['rsi_10']:.1f} | Nilai transaksi: {t['nilai_transaksi']:,.0f}")

        tgl = pd.to_datetime(ind["tanggal"])
        rs = ind[tgl >= tgl.max() - pd.Timedelta(days=int(hari))]
        fig = go.Figure()
        for n in (10, 14):
            fig.add_trace(go.Scatter(x=rs["tanggal"], y=rs[f"rsi_{n}"], name=f"RSI {n}"))
        fig.add_hline(y=70, line_dash="dot")
        fig.add_hline(y=30, line_dash="dot")
        fig.update_layout(height=300, yaxis_range=[0, 100], margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Screener indikator (semua saham)")
    hasil = tabel_indikator(sql)
    if hasil.empty:
        st.info("Belum ada data.")
    else:
        f1, f2, f3 = st.columns(3)
        rsi_min, rsi_max = f1.slider("RSI 14", 0, 100, (0, 100))
        pilih_ma = f2.multiselect("Harga di atas", [f"{j} {n}" for j in ("SMA", "EMA") for n in (20, 60, 200)])
        vol_min = f3.number_input("Rasio volume minimal", 0.0, 50.0, 0.0, 0.5)

        m = pd.Series(True, index=hasil.index)
        if (rsi_min, rsi_max) != (0, 100):
            m &= hasil["rsi_14"].between(rsi_min, rsi_max)
        for label in pilih_ma:
            jenis, n = label.split()
            m &= hasil[f"di_atas_{jenis.lower()}_{n}"].fillna(False).astype(bool)
        if vol_min > 0:
            m &= hasil["rasio_volume_20"].fillna(0) >= vol_min

        tampil = hasil.loc[m, ["close", "perubahan_pct", "rsi_10", "rsi_14", "atr_14_pct", "adr_20_pct",
                               "rasio_volume_20", "jarak_sma_20_pct", "jarak_sma_200_pct",
                               "jarak_ema_20_pct", "jarak_ema_200_pct"]]
        tampil.columns = ["Harga", "Ubah %", "RSI 10", "RSI 14", "ATR %", "ADR %", "Rasio vol",
                          "Jarak SMA20 %", "Jarak SMA200 %", "Jarak EMA20 %", "Jarak EMA200 %"]
        st.write(f"{len(tampil)} saham memenuhi syarat")
        st.dataframe(tampil.sort_values("RSI 14").round(2), use_container_width=True, height=500)
