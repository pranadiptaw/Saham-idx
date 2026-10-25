"""Modul indikator teknikal yang mengikuti rumus TradingView (Pine Script v5).

Aturan yang ditiru dari TradingView:
- SMA  : rata-rata biasa; kosong (NaN) sampai ada n data.
- EMA  : alpha = 2/(n+1). Nilai pertama = SMA n data pertama, lalu rekursif
         (sama seperti ta.ema). Ini BEDA dari pandas ewm() bawaan.
- RMA  : alpha = 1/n, nilai pertama = SMA (ta.rma). Dipakai oleh RSI dan ATR.
- RSI  : ta.rsi -> RMA dari kenaikan / RMA dari penurunan.
- ATR  : ta.atr -> RMA dari True Range (bar pertama: TR = high - low).
- ADR  : TradingView tidak punya ADR bawaan. Di sini disediakan dua versi:
         ADR nominal = SMA(high - low) dan ADR% = 100 * (SMA(high/low) - 1).

Pemakaian:
    from indikator import hitung_indikator, hitung_per_kode
    hasil = hitung_indikator(df)          # df: satu saham, urut tanggal
    hasil = hitung_per_kode(df_semua)     # df_semua: kolom kode, tanggal, ...
"""
import numpy as np
import pandas as pd

PERIODE_MA = (3, 5, 10, 20, 60, 100, 200)
PERIODE_RSI = (10, 14)
PERIODE_ATR = (14,)
PERIODE_ADR = (20,)
PERIODE_VOLUME = (10, 20)
PERIODE_PERUBAHAN = (5, 21, 63, 126, 252)   # 1 minggu, 1 bulan, 3 bln, 6 bln, 1 thn (hari bursa)


# ---------- Fungsi dasar (meniru Pine Script) ----------
def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def _ewm_seeded(s: pd.Series, n: int, alpha: float) -> pd.Series:
    """Rata-rata eksponensial dengan nilai awal = SMA n data valid pertama.

    Dipakai untuk EMA (alpha=2/(n+1)) dan RMA (alpha=1/n), persis cara Pine
    Script menghitung ta.ema dan ta.rma.
    """
    x = s.to_numpy(dtype=float)
    out = np.full(len(x), np.nan)
    valid = np.flatnonzero(~np.isnan(x))
    if len(valid) == 0:
        return pd.Series(out, index=s.index)
    f = valid[0]                       # indeks data valid pertama
    if len(x) - f < n or np.isnan(x[f:f + n]).any():
        return pd.Series(out, index=s.index)
    seg = x[f + n - 1:].copy()
    seg[0] = x[f:f + n].mean()         # nilai awal = SMA
    out[f + n - 1:] = pd.Series(seg).ewm(alpha=alpha, adjust=False).mean().to_numpy()
    return pd.Series(out, index=s.index)


def ema(s: pd.Series, n: int) -> pd.Series:
    return _ewm_seeded(s, n, 2.0 / (n + 1))


def rma(s: pd.Series, n: int) -> pd.Series:
    return _ewm_seeded(s, n, 1.0 / n)


def rsi(close: pd.Series, n: int) -> pd.Series:
    d = close.diff()
    naik = rma(d.clip(lower=0), n)
    turun = rma((-d).clip(lower=0), n)
    hasil = np.where(turun == 0, 100.0,
            np.where(naik == 0, 0.0, 100.0 - 100.0 / (1.0 + naik / turun)))
    hasil = pd.Series(hasil, index=close.index)
    return hasil.where(naik.notna() & turun.notna())


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    pc = close.shift()
    return pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)


def atr(high, low, close, n: int) -> pd.Series:
    return rma(true_range(high, low, close), n)


# ---------- Fungsi utama ----------
def hitung_indikator(df: pd.DataFrame) -> pd.DataFrame:
    """Tambahkan semua kolom indikator ke data SATU saham.

    df harus punya kolom: open, high, low, close, volume (huruf kecil).
    Kalau ada kolom 'tanggal', data diurutkan naik dulu.
    """
    d = df.sort_values("tanggal").reset_index(drop=True) if "tanggal" in df.columns else df.copy()
    c, h, l, v = d["close"], d["high"], d["low"], d["volume"].astype(float)
    kolom = {}

    # Perubahan harga
    kolom["perubahan"] = c.diff()
    kolom["perubahan_pct"] = c.pct_change() * 100
    for n in PERIODE_PERUBAHAN:
        kolom[f"perubahan_{n}h_pct"] = c.pct_change(n) * 100

    # MA: SMA dan EMA, plus posisi harga terhadap MA
    for n in PERIODE_MA:
        for nama, ma in (("sma", sma(c, n)), ("ema", ema(c, n))):
            kolom[f"{nama}_{n}"] = ma
            kolom[f"jarak_{nama}_{n}_pct"] = (c / ma - 1) * 100
            kolom[f"di_atas_{nama}_{n}"] = (c > ma).astype("boolean").mask(ma.isna())

    # RSI
    for n in PERIODE_RSI:
        kolom[f"rsi_{n}"] = rsi(c, n)

    # ATR
    for n in PERIODE_ATR:
        a = atr(h, l, c, n)
        kolom[f"atr_{n}"] = a
        kolom[f"atr_{n}_pct"] = a / c * 100

    # ADR (rata-rata rentang harian)
    for n in PERIODE_ADR:
        kolom[f"adr_{n}"] = sma(h - l, n)
        kolom[f"adr_{n}_pct"] = (sma(h / l, n) - 1) * 100

    # Volume
    kolom["nilai_transaksi"] = c * v
    kolom["perubahan_volume_pct"] = v.pct_change().replace([np.inf, -np.inf], np.nan) * 100
    for n in PERIODE_VOLUME:
        vs = sma(v, n)
        kolom[f"vol_sma_{n}"] = vs
        kolom[f"rasio_volume_{n}"] = v / vs.replace(0, np.nan)

    return pd.concat([d, pd.DataFrame(kolom, index=d.index)], axis=1)


def hitung_per_kode(df: pd.DataFrame) -> pd.DataFrame:
    """Sama seperti hitung_indikator, untuk tabel banyak saham (kolom 'kode')."""
    bagian = [hitung_indikator(g) for _, g in df.groupby("kode", sort=True)]
    return pd.concat(bagian, ignore_index=True) if bagian else df.copy()


def baris_terakhir(df: pd.DataFrame) -> pd.DataFrame:
    """Ambil satu baris terakhir per saham (untuk tabel screener).

    Dihitung per saham lalu langsung dipangkas ke baris terakhir, supaya
    memori tidak membengkak saat sahamnya banyak.
    """
    baris = [hitung_indikator(g).tail(1) for _, g in df.groupby("kode", sort=True)]
    if not baris:
        return df.iloc[0:0].copy()
    return pd.concat(baris, ignore_index=True).set_index("kode")
