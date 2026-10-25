import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text

from screener_pro import tampilkan_screener_pro
from tab_indikator import tampilkan_tab_indikator

st.set_page_config(page_title="Dashboard Saham IDX", layout="wide")
st.title("Dashboard Saham IDX")


@st.cache_resource
def mesin():
    url = st.secrets["DATABASE_URL"]
    for awal in ("postgresql://", "postgres://"):
        if url.startswith(awal):
            url = "postgresql+psycopg2://" + url[len(awal):]
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=600, show_spinner=False)
def sql(q: str, params: tuple = ()) -> pd.DataFrame:
    with mesin().connect() as c:
        return pd.read_sql(text(q), c, params=dict(zip([f"p{i}" for i in range(len(params))], params)))


def hilangkan_celah(fig, tanggal):
    """Buang Sabtu, Minggu, dan hari libur (hari tanpa data) dari sumbu tanggal."""
    t = pd.to_datetime(pd.Series(tanggal).unique())
    if len(t) < 2:
        return
    kosong = pd.date_range(t.min(), t.max()).difference(t)
    fig.update_xaxes(rangebreaks=[dict(values=kosong.strftime("%Y-%m-%d").tolist())])


info = sql("select max(tanggal) as tgl, max(diperbarui) as upd, count(distinct kode) as n from harga_harian")
if info["tgl"].iloc[0] is None:
    st.warning("Database masih kosong. Jalankan backfill dulu.")
    st.stop()
st.caption(f"Data terakhir: {info['tgl'].iloc[0]} | {info['n'].iloc[0]} saham | "
           f"diperbarui {pd.to_datetime(info['upd'].iloc[0]).tz_convert('Asia/Jakarta'):%d %b %Y %H:%M} WIB")

kode_list = sql("select distinct kode from harga_harian order by kode")["kode"].tolist()
hari = st.sidebar.selectbox("Rentang", [30, 90, 180, 365, 730, 1825], index=3,
                            format_func=lambda x: f"{x} hari")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Grafik satu saham", "Bandingkan", "Screener", "Indikator", "Screener Pro"])

with tab1:
    k = st.selectbox("Saham", kode_list, index=kode_list.index("BBCA") if "BBCA" in kode_list else 0)
    c1, c2 = st.columns(2)
    ma_a = c1.number_input("MA pendek", 5, 100, 20)
    ma_b = c2.number_input("MA panjang", 10, 300, 50)
    df = sql("select * from harga_harian where kode = :p0 and tanggal >= current_date - :p1 order by tanggal",
             (k, hari))
    if df.empty:
        st.info("Tidak ada data.")
    else:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df["tanggal"], open=df["open"], high=df["high"], low=df["low"],
                                     close=df["close"], name=k), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["tanggal"], y=df["close"].rolling(ma_a).mean(), name=f"MA{ma_a}"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["tanggal"], y=df["close"].rolling(ma_b).mean(), name=f"MA{ma_b}"), row=1, col=1)
        fig.add_trace(go.Bar(x=df["tanggal"], y=df["volume"], name="Volume"), row=2, col=1)
        fig.update_layout(height=650, xaxis_rangeslider_visible=False, margin=dict(t=20, b=20))
        hilangkan_celah(fig, df["tanggal"])
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    pilih = st.multiselect("Saham", kode_list, default=[x for x in ["BBCA", "BBRI", "BMRI"] if x in kode_list])
    if pilih:
        df = sql("select kode, tanggal, close from harga_harian where kode = any(:p0) and tanggal >= current_date - :p1 order by tanggal",
                 (pilih, hari))
        fig = go.Figure()
        for kd, g in df.groupby("kode"):
            fig.add_trace(go.Scatter(x=g["tanggal"], y=g["close"] / g["close"].iloc[0] * 100, name=kd))
        fig.update_layout(height=550, yaxis_title="Indeks (awal = 100)", margin=dict(t=20))
        hilangkan_celah(fig, df["tanggal"])
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    df = sql("select kode, tanggal, close, volume from harga_harian where tanggal >= current_date - 120 order by kode, tanggal")
    baris = []
    for kd, g in df.groupby("kode"):
        c = g["close"].dropna()
        if len(c) < 22:
            continue
        baris.append({"Kode": kd, "Harga": c.iloc[-1],
                      "1 hari %": (c.iloc[-1] / c.iloc[-2] - 1) * 100,
                      "1 minggu %": (c.iloc[-1] / c.iloc[-6] - 1) * 100,
                      "1 bulan %": (c.iloc[-1] / c.iloc[-22] - 1) * 100,
                      "Volume": g["volume"].iloc[-1],
                      "Rata2 vol 20 hari": g["volume"].tail(20).mean()})
    if baris:
        hasil = pd.DataFrame(baris).set_index("Kode")
        urut = st.selectbox("Urutkan", list(hasil.columns), index=1)
        naik = st.checkbox("Urut naik", value=False)
        st.dataframe(hasil.sort_values(urut, ascending=naik).style.format("{:,.2f}"),
                     use_container_width=True, height=520)
    else:
        st.info("Belum cukup data untuk screener.")

with tab4:
    tampilkan_tab_indikator(sql, kode_list, hari)

with tab5:
    tampilkan_screener_pro(sql)
