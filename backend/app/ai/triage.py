"""Triase regulasi: klasifikasikan substantif vs internal organisasi.

Model dipilih dari AppConfig 'TRIAGE_PROVIDER'/'TRIAGE_MODEL', default grok.
"""
from app.ai.client import chat_json
from app.config import get_settings
from app.models import Regulation

settings = get_settings()

SYSTEM_PROMPT = """Kamu adalah analis hukum pemerintah Indonesia. Tugasmu menilai daftar peraturan
perundang-undangan yang baru terbit dan mengelompokkannya.

Kategori:
- "substantif": mengatur hak/kewajiban pelaku usaha, sektor industri, masyarakat, atau tata niaga
  (contoh: impor, ekspor, upah minimum, pupuk bersubsidi, TKDN, harga batubara, perizinan).
- "internal": organisasi internal pemerintah saja, tidak berdampak langsung ke pelaku usaha/masyarakat
  (contoh: tim koordinasi, struktur organisasi, SOP kementerian, panitia seleksi, honor tim).
- "ragu": tidak jelas; biar manusia yang memutuskan.

Untuk tiap peraturan berikan ringkasan 1 kalimat dan dampak yang mungkin (high/med/low) jika substantif.

Output JSON:
{"items":[{"id":<id_angka>,"label":"substantif|internal|ragu","ringkasan":"...","dampak":"high|med|low"}]}"""


async def triage_regs(regs: list[Regulation], provider: str = "grok", model: str | None = None) -> dict[int, dict]:
    if not regs:
        return {}
    # pastikan API key provider tersedia; kalau tidak, kembalikan kosong (bukan error)
    from app.ai.client import _key_for
    if not _key_for(provider):
        return {}
    model = model or (settings.grok_model if provider == "grok" else settings.deepseek_model)
    payload = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": "Daftar peraturan:\n"
            + "\n".join(
                f"[{r.id}] {r.jenis} {r.nomor} — {r.judul}" for r in regs
            ),
        },
    ]
    result = await chat_json(provider, model, payload, max_tokens=6000)
    out: dict[int, dict] = {}
    for it in result.get("items", []):
        try:
            rid = int(it.get("id"))
        except (TypeError, ValueError):
            continue
        out[rid] = {"label": it.get("label", "ragu"), "ringkasan": it.get("ringkasan", ""), "dampak": it.get("dampak", "med")}
    return out
