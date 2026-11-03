"""
import_spectra.py — 公開データベースから実験スペクトルを取り込む

対象（いずれも実験データ）:
  - NMRShiftDB2 (https://nmrshiftdb.nmr.uni-koeln.de): 1H / 13C NMR の帰属付きピークリスト
      -> peaks テーブル (h_nmr / c_nmr) と、CAS がある化合物には生成曲線も spectra へ
  - MassBank (https://massbank.eu, release 2025.05.1): EI-MS レコード
      -> peaks テーブル (ei_ms) と、CAS がある化合物には曲線も spectra へ
      ライセンスが ND（改変禁止）のレコードは除外する

化合物の対応付けは InChIKey の完全一致のみ。既存のピーク/曲線がある (化合物, 種類) は上書きしない。

使い方:
  python import_spectra.py            # 必要ならデータをダウンロードして取り込み
  python import_spectra.py --dry-run  # 件数だけ数える
データは backend/.spectra_cache/ にキャッシュされる（NMRShiftDB2 SDF 約160MB / MassBank zip 約213MB）。
"""
import argparse
import re
import sqlite3
import sys
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
import db as dblayer  # noqa: E402
from create_spectra_files import make_nmr_xy  # noqa: E402

DB_PATH = BASE_DIR / "compounds.db"
CACHE_DIR = BASE_DIR / ".spectra_cache"
NMR_URL = "https://sourceforge.net/projects/nmrshiftdb2/files/data/nmrshiftdb2withsignals.sd/download"
NMR_FILE = CACHE_DIR / "nmrshiftdb2withsignals.sd"
MB_URL = "https://zenodo.org/api/records/15341877/files/MassBank%2FMassBank-data-2025.05.1.zip/content"
MB_FILE = CACHE_DIR / "massbank-2025.05.1.zip"

DEPT_LABEL = {"S": "C", "D": "CH", "T": "CH2", "Q": "CH3"}
LICENSE_RANK = {"CC0": 0, "CC BY": 1, "dl-de/by-2-0": 2, "CC BY-SA": 3,
                "CC BY-NC": 4, "CC BY-NC-SA": 5}


def ensure_downloads():
    CACHE_DIR.mkdir(exist_ok=True)
    for url, path in ((NMR_URL, NMR_FILE), (MB_URL, MB_FILE)):
        if not path.exists():
            print(f"downloading {path.name} ...")
            urllib.request.urlretrieve(url, path)
        print(f"data ready: {path.name} ({path.stat().st_size / 1e6:.0f} MB)")


