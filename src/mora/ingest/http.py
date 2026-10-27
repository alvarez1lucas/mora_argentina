"""Sesión HTTP con reintentos, compartida por todos los módulos de ingesta.

Los certificados se validan contra el almacén del sistema operativo (truststore) en lugar
del bundle de certifi: así funciona detrás de antivirus o proxies que inspeccionan TLS
con una raíz propia instalada en el sistema, sin desactivar la verificación.
"""

from __future__ import annotations

import ssl
from functools import lru_cache
from pathlib import Path

import requests
import truststore
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from mora.config import settings


class _SystemTrustAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return super().init_poolmanager(*args, **kwargs)


@lru_cache(maxsize=1)
def session() -> requests.Session:
    cfg = settings()["http"]
    retry = Retry(
        total=cfg["retries"],
        backoff_factor=cfg["backoff"],
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    s = requests.Session()
    s.headers["User-Agent"] = cfg["user_agent"]
    s.mount("https://", _SystemTrustAdapter(max_retries=retry))
    return s


def get_json(url: str, params: dict | None = None) -> dict:
    r = session().get(url, params=params, timeout=settings()["http"]["timeout"])
    r.raise_for_status()
    return r.json()


def download(url: str, dest: Path) -> Path:
    """Baja `url` a `dest` en streaming. Falla si el servidor devuelve HTML en lugar del archivo."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with session().get(url, stream=True, timeout=settings()["http"]["timeout"]) as r:
        r.raise_for_status()
        if "text/html" in r.headers.get("Content-Type", ""):
            raise FileNotFoundError(f"El servidor devolvió HTML para {url}")
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    tmp.replace(dest)
    return dest
