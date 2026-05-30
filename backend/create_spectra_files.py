import json
from pathlib import Path
import math

BASE_DIR = Path(__file__).parent
COMPOUNDS_PATH = BASE_DIR / "compounds.json"
SPECTRA_DIR = BASE_DIR / "spectra"


def parse_first_number(text: str) -> float:
    """
    '1740 cm⁻¹' や '3200-3600 cm⁻¹' から最初の数値を取る
    """
    import re

    matches = re.findall(r"\d+(?:\.\d+)?", text)
    if not matches:
        return 0.0

    numbers = [float(x) for x in matches]

    if "-" in text and len(numbers) >= 2:
        return sum(numbers[:2]) / 2

    return numbers[0]


def parse_shift(text: str) -> float:
    """
    '4.12 ppm' や '7.10-7.30 ppm' から代表値を取る
    """
    return parse_first_number(text)


def make_ir_xy(ir_peaks):
    """
    IRピークリストから簡易的な連続曲線を作る
    横軸: 4000 → 500 cm-1
    縦軸: transmittance
    """
    data = []

    for x in range(4000, 499, -10):
        y = 96.0

        for peak in ir_peaks:
            center = parse_first_number(peak.get("wavenumber", ""))
            assignment = peak.get("assignment", "")

            if center <= 0:
                continue

            # ピークの幅
            sigma = 80

            if "-" in peak.get("wavenumber", ""):
                sigma = 180

            # ピークの深さ
            depth = 25

            if "C=O" in assignment:
                depth = 65
            elif "O-H" in assignment:
                depth = 45
            elif "N-H" in assignment:
                depth = 40
            elif "C≡N" in assignment:
                depth = 45
            elif "C-O" in assignment:
                depth = 35

            gaussian = depth * math.exp(-((x - center) ** 2) / (2 * sigma**2))
            y -= gaussian

        y = max(5, min(100, y))

        data.append({
            "x": x,
            "y": round(y, 2)
        })

    return data


def make_ei_ms_xy(ei_ms_peaks):
    return [
        {
            "x": peak["mz"],
            "y": peak["intensity"],
            "assignment": peak.get("assignment", "")
        }
        for peak in ei_ms_peaks
    ]


def make_nmr_xy(nmr_peaks, max_ppm):
    """
    NMRピークリストから簡易的なローレンツ型スペクトルを作る
    """
    data = []

    step = 0.02 if max_ppm <= 20 else 0.2
    point_count = int(max_ppm / step) + 1

    signals = []

    for peak in nmr_peaks:
        center = parse_shift(peak.get("shift", ""))

        if center <= 0:
            continue

        integration_text = peak.get("integration", "1")
        integration = parse_first_number(integration_text) or 1

        multiplicity = peak.get("multiplicity", "").lower()

        if "br" in multiplicity:
            gamma = 0.15 if max_ppm <= 20 else 0.8
        else:
            gamma = 0.03 if max_ppm <= 20 else 0.45

        signals.append({
            "center": center,
            "integration": integration,
            "gamma": gamma
        })

    raw = []

    for i in range(point_count):
        x = round(max_ppm - i * step, 3)
        y = 0.0

        for signal in signals:
            center = signal["center"]
            gamma = signal["gamma"]
            integration = signal["integration"]

            lorentz = integration * (gamma**2) / ((x - center) ** 2 + gamma**2)
            y += lorentz

        raw.append({
            "x": x,
            "y": y
        })

    max_y = max([p["y"] for p in raw], default=1)

    for p in raw:
        data.append({
            "x": p["x"],
            "y": round((p["y"] / max_y) * 100, 2)
        })

    return data


def main():
    if not COMPOUNDS_PATH.exists():
        raise FileNotFoundError(f"compounds.json が見つかりません: {COMPOUNDS_PATH}")

    compounds = json.loads(COMPOUNDS_PATH.read_text(encoding="utf-8"))

    SPECTRA_DIR.mkdir(exist_ok=True)

    created_files = 0

    for compound in compounds:
        cas = compound.get("cas")
        name_ja = compound.get("name_ja", "unknown")

        if not cas:
            print(f"CAS番号なしのためスキップ: {name_ja}")
            continue

        compound_dir = SPECTRA_DIR / cas
        compound_dir.mkdir(parents=True, exist_ok=True)

        # IR
        if compound.get("ir_peaks"):
            ir_data = {
                "type": "IR",
                "source": "generated from compounds.json peak list",
                "source_url": "",
                "x_unit": "cm⁻¹",
                "y_unit": "transmittance",
                "data": make_ir_xy(compound["ir_peaks"])
            }

            (compound_dir / "ir.json").write_text(
                json.dumps(ir_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            created_files += 1

        # EI-MS
        if compound.get("ei_ms_peaks"):
            ms_data = {
                "type": "EI-MS",
                "source": "generated from compounds.json peak list",
                "source_url": "",
                "x_unit": "m/z",
                "y_unit": "relative intensity",
                "data": make_ei_ms_xy(compound["ei_ms_peaks"])
            }

            (compound_dir / "ei-ms.json").write_text(
                json.dumps(ms_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            created_files += 1

        # 1H NMR
        if compound.get("h_nmr_peaks"):
            h_nmr_data = {
                "type": "1H NMR",
                "source": "generated from compounds.json peak list",
                "source_url": "",
                "x_unit": "ppm",
                "y_unit": "intensity",
                "data": make_nmr_xy(compound["h_nmr_peaks"], max_ppm=12)
            }

            (compound_dir / "h-nmr.json").write_text(
                json.dumps(h_nmr_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            created_files += 1

        # 13C NMR
        if compound.get("c_nmr_peaks"):
            c_nmr_data = {
                "type": "13C NMR",
                "source": "generated from compounds.json peak list",
                "source_url": "",
                "x_unit": "ppm",
                "y_unit": "intensity",
                "data": make_nmr_xy(compound["c_nmr_peaks"], max_ppm=220)
            }

            (compound_dir / "c-nmr.json").write_text(
                json.dumps(c_nmr_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            created_files += 1

        print(f"処理完了: {name_ja} / {cas}")

    print("----------")
    print(f"作成したスペクトルJSON数: {created_files}")
    print(f"保存先: {SPECTRA_DIR}")


if __name__ == "__main__":
    main()