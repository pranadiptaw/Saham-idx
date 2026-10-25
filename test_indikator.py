import numpy as np, pandas as pd
from indikator import ema, rma, rsi, atr, sma, hitung_indikator, hitung_per_kode

# 1) RSI 14 contoh klasik Wilder (StockCharts ChartSchool)
harga = [44.34,44.09,44.15,43.61,44.33,44.83,45.10,45.42,45.84,46.08,45.89,
         46.03,45.61,46.28,46.28,46.00,46.03,46.41,46.22,45.64]
r = rsi(pd.Series(harga), 14)
print("RSI14:", [round(x, 2) for x in r.dropna()])

# 2) EMA/RMA vektor == rekursi Pine versi lambat
def pine_lambat(x, n, a):
    out = [np.nan]*len(x)
    for i in range(n-1, len(x)):
        out[i] = np.mean(x[:n]) if i == n-1 else a*x[i] + (1-a)*out[i-1]
    return np.array(out)
x = np.random.default_rng(1).normal(100, 5, 500).cumsum()
for n in (3, 10, 200):
    assert np.allclose(ema(pd.Series(x), n).to_numpy(), pine_lambat(x, n, 2/(n+1)), equal_nan=True)
    assert np.allclose(rma(pd.Series(x), n).to_numpy(), pine_lambat(x, n, 1/n), equal_nan=True)
print("EMA/RMA cocok dengan rekursi Pine")

# 3) Sifat dasar
assert (rsi(pd.Series(np.arange(1, 60.0)), 14).dropna() == 100).all()
assert (rsi(pd.Series(np.arange(60, 1, -1.0)), 14).dropna() == 0).all()
s = pd.Series(x); assert abs(ema(s, 20).iloc[19] - sma(s, 20).iloc[19]) < 1e-9
h = pd.Series([10, 12, 11, 13.0]); l = pd.Series([9, 10, 9.5, 11.0]); c = pd.Series([9.5, 11, 10, 12.0])
print("TR bar1-4:", list(pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)))

# 4) Kolom dan kecepatan
rng = np.random.default_rng(2)
n = 3000
cl = 5000 + rng.normal(0, 50, n).cumsum()
df = pd.DataFrame({"tanggal": pd.bdate_range("2012-01-02", periods=n), "open": cl, "high": cl*1.01,
                   "low": cl*0.99, "close": cl, "volume": rng.integers(1e5, 1e7, n)})
o = hitung_indikator(df)
print("jumlah kolom:", o.shape[1]); print(o.iloc[-1][["rsi_14","ema_20","atr_14","adr_20_pct","rasio_volume_20","di_atas_sma_200"]])
import time
besar = pd.concat([df.assign(kode=f"S{i:03d}") for i in range(200)])
t = time.time(); hitung_per_kode(besar); print("200 saham x 3000 baris:", round(time.time()-t, 1), "detik")
