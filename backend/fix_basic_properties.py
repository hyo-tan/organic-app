import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
COMPOUNDS_PATH = BASE_DIR / "compounds.json"

# 代表値・参考値として使う簡易物性データ
# 単位は表示用文字列として保存する
BASIC_PROPERTIES = {
    "1-propanol": {
        "melting_point": "-126 °C",
        "boiling_point": "97 °C",
        "density": "0.803 g/mL",
        "state": "液体"
    },
    "2-propanol": {
        "melting_point": "-89 °C",
        "boiling_point": "82.6 °C",
        "density": "0.785 g/mL",
        "state": "液体"
    },
    "1-butanol": {
        "melting_point": "-89.8 °C",
        "boiling_point": "117.7 °C",
        "density": "0.810 g/mL",
        "state": "液体"
    },
    "2-butanol": {
        "melting_point": "-114.7 °C",
        "boiling_point": "99.5 °C",
        "density": "0.808 g/mL",
        "state": "液体"
    },
    "tert-butanol": {
        "melting_point": "25.5 °C",
        "boiling_point": "82.2 °C",
        "density": "0.775 g/mL",
        "state": "固体または液体"
    },
    "1-pentanol": {
        "melting_point": "-78 °C",
        "boiling_point": "138 °C",
        "density": "0.811 g/mL",
        "state": "液体"
    },
    "1-hexanol": {
        "melting_point": "-52 °C",
        "boiling_point": "157 °C",
        "density": "0.814 g/mL",
        "state": "液体"
    },
    "ethylene glycol": {
        "melting_point": "-12.9 °C",
        "boiling_point": "197.3 °C",
        "density": "1.113 g/mL",
        "state": "液体"
    },

    "2-butanone": {
        "melting_point": "-86 °C",
        "boiling_point": "79.6 °C",
        "density": "0.805 g/mL",
        "state": "液体"
    },
    "cyclohexanone": {
        "melting_point": "-47 °C",
        "boiling_point": "155.6 °C",
        "density": "0.947 g/mL",
        "state": "液体"
    },
    "acetaldehyde": {
        "melting_point": "-123.5 °C",
        "boiling_point": "20.2 °C",
        "density": "0.784 g/mL",
        "state": "液体"
    },
    "propanal": {
        "melting_point": "-81 °C",
        "boiling_point": "49 °C",
        "density": "0.807 g/mL",
        "state": "液体"
    },
    "butanal": {
        "melting_point": "-96 °C",
        "boiling_point": "75 °C",
        "density": "0.800 g/mL",
        "state": "液体"
    },
    "benzaldehyde": {
        "melting_point": "-26 °C",
        "boiling_point": "179 °C",
        "density": "1.044 g/mL",
        "state": "液体"
    },
    "acetophenone": {
        "melting_point": "20 °C",
        "boiling_point": "202 °C",
        "density": "1.028 g/mL",
        "state": "液体または固体"
    },

    "formic acid": {
        "melting_point": "8.4 °C",
        "boiling_point": "100.8 °C",
        "density": "1.220 g/mL",
        "state": "液体"
    },
    "propionic acid": {
        "melting_point": "-20.5 °C",
        "boiling_point": "141 °C",
        "density": "0.993 g/mL",
        "state": "液体"
    },
    "butyric acid": {
        "melting_point": "-7.9 °C",
        "boiling_point": "163.5 °C",
        "density": "0.959 g/mL",
        "state": "液体"
    },
    "salicylic acid": {
        "melting_point": "158.6 °C",
        "boiling_point": "分解",
        "density": "1.44 g/cm³",
        "state": "固体"
    },

    "methyl acetate": {
        "melting_point": "-98 °C",
        "boiling_point": "57 °C",
        "density": "0.932 g/mL",
        "state": "液体"
    },
    "propyl acetate": {
        "melting_point": "-95 °C",
        "boiling_point": "102 °C",
        "density": "0.888 g/mL",
        "state": "液体"
    },
    "butyl acetate": {
        "melting_point": "-78 °C",
        "boiling_point": "126 °C",
        "density": "0.882 g/mL",
        "state": "液体"
    },
    "methyl benzoate": {
        "melting_point": "-12 °C",
        "boiling_point": "199.6 °C",
        "density": "1.094 g/mL",
        "state": "液体"
    },
    "ethyl benzoate": {
        "melting_point": "-34 °C",
        "boiling_point": "213 °C",
        "density": "1.045 g/mL",
        "state": "液体"
    },

    "ethylbenzene": {
        "melting_point": "-95 °C",
        "boiling_point": "136 °C",
        "density": "0.867 g/mL",
        "state": "液体"
    },
    "styrene": {
        "melting_point": "-30.6 °C",
        "boiling_point": "145 °C",
        "density": "0.909 g/mL",
        "state": "液体"
    },
    "nitrobenzene": {
        "melting_point": "5.7 °C",
        "boiling_point": "210.9 °C",
        "density": "1.199 g/mL",
        "state": "液体"
    },
    "chlorobenzene": {
        "melting_point": "-45 °C",
        "boiling_point": "132 °C",
        "density": "1.106 g/mL",
        "state": "液体"
    },
    "bromobenzene": {
        "melting_point": "-30.6 °C",
        "boiling_point": "156 °C",
        "density": "1.495 g/mL",
        "state": "液体"
    },
    "iodobenzene": {
        "melting_point": "-31 °C",
        "boiling_point": "188 °C",
        "density": "1.83 g/mL",
        "state": "液体"
    },
    "naphthalene": {
        "melting_point": "80.2 °C",
        "boiling_point": "218 °C",
        "density": "1.14 g/cm³",
        "state": "固体"
    },
    "anisole": {
        "melting_point": "-37 °C",
        "boiling_point": "154 °C",
        "density": "0.995 g/mL",
        "state": "液体"
    },
    "benzonitrile": {
        "melting_point": "-13 °C",
        "boiling_point": "191 °C",
        "density": "1.01 g/mL",
        "state": "液体"
    },

    "heptane": {
        "melting_point": "-90.6 °C",
        "boiling_point": "98.4 °C",
        "density": "0.684 g/mL",
        "state": "液体"
    },
    "octane": {
        "melting_point": "-56.8 °C",
        "boiling_point": "125.6 °C",
        "density": "0.703 g/mL",
        "state": "液体"
    }
}