def fmt_shift(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return f"{s} ppm"


# ---------------------------------------------------------------- NMRShiftDB2
SEG_C = re.compile(r"^\s*([\d.]+);([\d.]*)([SDTQ])?;(\d+)")
SEG_H = re.compile(r"^\s*([\d.]+);([\d.]*);(\d+)")


def parse_sdf_records(path):
    rec = {"fields": {}, "atoms": []}
    field = None
    lines = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip() == "$$$$":
                yield rec
                rec = {"fields": {}, "atoms": []}
                field = None
                lines = []
                continue
            lines.append(line)
            if len(lines) == 4:
                # counts line -> atom symbols
                try:
                    natoms = int(line[0:3])
                except ValueError:
                    natoms = 0
                rec["_natoms"] = natoms
                continue
            if len(lines) > 4 and len(rec["atoms"]) < rec.get("_natoms", 0):
                rec["atoms"].append(line[31:34].strip())
                continue
            m = re.match(r"> <(.+)>", line)
            if m:
                field = m.group(1)
                rec["fields"][field] = ""
            elif field:
                rec["fields"][field] += line
    if rec["fields"]:
        yield rec


def solvent_indices(solvent_text):
    return set(int(i) for i in re.findall(r"(\d+):", solvent_text or ""))


def collect_nmr(path, targets):
    """{inchi_key: {'c_nmr': peaks, 'h_nmr': peaks}} を作る"""
    # (key, kind) -> (score, peaks)
    best = {}
    for rec in parse_sdf_records(path):
        f = rec["fields"]
        ik = (f.get("INChI key") or "").strip()
        if ik not in targets:
            continue
        if not ((f.get("Solvent") or "").strip() or (f.get("Field Strength [MHz]") or "").strip()):
            continue  # 実験データでないものは除く
        solv_idx = solvent_indices(f.get("Solvent", ""))
        atoms = rec["atoms"]

        for kind, prefix in (("c_nmr", "Spectrum 13C"), ("h_nmr", "Spectrum 1H")):
            for fname, value in f.items():
                if not fname.startswith(prefix) or not value.strip():
                    continue
                idx = int(fname.rsplit(" ", 1)[1])
                segs = [s for s in value.split("|") if s.strip()]
                score = (1 if idx in solv_idx else 0, len(segs))
                key = (ik, kind)
                if key in best and best[key][0] >= score:
                    continue
                if kind == "c_nmr":
                    peaks = []
                    seen = set()
                    atom_class = {}
                    for s in segs:
                        m = SEG_C.match(s)
                        if not m:
                            continue
                        shift = float(m.group(1))
                        letter = m.group(3)
                        atom_i = int(m.group(4))
                        if letter:
                            atom_class[atom_i] = DEPT_LABEL[letter]
                        if round(shift, 2) in seen:
                            continue
                        seen.add(round(shift, 2))
                        peaks.append({"shift": fmt_shift(shift),
                                      "assignment": DEPT_LABEL.get(letter or "", "C")})
                    peaks.sort(key=lambda p: -float(p["shift"].split()[0]))
                else:
                    # 13C の原子クラス表（同じレコードの全 13C スペクトルから）
                    atom_class = {}
                    for fn2, v2 in f.items():
                        if fn2.startswith("Spectrum 13C"):
                            for s in v2.split("|"):
                                m = SEG_C.match(s)
                                if m and m.group(3):
                                    atom_class[int(m.group(4))] = DEPT_LABEL[m.group(3)]
                    groups = {}
                    for s in segs:
                        m = SEG_H.match(s)
                        if not m:
                            continue
                        shift = round(float(m.group(1)), 2)
                        atom_i = int(m.group(3))
                        g = groups.setdefault(shift, {"n": 0, "atom": atom_i})
                        g["n"] += 1
                    peaks = []
                    for shift, g in groups.items():
                        el = atoms[g["atom"]] if g["atom"] < len(atoms) else ""
                        if el == "C":
                            label = atom_class.get(g["atom"], "CH")
                        elif el in ("O", "N", "S"):
                            label = el + "H"
                        else:
                            label = el
                        peaks.append({"shift": fmt_shift(shift),
                                      "integration": f"{g['n']}H",
                                      "assignment": label})
                    peaks.sort(key=lambda p: -float(p["shift"].split()[0]))
                if peaks:
                    best[key] = (score, peaks)
    result = defaultdict(dict)
    for (ik, kind), (_, peaks) in best.items():
        result[ik][kind] = peaks
    return result


# ---------------------------------------------------------------- MassBank
MB_IK = re.compile(r"INCHIKEY\s+([A-Z]{14}-[A-Z]{10}-[A-Z])")
MB_ACC = re.compile(r"^ACCESSION:\s*(.+)$", re.M)
MB_LIC = re.compile(r"^LICENSE:\s*(.+)$", re.M)
MB_INST = re.compile(r"INSTRUMENT_TYPE:\s*(.+)")
MB_MST = re.compile(r"MS_TYPE\s+(MS\d?)")


def parse_peak_block(text):
    peaks = []
    in_block = False
    for line in text.splitlines():
        if line.startswith("PK$PEAK:"):
            in_block = True
            continue
        if in_block:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    peaks.append((float(parts[0]), float(parts[2])))
                    continue
                except ValueError:
                    pass
            if line.startswith("PK$") or line.startswith("//"):
                break
            if parts and not parts[0][0].isdigit():
                break
    return peaks


def collect_massbank(path, targets):
    """{inchi_key: {'accession':..., 'license':..., 'peaks': [(mz, rel999)]}}"""
    best = {}
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if not info.filename.endswith(".txt"):
                continue
            text = z.read(info).decode("utf-8", errors="replace")
            m = MB_IK.search(text)
            if not m or m.group(1) not in targets:
                continue
            inst = (MB_INST.search(text).group(1) if MB_INST.search(text) else "")
            if "EI" not in inst.upper():
                continue
            mst = (MB_MST.search(text).group(1) if MB_MST.search(text) else "")
            if mst not in ("MS", ""):
                continue
            lic = (MB_LIC.search(text).group(1).strip() if MB_LIC.search(text) else "unknown")
            if "ND" in lic:
                continue  # 改変禁止ライセンスは除外
            peaks = parse_peak_block(text)
            if len(peaks) < 3:
                continue
            acc = (MB_ACC.search(text).group(1).strip() if MB_ACC.search(text) else "")
            rank = (LICENSE_RANK.get(lic, 6), -len(peaks))
            key = m.group(1)
            if key in best and best[key][0] <= rank:
                continue
            best[key] = (rank, {"accession": acc, "license": lic, "peaks": peaks})
    return {k: v[1] for k, v in best.items()}


def num(x):
    return int(x) if float(x).is_integer() else round(float(x), 2)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ensure_downloads()
    con = dblayer.connect(DB_PATH)
    targets = {r[0]: (r[1], r[2]) for r in con.execute(
        "SELECT inchi_key, id, cas FROM compounds WHERE tier='pubchem' AND inchi_key IS NOT NULL")}
    existing_peaks = {(r[0], r[1]) for r in con.execute("SELECT compound_id, kind FROM peaks")}
    existing_spectra = {(r[0], r[1]) for r in con.execute("SELECT compound_id, kind FROM spectra")}
    print(f"targets: {len(targets)} compounds")

    nmr = collect_nmr(NMR_FILE, set(targets))
    print(f"NMR matched: {len(nmr)} compounds "
          f"(13C {sum(1 for v in nmr.values() if 'c_nmr' in v)}, 1H {sum(1 for v in nmr.values() if 'h_nmr' in v)})")
    mb = collect_massbank(MB_FILE, set(targets))
    print(f"MassBank EI-MS matched: {len(mb)} compounds")

    counts = defaultdict(int)
    for ik, kinds in nmr.items():
        cid_id, cas = targets[ik]
        for kind, peaks in kinds.items():
            if (cid_id, kind) in existing_peaks:
                continue
            counts[f"peaks_{kind}"] += 1
            if not args.dry_run:
                dblayer.set_peaks(con, cid_id, kind, peaks)
            if cas and (cid_id, kind) not in existing_spectra:
                counts[f"curve_{kind}"] += 1
                if not args.dry_run:
                    max_ppm = 12 if kind == "h_nmr" else 220
                    dblayer.set_spectrum(con, cid_id, kind, {
                        "source": "NMRShiftDB2（実験ピークリストより生成）",
                        "x_unit": "ppm", "y_unit": "intensity",
                        "data": make_nmr_xy(peaks, max_ppm),
                    })
    for ik, rec in mb.items():
        cid_id, cas = targets[ik]
        if (cid_id, "ei_ms") in existing_peaks:
            continue
        raw = rec["peaks"]
        rel_max = max(r for _, r in raw) or 1
        norm = [(mz, rel / rel_max * 100) for mz, rel in raw]
        top = sorted(norm, key=lambda p: -p[1])[:40]
        peaks = [{"mz": num(mz), "intensity": int(round(y)), "assignment": ""}
                 for mz, y in sorted(top, key=lambda p: -p[1])]
        counts["peaks_ei_ms"] += 1
        if not args.dry_run:
            dblayer.set_peaks(con, cid_id, "ei_ms", peaks)
        if cas and (cid_id, "ei_ms") not in existing_spectra:
            counts["curve_ei_ms"] += 1
            if not args.dry_run:
                curve = [{"x": num(mz), "y": round(y, 1), "assignment": ""}
                         for mz, y in sorted(norm, key=lambda p: p[0])]
                dblayer.set_spectrum(con, cid_id, "ei_ms", {
                    "source": f"MassBank {rec['accession']}（{rec['license']}）",
                    "x_unit": "m/z", "y_unit": "relative intensity",
                    "data": curve,
                })
    if not args.dry_run:
        dblayer.set_meta(con, "spectra_import_sources",
                         "NMR: NMRShiftDB2 (experimental, open content license); "
                         "EI-MS: MassBank 2025.05.1 (per-record CC license in spectrum source)")
        con.commit()
    print("written:" if not args.dry_run else "would write:", dict(counts))
    con.close()


if __name__ == "__main__":
    main()
