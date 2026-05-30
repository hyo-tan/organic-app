import json
import re
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
COMPOUNDS_PATH = BASE_DIR / "compounds.json"


TARGET_HEADINGS = {
    "melting_point": [
        "Melting Point",
        "Experimental Melting Point",
    ],
    "boiling_point": [
        "Boiling Point",
        "Experimental Boiling Point",
    ],
    "density": [
        "Density",
        "Experimental Density",
    ],
}


def is_empty(value):
    return value is None or value == "" or value == "-" or value == "unknown" or value == "未登録"


def clean_text(text):
    if text is None:
        return ""

    text = str(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_value_text(value_obj):
    """
    PubChem PUG View の Value から表示用テキストを取り出す。
    StringWithMarkup / Number / String などに対応。
    """
    if not isinstance(value_obj, dict):
        return ""

    if "StringWithMarkup" in value_obj:
        items = value_obj.get("StringWithMarkup", [])
        texts = []

        for item in items:
            if isinstance(item, dict):
                text = item.get("String", "")
                if text:
                    texts.append(text)

        return clean_text("; ".join(texts))

    if "String" in value_obj:
        return clean_text(value_obj.get("String"))

    if "Number" in value_obj:
        return clean_text(value_obj.get("Number"))

    return ""


def find_values_in_section(section, target_words):
    """
    PubChem PUG View の Section を再帰的に探索して、
    heading や name に target_words を含む項目を探す。
    """
    found = []

    if not isinstance(section, dict):
        return found

    heading = section.get("TOCHeading", "") or section.get("Name", "")

    # Information 内を探索
    for info in section.get("Information", []):
        info_name = info.get("Name", "")
        combined_name = f"{heading} {info_name}"

        if any(word.lower() in combined_name.lower() for word in target_words):
            value_text = extract_value_text(info.get("Value", {}))

            if value_text:
                found.append(value_text)

    # Section の見出し自体が一致する場合、その中の Information を拾う
    if any(word.lower() in heading.lower() for word in target_words):
        for info in section.get("Information", []):
            value_text = extract_value_text(info.get("Value", {}))

            if value_text:
                found.append(value_text)

    # 子セクションを再帰探索
    for child in section.get("Section", []):
        found.extend(find_values_in_section(child, target_words))

    return found


def fetch_pug_view_by_cid(cid):
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"

    try:
        res = requests.get(url, timeout=20)

        if res.status_code != 200:
            print(f"  PUG View取得失敗: CID={cid}, status={res.status_code}")
            return None

        return res.json()

    except Exception as e:
        print(f"  PUG View取得エラー: CID={cid}, error={e}")
        return None


def pick_first_reasonable(values):
    """
    取得値が複数ある場合、とりあえず最初の短めの値を採用。
    長すぎる説明文は避ける。
    """
    cleaned = []

    for value in values:
        value = clean_text(value)

        if not value:
            continue

        # 長すぎる説明文は避ける
        if len(value) > 180:
            continue

        cleaned.append(value)

    if cleaned:
        return cleaned[0]

    if values:
        return clean_text(values[0])[:180]

    return ""


def estimate_state(melting_point, boiling_point):
    """
    室温付近での状態をざっくり推定。
    数値が取れない場合は unknown。
    """
    mp_nums = re.findall(r"-?\d+(?:\.\d+)?", str(melting_point))
    bp_nums = re.findall(r"-?\d+(?:\.\d+)?", str(boiling_point))

    if not mp_nums or not bp_nums:
        return "unknown"

    try:
        mp = float(mp_nums[0])
        bp = float(bp_nums[0])
    except ValueError:
        return "unknown"

    room_temp = 25.0

    if room_temp < mp:
        return "固体"

    if room_temp > bp:
        return "気体"

    return "液体"


def main():
    with open(COMPOUNDS_PATH, encoding="utf-8") as f:
        compounds = json.load(f)

    updated = 0
    no_cid = []
    no_data = []

    for index, compound in enumerate(compounds, start=1):
        cid = compound.get("cid")
        name_ja = compound.get("name_ja", "")
        name_en = compound.get("name_en", "")

        needs_update = (
            is_empty(compound.get("melting_point"))
            or is_empty(compound.get("boiling_point"))
            or is_empty(compound.get("density"))
            or is_empty(compound.get("state"))
        )

        if not needs_update:
            continue

        if not cid:
            no_cid.append(f"{name_ja} / {name_en}")
            continue

        print(f"[{index}/{len(compounds)}] 物性取得中: {name_ja} / {name_en} / CID={cid}")

        data = fetch_pug_view_by_cid(cid)

        if not data:
            no_data.append(f"{name_ja} / {name_en} / CID={cid}")
            time.sleep(1.0)
            continue

        record = data.get("Record", {})

        changed_this = False

        for key, headings in TARGET_HEADINGS.items():
            if not is_empty(compound.get(key)):
                continue

            values = find_values_in_section(record, headings)
            picked = pick_first_reasonable(values)

            if picked:
                compound[key] = picked
                changed_this = True
                print(f"  {key}: {picked}")

        # 状態を補完
        if is_empty(compound.get("state")):
            estimated = estimate_state(
                compound.get("melting_point"),
                compound.get("boiling_point"),
            )

            if estimated != "unknown":
                compound["state"] = estimated
                changed_this = True
                print(f"  state: {estimated}")

        if changed_this:
            updated += 1

        time.sleep(1.0)

    with open(COMPOUNDS_PATH, "w", encoding="utf-8") as f:
        json.dump(compounds, f, ensure_ascii=False, indent=2)

    print("----------")
    print(f"物性更新した化合物数: {updated}")

    if no_cid:
        print("")
        print("CIDなし:")
        for item in no_cid[:50]:
            print(f"- {item}")

    if no_data:
        print("")
        print("PubChem詳細取得失敗:")
        for item in no_data[:50]:
            print(f"- {item}")

    print(f"保存先: {COMPOUNDS_PATH}")


if __name__ == "__main__":
    main()