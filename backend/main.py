import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).parent
COMPOUNDS_PATH = BASE_DIR / "compounds.json"
SPECTRA_DIR = BASE_DIR / "spectra"

app = FastAPI(
    title="Organic Compound Spectra API",
    description="有機化合物の基本情報・構造式・スペクトル学習用API",
    version="1.0.0",
)

# 公開時は Cloudflare Pages のURLを allow_origins に追加する。
# 動作確認中は "*" でもよいが、公開後は絞る方が安全。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_compounds() -> list[dict[str, Any]]:
    if not COMPOUNDS_PATH.exists():
        return []

    with open(COMPOUNDS_PATH, encoding="utf-8") as f:
        return json.load(f)


def normalize_text(value: Any) -> str:
    return str(value or "").lower()


def compound_matches_query(compound: dict[str, Any], query: str) -> bool:
    q = query.lower().strip()

    if not q:
        return False

    searchable_fields = [
        compound.get("name_ja"),
        compound.get("name_en"),
        compound.get("iupac_name"),
        compound.get("cas"),
        compound.get("formula"),
        compound.get("smiles"),
        compound.get("category"),
    ]

    return any(q in normalize_text(field) for field in searchable_fields)


@app.get("/")
def root():
    return {
        "message": "Organic Compound Spectra API",
        "docs": "/docs",
        "compounds": "/api/compounds",
    }


@app.get("/api/health")
def health_check():
    compounds = load_compounds()

    return {
        "status": "ok",
        "compound_count": len(compounds),
    }


@app.get("/api/compounds")
def get_compounds():
    return load_compounds()


@app.get("/api/search")
def search_compounds(q: str = ""):
    compounds = load_compounds()

    if not q.strip():
        return []

    results = [
        compound
        for compound in compounds
        if compound_matches_query(compound, q)
    ]

    return results


@app.get("/api/compounds/{cas}/spectra/{spectrum_type}")
def get_spectrum(cas: str, spectrum_type: str):
    allowed_types = {
        "ir": "ir.json",
        "ei-ms": "ei-ms.json",
        "h-nmr": "h-nmr.json",
        "c-nmr": "c-nmr.json",
    }

    if spectrum_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported spectrum type")

    spectrum_path = SPECTRA_DIR / cas / allowed_types[spectrum_type]

    if not spectrum_path.exists():
        raise HTTPException(status_code=404, detail="Spectrum not found")

    with open(spectrum_path, encoding="utf-8") as f:
        return json.load(f)
