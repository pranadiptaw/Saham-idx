"""Tarik data harian Yahoo Finance lalu upsert ke Supabase.

Pemakaian:
  python fetch_data.py daily      # 5 hari terakhir (jadwal harian, menimpa data siang)
  python fetch_data.py backfill   # 5 tahun riwayat (jalankan sekali di awal)
"""
import os
import sys
import time

import pandas as pd
import psycopg2
import yfinance as yf
from psycopg2.extras import execute_values

MODE = sys.argv[1] if len(sys.argv) > 1 else "daily"
PERIOD = "max" if MODE == "backfill" else "5d"
UKURAN = 25   # saham per kelompok
JEDA = 6      # detik antar kelompok

UPSERT = """
insert into harga_harian (kode, tanggal, open, high, low, close, volume)
values %s
on conflict (kode, tanggal) do update set
  open = excluded.open, high = excluded.high, low = excluded.low,
  close = excluded.close, volume = excluded.volume, diperbarui = now()
"""


def baca_kode():
    with open("tickers.txt") as f:
        return sorted({x.strip().upper().replace(".JK", "") for x in f if x.strip()})


def angka(v):
    return None if pd.isna(v) else float(v)


def ambil(batch):
    df = yf.download([k + ".JK" for k in batch], period=PERIOD, auto_adjust=False,
                     group_by="ticker", progress=False, threads=True)
    baris = []
    for k in batch:
        t = k + ".JK"
        try:
            d = df[t] if isinstance(df.columns, pd.MultiIndex) else df
        except KeyError:
            continue
        d = d.dropna(subset=["Close"])
        for tgl, r in d.iterrows():
            baris.append((k, tgl.date(), angka(r["Open"]), angka(r["High"]),
                          angka(r["Low"]), angka(r["Close"]),
                          None if pd.isna(r["Volume"]) else int(r["Volume"])))
    return baris


def main():
    kode = baca_kode()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    total, gagal = 0, []
    for i in range(0, len(kode), UKURAN):
        batch = kode[i:i + UKURAN]
        try:
            baris = ambil(batch)
        except Exception as e:
            print("Kelompok gagal:", batch[0], "...", e)
            gagal += batch
            continue
        ada = {b[0] for b in baris}
        gagal += [k for k in batch if k not in ada]
        if baris:
            with conn, conn.cursor() as cur:
                execute_values(cur, UPSERT, baris, page_size=1000)
            total += len(baris)
        time.sleep(JEDA)
    conn.close()
    print(f"Mode {MODE}: {total} baris di-upsert; {len(gagal)} kode tanpa data")
    if gagal:
        print("Tanpa data:", ", ".join(gagal[:50]), "..." if len(gagal) > 50 else "")
    if total == 0:
        sys.exit(1)  # supaya GitHub Actions menandai gagal


if __name__ == "__main__":
    main()
