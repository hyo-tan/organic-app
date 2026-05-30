import json
from pathlib import Path

from category_rules import detect_category

BASE_DIR = Path(__file__).parent
COMPOUNDS_PATH = BASE_DIR / "compounds.json"


def main():
    with open(COMPOUNDS_PATH, encoding="utf-8") as f:
        compounds = json.load(f)

    changed = 0

    for compound in compounds:
        old_category = compound.get("category", "")
        new_category = detect_category(compound)

        if old_category != new_category:
            print(
                f"{compound.get('name_ja')} / {compound.get('name_en')}: "
                f"{old_category} -> {new_category}"
            )
            compound["category"] = new_category
            changed += 1

    with open(COMPOUNDS_PATH, "w", encoding="utf-8") as f:
        json.dump(compounds, f, ensure_ascii=False, indent=2)

    print("----------")
    print(f"カテゴリ修正数: {changed}")
    print(f"保存先: {COMPOUNDS_PATH}")


if __name__ == "__main__":
    main()