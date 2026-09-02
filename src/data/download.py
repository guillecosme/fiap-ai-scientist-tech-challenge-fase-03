"""Download das fontes com verificacao de integridade.

Uso:
    python -m src.data.download            # baixa tudo que ainda nao existe
    python -m src.data.download --force    # baixa de novo, mesmo que exista
    python -m src.data.download --group ibge

Regras:
- arquivos ja presentes nao sao baixados de novo, a menos que --force;
- zips sao extraidos em uma pasta com o mesmo nome, ao lado do arquivo;
- quando o zip traz um arquivo MD5 do Inep, o conteudo extraido e conferido com ele;
- o SHA-256 de cada download e gravado em data/manifest.json. Na primeira vez o
  manifesto e criado; nas seguintes, um hash diferente do registrado indica que a
  fonte mudou no servidor e o aviso fica no log, sem interromper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import requests

from src.data.sources import SOURCES, Source

MANIFEST = Path("data/manifest.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (tech-challenge-fase3)"}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def save_manifest(manifest: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fetch(url: str, dest: Path, retries: int = 6, timeout: int = 900) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=timeout) as resp:
                resp.raise_for_status()
                with tmp.open("wb") as f:
                    for chunk in resp.iter_content(chunk_size=1 << 20):
                        if chunk:
                            f.write(chunk)
            tmp.replace(dest)
            return
        except (requests.RequestException, OSError) as err:  # rede instavel do Inep
            last_error = err
            wait = 10 * attempt
            print(f"[download] tentativa {attempt}/{retries} falhou ({err}); aguardando {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Download falhou apos {retries} tentativas: {url}") from last_error


def extract_zip(path: Path) -> Path:
    out = path.with_suffix("")
    with zipfile.ZipFile(path) as z:
        z.extractall(out)
    return out


def check_inep_md5(extracted: Path) -> None:
    """Confere os arquivos extraidos com o MD5_*.txt que o Inep coloca no zip."""
    for md5_file in extracted.rglob("*.txt"):
        if not md5_file.name.lower().startswith("md5"):
            continue
        text = md5_file.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            m = re.match(r"\s*([0-9a-fA-F]{32})\s+\*?(.+?)\s*$", line)
            if not m:
                continue
            expected, name = m.group(1).lower(), Path(m.group(2).strip()).name
            candidates = list(extracted.rglob(name))
            if not candidates:
                continue
            actual = md5_of(candidates[0])
            status = "ok" if actual == expected else "DIVERGENTE"
            print(f"[md5] {name}: {status}")
            if status != "ok":
                raise RuntimeError(f"MD5 divergente para {name} em {extracted}")


def download_source(source: Source, manifest: dict, force: bool = False) -> None:
    if source.dest.exists() and not force:
        print(f"[skip] {source.name}: ja existe em {source.dest}")
        return
    print(f"[get ] {source.name}: {source.url}")
    fetch(source.url, source.dest)
    digest = sha256_of(source.dest)
    previous = manifest.get(source.name, {}).get("sha256")
    if previous and previous != digest:
        print(f"[aviso] {source.name}: hash diferente do manifesto (fonte atualizada?)")
    manifest[source.name] = {
        "url": source.url,
        "path": str(source.dest),
        "sha256": digest,
        "bytes": source.dest.stat().st_size,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if source.kind == "zip":
        extracted = extract_zip(source.dest)
        check_inep_md5(extracted)
    save_manifest(manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Baixa as fontes do projeto")
    parser.add_argument(
        "--group", help="baixa so um grupo (indicador, microdados, inse, censo, ideb, ibge)"
    )
    parser.add_argument(
        "--force", action="store_true", help="baixa de novo mesmo que o arquivo exista"
    )
    args = parser.parse_args()

    manifest = load_manifest()
    selected = [s for s in SOURCES if not args.group or s.group == args.group]
    for source in selected:
        download_source(source, manifest, force=args.force)
    print(f"[fim] {len(selected)} fontes verificadas; manifesto em {MANIFEST}")


if __name__ == "__main__":
    main()
