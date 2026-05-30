from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
COMPOUNDS_PATH = BASE_DIR / "compounds.json"
SPECTRA_DIR = BASE_DIR / "spectra"

with open(COMPOUNDS_PATH, encoding="utf-8") as f:
    compounds = json.load(f)


@app.get("/")
def root():
    return {"message": "Organic Chemistry API"}


@app.get("/api/search")
def search(q: str):
    q = q.strip().lower()

    results = []

    for c in compounds:
        name_ja = c.get("name_ja", "").lower()
        name_en = c.get("name_en", "").lower()
        iupac_name = c.get("iupac_name", "").lower()
        cas = c.get("cas", "").lower()
        smiles = c.get("smiles", "").lower()

        if (
            q in name_ja
            or q in name_en
            or q in iupac_name
            or q in cas
            or q in smiles
        ):
            results.append(c)

    return results


@app.get("/api/compounds/{cas}/spectra/{spectrum_type}")
def get_spectrum(cas: str, spectrum_type: str):
    """
    例:
    /api/compounds/108-88-3/spectra/ei-ms
    /api/compounds/108-88-3/spectra/ir
    /api/compounds/108-88-3/spectra/h-nmr
    /api/compounds/108-88-3/spectra/c-nmr
    """

    allowed_types = ["ei-ms", "ir", "h-nmr", "c-nmr"]

    if spectrum_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid spectrum type"
        )

    safe_cas = cas.replace("/", "-")
    file_path = SPECTRA_DIR / safe_cas / f"{spectrum_type}.json"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Spectrum not found"
        )

    with open(file_path, encoding="utf-8") as f:
        return json.load(f)