import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
COMPOUNDS_PATH = BASE_DIR / "compounds.json"

REMAINING_PROPERTIES = {
    "1-butyne": {
        "melting_point": "-126 °C",
        "boiling_point": "8 °C",
        "density": "0.678",
        "state": "気体"
    },
    "2-butyne": {
        "melting_point": "-32 °C",
        "boiling_point": "27 °C",
        "density": "0.691 g/mL at 25 °C",
        "state": "液体"
    },
    "fructose": {
        "melting_point": "119-122 °C (分解)",
        "boiling_point": "分解",
        "density": "1.59 g/cm³",
        "state": "固体"
    },
    "pinene": {
        "melting_point": "-55 °C",
        "boiling_point": "155-156 °C",
        "density": "0.858 g/mL at 25 °C",
        "state": "液体"
    },
    "alpha-pinene": {
        "melting_point": "-55 °C",
        "boiling_point": "155-156 °C",
        "density": "0.858 g/mL at 25 °C",
        "state": "液体"
    },
    "2-heptanol": {
        "melting_point": "-30.15 °C",
        "boiling_point": "160-162 °C",
        "density": "0.817 g/mL at 25 °C",
        "state": "液体"
    },
    "dimethyl oxalate": {
        "melting_point": "50-54 °C",
        "boiling_point": "163.5 °C",
        "density": "1.148 g/mL at 25 °C",
        "state": "固体"
    },
    "tartaric acid": {
        "melting_point": "170-172 °C",
        "boiling_point": "分解または未登録",
        "density": "1.76",
        "state": "固体"
    },
    "anilide": {
        "melting_point": "142.8-143.8 °C",
        "boiling_point": "未登録",
        "density": "1.381 at 20 °C",
        "state": "固体"
    }
}


def is_empty_value(value):
    return value is None or value == "" or value == "-" or value == "unknown" or value == "未登録"


def main():
    with open(COMPOUNDS_PATH, encoding="utf-8") as f:
        compounds = json.load(f)

    fixed = 0

    for compound in compounds:
        name_en = (compound.get("name_en") or "").strip().lower()
        name_ja = compound.get("name_ja", "")

        props = REMAINING_PROPERTIES.get(name_en)

        # pinene が PubChem 側や自前リストで alpha-pinene 扱いになっている場合の保険
        if not props and name_en in ["α-pinene", "alpha pinene", "a-pinene"]:
            props = REMAINING_PROPERTIES["alpha-pinene"]

        if not props:
            continue

        changed_this = False

        for key in ["melting_point", "boiling_point", "density", "state"]:
            if is_empty_value(compound.get(key)):
                compound[key] = props[key]
                changed_this = True

        if changed_this:
            print(f"補完: {name_ja} / {name_en}")
            fixed += 1

    with open(COMPOUNDS_PATH, "w", encoding="utf-8") as f:
        json.dump(compounds, f, ensure_ascii=False, indent=2)

    print("----------")
    print(f"補完した化合物数: {fixed}")
    print(f"保存先: {COMPOUNDS_PATH}")


if __name__ == "__main__":
    main()