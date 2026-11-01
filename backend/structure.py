"""
構造式まわりの API (Phase 2: 構造式描画)

RDKit を使って以下を提供する:
- 描画: SMILES -> SVG / PNG（外部サービスに依存しない自前描画）
- 解析: SMILES / MolBlock -> 分子式・分子量・精密質量・InChIKey など + DB照合
- 立体異性体: 未指定の立体中心を列挙
- 3D配座: ETKDG で配座生成 + MMFF/UFF 最適化し、MolBlock(SDF) を返す（3Dmol.js 用）

注: これらは計算による生成データ。data としては化合物DBの実測値とは区別して扱うこと。
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(prefix="/api/structure", tags=["structure"])


def _mol_from_input(smiles: Optional[str] = None, molblock: Optional[str] = None):
    from rdkit import Chem

    mol = None
    if molblock:
        mol = Chem.MolFromMolBlock(molblock, sanitize=True, removeHs=False)
    if mol is None and smiles:
        mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise HTTPException(status_code=400, detail="Invalid structure input (SMILES / MolBlock を解釈できません)")
    return mol


def depict_svg(smiles: str, width: int = 420, height: int = 360) -> str:
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise HTTPException(status_code=400, detail="Invalid SMILES")
    Chem.rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    opts = drawer.drawOptions()
    opts.bondLineWidth = 2.2
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


def depict_png(smiles: str, width: int = 420, height: int = 360) -> bytes:
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise HTTPException(status_code=400, detail="Invalid SMILES")
    Chem.rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DCairo(width, height)
    opts = drawer.drawOptions()
    opts.bondLineWidth = 2.2
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


@router.get("/depict")
def depict(
    smiles: str = Query(..., min_length=1),
    format: str = Query("svg", pattern="^(svg|png)$"),
    width: int = Query(420, ge=80, le=1600),
    height: int = Query(360, ge=80, le=1600),
):
    if format == "png":
        return Response(content=depict_png(smiles, width, height), media_type="image/png")
    return Response(content=depict_svg(smiles, width, height), media_type="image/svg+xml")


class StructureIn(BaseModel):
    smiles: Optional[str] = None
    molblock: Optional[str] = None


class StereoIn(StructureIn):
    max_isomers: int = 32


@router.post("/analyze")
def analyze(body: StructureIn):
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors

    mol = _mol_from_input(body.smiles, body.molblock)
    result: dict[str, Any] = {
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "mw": round(Descriptors.MolWt(mol), 3),
        "exact_mass": round(Descriptors.ExactMolWt(mol), 5),
        "canonical_smiles": Chem.MolToSmiles(mol),
        "isomeric_smiles": Chem.MolToSmiles(mol, isomericSmiles=True),
        "inchi": Chem.MolToInchi(mol),
        "inchi_key": Chem.MolToInchiKey(mol),
        "num_atoms": mol.GetNumAtoms(),
        "db_match": None,
    }

    # DB照合: InChIKey が一致する化合物があれば基本情報を返す
    try:
        import db as dblayer

        con = dblayer.connect()
        try:
            row = con.execute(
                "SELECT name_ja, name_en, iupac_name, cas, formula, mw, tier FROM compounds WHERE inchi_key=?",
                (result["inchi_key"],),
            ).fetchone()
            if row:
                result["db_match"] = dict(row)
        finally:
            con.close()
    except Exception:
        pass
    return result


@router.post("/stereoisomers")
def stereoisomers(body: StereoIn):
    from rdkit import Chem
    from rdkit.Chem.EnumerateStereoisomers import EnumerateStereoisomers, StereoEnumerationOptions

    mol = _mol_from_input(body.smiles, body.molblock)
    max_isomers = max(1, min(body.max_isomers, 128))
    opts = StereoEnumerationOptions(tryEmbedding=False, maxIsomers=max_isomers)
    isomers = []
    for iso in EnumerateStereoisomers(mol, options=opts):
        smi = Chem.MolToSmiles(iso, isomericSmiles=True)
        isomers.append({"smiles": smi, "svg": depict_svg(smi, 260, 220)})
    return {"count": len(isomers), "isomers": isomers}


@router.post("/conformer")
def conformer(body: StructureIn):
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = _mol_from_input(body.smiles, body.molblock)
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    if AllChem.EmbedMolecule(mol, params) != 0:
        raise HTTPException(status_code=422, detail="3D配座の生成に失敗しました")
    energy = None
    if AllChem.MMFFHasAllMoleculeParams(mol):
        props = AllChem.MMFFGetMoleculeProperties(mol)
        ff = AllChem.MMFFGetMoleculeForceField(mol, props)
        ff.Minimize(maxIts=500)
        energy = round(ff.CalcEnergy(), 2)
    else:
        ff = AllChem.UFFGetMoleculeForceField(mol)
        ff.Minimize(maxIts=500)
        energy = round(ff.CalcEnergy(), 2)
    molblock = Chem.MolToMolBlock(mol)
    return {"molblock": molblock, "energy_kcal_mol": energy, "num_atoms": mol.GetNumAtoms()}
