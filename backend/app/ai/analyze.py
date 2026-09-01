"""Analisis mendalam dokumen dengan Grok/DeepSeek."""
from app.ai.client import chat_json
from app.config import get_settings
from app.models import Regulation

settings = get_settings()

INDUSTRI = [
    "Manufaktur", "Petrokimia", "Logistik & Pelabuhan", "Ritel & E-commerce", "Perdagangan (Ekspor-Impor)",
    "Pertanian & Pangan", "Perkebunan", "Perikanan", "Energi & Minerba", "Kelistrikan",
    "Otomotif", "Elektronika & TIK", "Farmasi & Kesehatan", "Tembakau", "Perbankan & Keuangan",
    "Investasi & Kawasan Ekonomi", "Konstruksi & Infrastruktur", "BUMN", "UMKM", "Ketenagakerjaan",
    "Telekomunikasi", "Media & Digital", "Kimia", "Semen & Material", "Pupuk",
]

SYSTEM_PROMPT = """Kamu analis regulasi untuk tim public affairs / government relations di Indonesia.
Analisis dokumen peraturan perundang-undangan berikut dan hasilkan JSON dengan skema:

{
  "ringkas": "ringkasan substansi 3-5 kalimat dalam Bahasa Indonesia",
  "delta": ["perubahan penting yang diatur, tiap item 1 kalimat, maks 6 item"],
  "sektor_terdampak": ["industri yang terdampak, pilih dari daftar yang diberikan; maks 5"],
  "dampak": "high|med|low",
  "watch": "catatan tindak lanjut / hal yang perlu diperhatikan pelaku usaha, 2-3 kalimat",
  "kontak": "unit/satker kementerian yang paling relevan untuk dihubungi (jika bisa disimpulkan; jika tidak, kosongkan)"
}

Gunakan hanya informasi yang ada di dokumen. Bahasa Indonesia."""


async def analyze_reg(reg: Regulation, text: str, provider: str = "grok", model: str | None = None) -> dict:
    model = model or (settings.grok_model if provider == "grok" else settings.deepseek_model)
    payload = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Jenis: {reg.jenis} {reg.nomor}\nJudul: {reg.judul}\n\n"
                f"Daftar industri yang tersedia: {', '.join(INDUSTRI)}\n\n"
                "=== ISI DOKUMEN ===\n" + text[:60000]
            ),
        },
    ]
    result = await chat_json(provider, model, payload, max_tokens=5000)
    # validasi sektor agar tetap dari daftar
    sektor = result.get("sektor_terdampak", [])
    if isinstance(sektor, str):
        sektor = [sektor]
    result["sektor_terdampak"] = [s for s in sektor if s in INDUSTRI][:5]
    result["delta"] = (result.get("delta") or [])[:6]
    if result.get("dampak") not in ("high", "med", "low"):
        result["dampak"] = "med"
    return result
