import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
COMPOUNDS_PATH = BASE_DIR / "compounds.json"

JAPANESE_NAME_MAP = {
    # alcohols
    "methanol": "メタノール",
    "ethanol": "エタノール",
    "1-propanol": "1-プロパノール",
    "propan-1-ol": "1-プロパノール",
    "n-propanol": "1-プロパノール",
    "2-propanol": "2-プロパノール",
    "propan-2-ol": "2-プロパノール",
    "isopropanol": "2-プロパノール",
    "1-butanol": "1-ブタノール",
    "butan-1-ol": "1-ブタノール",
    "2-butanol": "2-ブタノール",
    "butan-2-ol": "2-ブタノール",
    "tert-butanol": "tert-ブタノール",
    "tert-butyl alcohol": "tert-ブタノール",
    "2-methylpropan-2-ol": "tert-ブタノール",
    "1-pentanol": "1-ペンタノール",
    "pentan-1-ol": "1-ペンタノール",
    "1-hexanol": "1-ヘキサノール",
    "hexan-1-ol": "1-ヘキサノール",
    "ethylene glycol": "エチレングリコール",
    "ethane-1,2-diol": "エチレングリコール",

    # ketones / aldehydes
    "acetone": "アセトン",
    "propanone": "アセトン",
    "2-butanone": "2-ブタノン",
    "butan-2-one": "2-ブタノン",
    "cyclohexanone": "シクロヘキサノン",
    "acetaldehyde": "アセトアルデヒド",
    "ethanal": "アセトアルデヒド",
    "propanal": "プロパナール",
    "butanal": "ブタナール",
    "benzaldehyde": "ベンズアルデヒド",
    "acetophenone": "アセトフェノン",
    "1-phenylethanone": "アセトフェノン",

    # acids
    "formic acid": "ギ酸",
    "methanoic acid": "ギ酸",
    "acetic acid": "酢酸",
    "ethanoic acid": "酢酸",
    "propionic acid": "プロピオン酸",
    "propanoic acid": "プロピオン酸",
    "butyric acid": "酪酸",
    "butanoic acid": "酪酸",
    "benzoic acid": "安息香酸",
    "salicylic acid": "サリチル酸",
    "2-hydroxybenzoic acid": "サリチル酸",

    # esters
    "methyl acetate": "酢酸メチル",
    "methyl ethanoate": "酢酸メチル",
    "ethyl acetate": "酢酸エチル",
    "ethyl ethanoate": "酢酸エチル",
    "propyl acetate": "酢酸プロピル",
    "propyl ethanoate": "酢酸プロピル",
    "butyl acetate": "酢酸ブチル",
    "butyl ethanoate": "酢酸ブチル",
    "methyl benzoate": "安息香酸メチル",
    "ethyl benzoate": "安息香酸エチル",

    # aromatics
    "benzene": "ベンゼン",
    "toluene": "トルエン",
    "methylbenzene": "トルエン",
    "ethylbenzene": "エチルベンゼン",
    "styrene": "スチレン",
    "ethenylbenzene": "スチレン",
    "phenol": "フェノール",
    "aniline": "アニリン",
    "nitrobenzene": "ニトロベンゼン",
    "chlorobenzene": "クロロベンゼン",
    "bromobenzene": "ブロモベンゼン",
    "iodobenzene": "ヨードベンゼン",
    "naphthalene": "ナフタレン",
    "anisole": "アニソール",
    "methoxybenzene": "アニソール",
    "benzonitrile": "ベンゾニトリル",

    # hydrocarbons / solvents
    "hexane": "ヘキサン",
    "heptane": "ヘプタン",
    "octane": "オクタン",
    "cyclohexane": "シクロヘキサン",
    "diethyl ether": "ジエチルエーテル",
    "ethoxyethane": "ジエチルエーテル",
    "tetrahydrofuran": "テトラヒドロフラン",
    "chloroform": "クロロホルム",
    "trichloromethane": "クロロホルム",
    "dichloromethane": "ジクロロメタン",
    "methylene chloride": "ジクロロメタン",
    "acetonitrile": "アセトニトリル",
    "pyridine": "ピリジン"
}


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def main():
    with open(COMPOUNDS_PATH, encoding="utf-8") as f:
        compounds = json.load(f)

    changed = 0
    not_mapped = []

    for compound in compounds:
        name_ja = compound.get("name_ja", "")
        name_en = compound.get("name_en", "")
        iupac_name = compound.get("iupac_name", "")

        candidates = [
            normalize(name_ja),
            normalize(name_en),
            normalize(iupac_name),
        ]

        new_name_ja = None

        for candidate in candidates:
            if candidate in JAPANESE_NAME_MAP:
                new_name_ja = JAPANESE_NAME_MAP[candidate]
                break

        if new_name_ja:
            if name_ja != new_name_ja:
                print(f"{name_ja} -> {new_name_ja}")
                compound["name_ja"] = new_name_ja
                changed += 1
        else:
            # 英字を含む name_ja だけ未対応として表示
            if any("a" <= ch.lower() <= "z" for ch in name_ja):
                not_mapped.append({
                    "name_ja": name_ja,
                    "name_en": name_en,
                    "iupac_name": iupac_name
                })

    with open(COMPOUNDS_PATH, "w", encoding="utf-8") as f:
        json.dump(compounds, f, ensure_ascii=False, indent=2)

    print("----------")
    print(f"修正した化合物数: {changed}")

    if not_mapped:
        print("")
        print("未対応の英語名っぽい化合物:")
        for item in not_mapped:
            print(
                f"- name_ja={item['name_ja']} / "
                f"name_en={item['name_en']} / "
                f"iupac={item['iupac_name']}"
            )

    print(f"保存先: {COMPOUNDS_PATH}")


if __name__ == "__main__":
    main()