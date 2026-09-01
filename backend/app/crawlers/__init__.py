"""Registry adapter crawler."""
from app.crawlers.base import BaseAdapter
from app.crawlers.bkpm import BkpmAdapter
from app.crawlers.kemendag import KemendagAdapter
from app.crawlers.kemenkeu import KemenkeuAdapter
from app.crawlers.kemkes import KemkesAdapter
from app.crawlers.kemnaker import KemnakerAdapter
from app.crawlers.kementan import KementanAdapter
from app.crawlers.kemenperin import EsdmAdapter, KemenperinAdapter
from app.crawlers.kkp import KkpAdapter

ADAPTERS: dict[str, type[BaseAdapter]] = {
    "bkpm": BkpmAdapter,
    "kemenkeu": KemenkeuAdapter,
    "kemendag": KemendagAdapter,
    "kementan": KementanAdapter,
    "kkp": KkpAdapter,
    "kemenperin": KemenperinAdapter,
    "esdm": EsdmAdapter,
    "kemnaker": KemnakerAdapter,
    "kemkes": KemkesAdapter,
}


def get_adapter(key: str) -> type[BaseAdapter] | None:
    return ADAPTERS.get(key)
