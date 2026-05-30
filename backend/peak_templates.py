def detect_groups(smiles: str):
    groups = []
    s = smiles or ""

    if "c1" in s or "C1=CC=CC=C1" in s:
        groups.append("aromatic")

    if "C(=O)O" in s or "O=C(O)" in s:
        groups.append("carboxylic_acid")

    if "C(=O)O" in s and ("OC" in s or "OCC" in s):
        groups.append("ester")

    if "C(=O)" in s or "O=C" in s:
        groups.append("carbonyl")

    if "N" in s:
        groups.append("nitrogen")

    if "O" in s:
        groups.append("oxygenated")

    if "#" in s and "N" in s:
        groups.append("nitrile")

    if "Cl" in s or "Br" in s or "I" in s:
        groups.append("halogenated")

    return list(dict.fromkeys(groups))


def generate_ir(smiles: str):
    groups = detect_groups(smiles)
    peaks = []

    peaks.append({"wavenumber": "2950 cm⁻¹", "assignment": "C-H 伸縮"})

    if "aromatic" in groups:
        peaks.append({"wavenumber": "3030 cm⁻¹", "assignment": "芳香族 C-H 伸縮"})
        peaks.append({"wavenumber": "1600 cm⁻¹", "assignment": "芳香環 C=C 伸縮"})
        peaks.append({"wavenumber": "750 cm⁻¹", "assignment": "芳香族 C-H 面外変角"})

    if "ester" in groups:
        peaks.append({"wavenumber": "1740 cm⁻¹", "assignment": "エステル C=O 伸縮"})
        peaks.append({"wavenumber": "1240 cm⁻¹", "assignment": "エステル C-O 伸縮"})
    elif "carboxylic_acid" in groups:
        peaks.append({"wavenumber": "2500-3300 cm⁻¹", "assignment": "カルボン酸 O-H 伸縮"})
        peaks.append({"wavenumber": "1710 cm⁻¹", "assignment": "カルボン酸 C=O 伸縮"})
    elif "carbonyl" in groups:
        peaks.append({"wavenumber": "1715 cm⁻¹", "assignment": "C=O 伸縮"})

    if "oxygenated" in groups:
        peaks.append({"wavenumber": "1050 cm⁻¹", "assignment": "C-O 伸縮"})

    if "nitrogen" in groups:
        peaks.append({"wavenumber": "3300-3500 cm⁻¹", "assignment": "N-H または N含有官能基"})

    if "nitrile" in groups:
        peaks.append({"wavenumber": "2250 cm⁻¹", "assignment": "C≡N 伸縮"})

    if "halogenated" in groups:
        peaks.append({"wavenumber": "700 cm⁻¹", "assignment": "C-X 伸縮"})

    return peaks


def generate_ms(mw, smiles: str):
    s = smiles or ""
    mw_int = int(round(float(mw))) if mw else 100

    peaks = [
        {"mz": mw_int, "intensity": 30, "assignment": "分子イオン M⁺"},
        {"mz": 29, "intensity": 35, "assignment": "小フラグメント"},
        {"mz": 43, "intensity": 60, "assignment": "汎用フラグメント"}
    ]

    if "c1" in s:
        peaks.append({"mz": 77, "intensity": 45, "assignment": "C6H5⁺"})
        peaks.append({"mz": 91, "intensity": 100, "assignment": "トロピリウムイオン候補 C7H7⁺"})

    if "C(=O)" in s or "O=C" in s:
        peaks.append({"mz": 43, "intensity": 100, "assignment": "アシリウムイオン候補 RCO⁺"})

    merged = {}
    for peak in peaks:
        mz = peak["mz"]
        if mz not in merged or peak["intensity"] > merged[mz]["intensity"]:
            merged[mz] = peak

    return sorted(merged.values(), key=lambda p: p["mz"])


def generate_h_nmr(smiles: str):
    s = smiles or ""
    peaks = []

    if "c1" in s:
        peaks.append({
            "shift": "7.0-8.0 ppm",
            "multiplicity": "m",
            "integration": "Ar-H",
            "assignment": "芳香族H"
        })

    if "O" in s:
        peaks.append({
            "shift": "3.3-4.2 ppm",
            "multiplicity": "m",
            "integration": "H",
            "assignment": "O隣接プロトン"
        })

    if "C(=O)" in s or "O=C" in s:
        peaks.append({
            "shift": "2.0-2.6 ppm",
            "multiplicity": "m",
            "integration": "H",
            "assignment": "カルボニル隣接プロトン"
        })

    peaks.append({
        "shift": "0.8-1.8 ppm",
        "multiplicity": "m",
        "integration": "H",
        "assignment": "アルキルH"
    })

    return peaks


def generate_c_nmr(smiles: str):
    s = smiles or ""
    peaks = []

    if "C(=O)" in s or "O=C" in s:
        peaks.append({"shift": "170-210 ppm", "assignment": "C=O"})

    if "c1" in s:
        peaks.append({"shift": "120-150 ppm", "assignment": "芳香族C"})

    if "O" in s:
        peaks.append({"shift": "50-80 ppm", "assignment": "O隣接C"})

    peaks.append({"shift": "10-40 ppm", "assignment": "アルキルC"})

    return peaks