def is_empty_value(value):
    return value is None or value == "" or value == "-" or value == "unknown"


def main():
    with open(COMPOUNDS_PATH, encoding="utf-8") as f:
        compounds = json.load(f)

    fixed = 0
    not_found = []

    for compound in compounds:
        name_en = (compound.get("name_en") or "").strip().lower()
        name_ja = compound.get("name_ja", "")

        props = BASIC_PROPERTIES.get(name_en)

        if not props:
            # 自動生成化合物で、物性が空のものだけ記録
            if (
                is_empty_value(compound.get("melting_point"))
                or is_empty_value(compound.get("boiling_point"))
                or is_empty_value(compound.get("density"))
                or is_empty_value(compound.get("state"))
            ):
                not_found.append(f"{name_ja} / {name_en}")
            continue

        changed_this = False

        for key in ["melting_point", "boiling_point", "density", "state"]:
            if is_empty_value(compound.get(key)):
                compound[key] = props[key]
                changed_this = True

        if changed_this:
            print(f"物性補完: {name_ja} / {name_en}")
            fixed += 1

    with open(COMPOUNDS_PATH, "w", encoding="utf-8") as f:
        json.dump(compounds, f, ensure_ascii=False, indent=2)

    print("----------")
    print(f"物性補完した化合物数: {fixed}")

    if not_found:
        print("")
        print("物性未登録のままの化合物:")
        for item in not_found:
            print(f"- {item}")

    print(f"保存先: {COMPOUNDS_PATH}")


if __name__ == "__main__":
    main()
