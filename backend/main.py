import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

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

# 一覧応答（約11MB）などの大きなJSONを gzip 圧縮して転送量を削減する
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Phase 2: 構造式描画 API (RDKit)。rdkit 未導入の環境では検索APIだけでも動くよう任意登録にする。
try:
    from structure import router as structure_router

    app.include_router(structure_router)
except Exception as _e:  # pragma: no cover
    print(f"[warn] structure API disabled: {_e}")

# Phase 3: スペクトル解析 API (scipy / openpyxl)。未導入の環境では任意登録にする。
try:
    from analysis import router as analysis_router

    app.include_router(analysis_router)
except Exception as _e:  # pragma: no cover
    print(f"[warn] analysis API disabled: {_e}")


def _load_compounds_from_source() -> list[dict[str, Any]]:
    # Phase 1 (DB化): compounds.db があれば SQLite を正本にする。無ければ従来の JSON にフォールバック。
    db_path = BASE_DIR / "compounds.db"
    if db_path.exists():
        import db as dblayer

        con = dblayer.connect(db_path)
        try:
            return dblayer.load_compounds(con)
        finally:
            con.close()

    if not COMPOUNDS_PATH.exists():
        return []

    with open(COMPOUNDS_PATH, encoding="utf-8") as f:
        return json.load(f)


_compounds_cache: list[dict[str, Any]] | None = None
_compounds_list_cache: list[dict[str, Any]] | None = None


def load_compounds() -> list[dict[str, Any]]:
    # 化合物データはデプロイ時にしか変わらないため、初回読み込み後はメモリに保持する
    global _compounds_cache
    if _compounds_cache is None:
        _compounds_cache = _load_compounds_from_source()
    return _compounds_cache


def load_compounds_for_list() -> list[dict[str, Any]]:
    # 一覧表示用: synonyms（全体の約半分の容量）は検索API側でのみ使うため、一覧応答からは除いて軽量化する
    global _compounds_list_cache
    if _compounds_list_cache is None:
        _compounds_list_cache = [
            {k: v for k, v in compound.items() if k != "synonyms"}
            for compound in load_compounds()
        ]
    return _compounds_list_cache


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
        compound.get("inchi_key"),
        " ".join(compound.get("synonyms") or []),
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


_compounds_list_json: str | None = None


@app.get("/api/compounds")
def get_compounds():
    # 一覧は初回に JSON 文字列まで作って保持し、毎回のシリアライズを避ける
    global _compounds_list_json
    if _compounds_list_json is None:
        _compounds_list_json = json.dumps(load_compounds_for_list(), ensure_ascii=False)
    return Response(content=_compounds_list_json, media_type="application/json")


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

    # DB があれば先に引く（曲線データは圧縮してDBに格納済み）
    db_path = BASE_DIR / "compounds.db"
    if db_path.exists():
        import db as dblayer

        con = dblayer.connect(db_path)
        try:
            data = dblayer.get_spectrum_data(con, cas, spectrum_type.replace("-", "_"))
        finally:
            con.close()
        if data is not None:
            return data

    spectrum_path = SPECTRA_DIR / cas / allowed_types[spectrum_type]

    if not spectrum_path.exists():
        raise HTTPException(status_code=404, detail="Spectrum not found")

    with open(spectrum_path, encoding="utf-8") as f:
        return json.load(f)
