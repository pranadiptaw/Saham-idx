-- Jalankan sekali di Supabase: SQL Editor > New query > paste > Run
create table if not exists harga_harian (
  kode        text             not null,
  tanggal     date             not null,
  open        double precision,
  high        double precision,
  low         double precision,
  close       double precision,
  volume      bigint,
  diperbarui  timestamptz      not null default now(),
  primary key (kode, tanggal)   -- kunci upsert: data sore menimpa data siang
);
create index if not exists idx_harga_tanggal on harga_harian (tanggal);
