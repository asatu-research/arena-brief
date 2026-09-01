# Arena Brief

Dashboard public affairs + admin untuk memonitor regulasi dari 9 JDIH kementerian,
dengan pipeline AI: crawl mingguan → triase judul → approve manual → download → parse → analisis
→ klasifikasi industri terdampak.

## Arsitektur

```
n8n (VPS) ──cron Jumat──► /api/crawl/run  ──►  crawl 9 situs JDIH
                                                     │  (Playwright untuk situs JS/Livewire)
                                                     ▼
                                              kandidat status=pending
                                                     │
Admin (/admin) ── approve ──►  download PDF → parse (Mistral OCR, fallback pypdf)
                                                     │        → analisis (Grok/DeepSeek)
                                                     ▼
                                              status=analyzed  →  dashboard (/)
```

- **Backend**: FastAPI + PostgreSQL (async SQLAlchemy). Satu file per adapter crawler di
  `backend/app/crawlers/`.
- **AI**: triase & analisis via Grok (xAI) atau DeepSeek; parsing dokumen via Mistral OCR
  (fallback pypdf jika API key Mistral kosong).
- **Admin**: `GET /admin` — login, approve/skip kandidat, kelola sumber & konfigurasi AI.
- **Dashboard**: `GET /` — read-only, membaca `/api/dashboard/regulations`.

## Struktur

```
backend/
  app/
    crawlers/        9 adapter JDIH (bkpm, kemenkeu, kemendag, kementan, kkp, kemenperin, esdm, kemnaker, kemkes)
    ai/              client LLM, triase, parse PDF, analisis
    services/        crawl_service, analysis_service
    routers/         auth, admin, dashboard, crawl
  static/
    admin/           halaman admin SPA
    dashboard/       dashboard read-only
n8n/                 workflow JSON: cron Jumat + notifikasi (opsional)
docker-compose.yml   backend (DB: pakai Supabase eksternal)
docker-compose.local.yml  opsi Postgres lokal di VPS
```

## Cara pakai

### 1. Local development

```bash
# PostgreSQL harus jalan, buat db arena
cd backend
copy .env.example .env        # isi ADMIN_PASSWORD, SECRET_KEY
pip install -r requirements.txt
python -m playwright install chromium
uvicorn app.main:app --reload
```

Buka:
- Dashboard: http://localhost:8000/
- Admin:    http://localhost:8000/admin

### 2. Deploy VPS (Docker) — database pakai Supabase

> Supabase = Postgres terkelola di cloud. VPS tidak perlu menjalankan Postgres,
> beban VPS lebih ringan dan data tercadangkan otomatis. Cara ini direkomendasikan.

1. Buat project gratis di [supabase.com](https://supabase.com) → **Settings → Database → Connection string**.
2. Salin `DATABASE_URL` (mode **transaction pooler**, port 6543):

   ```
   postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```

   Backend otomatis mengenali host `supabase.com` → menyalakan SSL dan mematikan
   prepared statements (syarat pooler Supabase). Tidak perlu ubah kode.

3. Set env & deploy:

   ```bash
   git clone <repo> arena-brief && cd arena-brief
   export DATABASE_URL="postgresql+asyncpg://postgres.<ref>:...@...pooler.supabase.com:6543/postgres"
   export ADMIN_USERNAME=admin ADMIN_PASSWORD=... SECRET_KEY=... GROK_API_KEY=...
   docker compose up -d --build
   ```

   Skema tabel dibuat otomatis saat pertama kali backend start.

**Alternatif Postgres lokal** (tidak pakai Supabase):

```bash
export DATABASE_URL="postgresql+asyncpg://arena:arena_secret@localhost:5432/arena"
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

- Import workflow n8n (`n8n/crawl_friday.json`) ke instance n8n di VPS, atur
  `BACKEND_HOST` ke IP/internal host, dan aktifkan. Workflow kedua (`notif_friday.json`)
  opsional untuk notifikasi Telegram.

### 3. Flow kerja mingguan

1. Jumat 08:00 — n8n memanggil `/api/crawl/run`. Semua sumber aktif di-crawl,
   regulasi baru masuk status `pending`.
2. Kamu buka `/admin` → tab **Kandidat**. AI sudah memberi label
   (`substantif` / `internal` / `ragu`) + ringkasan + dampak. Kamu **Analisis & Approve**
   atau **Skip**.
3. Approve → backend download PDF, parse (Mistral OCR atau pypdf), analisis Grok →
   hasil (ringkas, delta, industri terdampak, dampak, catatan tindak lanjut) tersimpan.
4. Dashboard `/` langsung menampilkan regulasi yang sudah dianalisis.

## Konfigurasi AI

Dari `/admin` → tab **Konfigurasi** (tersimpan di DB, masked untuk secret).
Nilai yang diisi di UI langsung aktif tanpa restart (disinkronkan ke runtime saat disimpan):

| Key | Default | Keterangan |
|---|---|---|
| `GROK_API_KEY` | (kosong) | Analisis + triase utama |
| `MISTRAL_API_KEY` | (kosong) | Parsing PDF/OCR — **isi sendiri** |
| `DEEPSEEK_API_KEY` | (kosong) | Alternatif analisis |
| `TRIAGE_PROVIDER` | `grok` | Provider triase (grok / deepseek) |
| `ANALYSIS_PROVIDER` | `grok` | Provider analisis (grok / deepseek) |
| `TRIAGE_MODEL` / `ANALYSIS_MODEL` | (pakai default env) | Model |

> Catatan: tanpa `MISTRAL_API_KEY`, parsing memakai pypdf (hanya PDF berbasis teks).
> PDF hasil scan butuh Mistral OCR.

## Sumber JDIH yang didukung

`bkpm`, `kemenkeu`, `kemendag`, `kementan`, `kkp`, `kemenperin`, `esdm`, `kemnaker`, `kemkes`.
URL listing tiap sumber bisa diedit dari `/admin` → tab **Sumber** (termasuk filter tahun/jenis).

## Batasan & catatan teknis

- Semua situs tidak punya API resmi → pakai adapter scraping. Struktur DOM bisa berubah;
  adapter per situs memudahkan perbaikan terpisah.
- Kementan memakai Bearer token yang di-hardcode di bundle frontend-nya; bisa berubah saat
  redeploy, fallback ke Playwright.
- Kemenkes (Livewire) butuh Playwright untuk pagination; tanpa browser hanya halaman pertama.
- `verify=False` pada HTTP untuk beberapa situs yang sertifikatnya bermasalah (lintas admin/prod).
- **Supabase free tier**: project bisa otomatis *pause* setelah ±1 minggu tanpa aktivitas.
  Pakai cron Jumat (n8n) sebagai aktivitas rutin, atau aktifkan kembali manual dari dashboard
  Supabase jika koneksi gagal setelah lama tidak dipakai.
- **Supabase pooler (port 6543)**: backend otomatis menonaktifkan prepared statements &
  menyalakan SSL saat host berakhiran `supabase.com`. Untuk Postgres lokal (non-pooler) tidak perlu.
- Keamanan: login admin memakai cookie sesi bertanda (`itsdangerous`). Untuk produksi HTTPS,
  pasang reverse proxy (Caddy/Nginx) di depan container backend.
