def normalize(text: str) -> str:
    return (text or "").strip().lower()


EXPLICIT_CATEGORY_MAP = {
    # 炭化水素
    "methane": "炭化水素",
    "ethane": "炭化水素",
    "propane": "炭化水素",
    "butane": "炭化水素",
    "pentane": "炭化水素",
    "hexane": "炭化水素",
    "heptane": "炭化水素",
    "octane": "炭化水素",
    "nonane": "炭化水素",
    "decane": "炭化水素",
    "cyclopentane": "炭化水素",
    "cyclohexane": "炭化水素",

    # 不飽和炭化水素
    "ethene": "不飽和炭化水素",
    "propene": "不飽和炭化水素",
    "1-butene": "不飽和炭化水素",
    "2-butene": "不飽和炭化水素",
    "ethyne": "不飽和炭化水素",
    "propyne": "不飽和炭化水素",

    # アルコール
    "methanol": "アルコール",
    "ethanol": "アルコール",
    "1-propanol": "アルコール",
    "2-propanol": "アルコール",
    "propan-1-ol": "アルコール",
    "propan-2-ol": "アルコール",
    "1-butanol": "アルコール",
    "2-butanol": "アルコール",
    "tert-butanol": "アルコール",
    "1-pentanol": "アルコール",
    "1-hexanol": "アルコール",
    "ethylene glycol": "アルコール",
    "glycerol": "アルコール",
    "cyclohexanol": "アルコール",
    "benzyl alcohol": "アルコール",

    # エーテル
    "dimethyl ether": "エーテル",
    "diethyl ether": "エーテル",
    "tetrahydrofuran": "エーテル",
    "1,4-dioxane": "エーテル",
    "anisole": "エーテル",
    "phenetole": "エーテル",

    # アルデヒド
    "formaldehyde": "アルデヒド",
    "acetaldehyde": "アルデヒド",
    "ethanal": "アルデヒド",
    "propanal": "アルデヒド",
    "butanal": "アルデヒド",
    "pentanal": "アルデヒド",
    "hexanal": "アルデヒド",
    "benzaldehyde": "アルデヒド",
    "salicylaldehyde": "アルデヒド",
    "cinnamaldehyde": "アルデヒド",
    "furfural": "アルデヒド",

    # ケトン
    "acetone": "ケトン",
    "propanone": "ケトン",
    "2-butanone": "ケトン",
    "butan-2-one": "ケトン",
    "2-pentanone": "ケトン",
    "3-pentanone": "ケトン",
    "cyclopentanone": "ケトン",
    "cyclohexanone": "ケトン",
    "acetophenone": "ケトン",
    "benzophenone": "ケトン",
    "camphor": "ケトン",

    # カルボン酸
    "formic acid": "カルボン酸",
    "methanoic acid": "カルボン酸",
    "acetic acid": "カルボン酸",
    "ethanoic acid": "カルボン酸",
    "propionic acid": "カルボン酸",
    "propanoic acid": "カルボン酸",
    "butyric acid": "カルボン酸",
    "butanoic acid": "カルボン酸",
    "valeric acid": "カルボン酸",
    "hexanoic acid": "カルボン酸",
    "benzoic acid": "カルボン酸",
    "salicylic acid": "カルボン酸",
    "phthalic acid": "カルボン酸",
    "terephthalic acid": "カルボン酸",
    "lactic acid": "カルボン酸",
    "citric acid": "カルボン酸",
    "oxalic acid": "カルボン酸",
    "malonic acid": "カルボン酸",
    "succinic acid": "カルボン酸",
    "adipic acid": "カルボン酸",

    # エステル
    "methyl formate": "エステル",
    "ethyl formate": "エステル",
    "methyl acetate": "エステル",
    "ethyl acetate": "エステル",
    "propyl acetate": "エステル",
    "butyl acetate": "エステル",
    "isoamyl acetate": "エステル",
    "methyl propionate": "エステル",
    "ethyl propionate": "エステル",
    "methyl butyrate": "エステル",
    "ethyl butyrate": "エステル",
    "methyl benzoate": "エステル",
    "ethyl benzoate": "エステル",
    "benzyl acetate": "エステル",
    "ethyl lactate": "エステル",

    # 芳香族
    "benzene": "芳香族",
    "toluene": "芳香族",
    "methylbenzene": "芳香族",
    "ethylbenzene": "芳香族",
    "styrene": "芳香族",
    "xylene": "芳香族",
    "o-xylene": "芳香族",
    "m-xylene": "芳香族",
    "p-xylene": "芳香族",
    "phenol": "芳香族",
    "cresol": "芳香族",
    "o-cresol": "芳香族",
    "m-cresol": "芳香族",
    "p-cresol": "芳香族",
    "aniline": "芳香族",
    "nitrobenzene": "芳香族",
    "chlorobenzene": "芳香族",
    "bromobenzene": "芳香族",
    "iodobenzene": "芳香族",
    "naphthalene": "芳香族",
    "anthracene": "芳香族",
    "phenanthrene": "芳香族",
    "biphenyl": "芳香族",
    "benzonitrile": "芳香族",
    "benzyl chloride": "芳香族",
    "benzyl bromide": "芳香族",

    # アミン・窒素化合物
    "methylamine": "アミン・窒素化合物",
    "ethylamine": "アミン・窒素化合物",
    "propylamine": "アミン・窒素化合物",
    "diethylamine": "アミン・窒素化合物",
    "triethylamine": "アミン・窒素化合物",
    "pyridine": "アミン・窒素化合物",
    "pyrrole": "アミン・窒素化合物",
    "imidazole": "アミン・窒素化合物",
    "indole": "アミン・窒素化合物",
    "quinoline": "アミン・窒素化合物",
    "acetonitrile": "アミン・窒素化合物",
    "propionitrile": "アミン・窒素化合物",
    "acrylonitrile": "アミン・窒素化合物",
    "benzamide": "アミン・窒素化合物",
    "acetamide": "アミン・窒素化合物",
    "acetanilide": "アミン・窒素化合物",

    # ハロゲン化物・溶媒
    "chloroform": "ハロゲン化物・溶媒",
    "dichloromethane": "ハロゲン化物・溶媒",
    "carbon tetrachloride": "ハロゲン化物・溶媒",
    "1,2-dichloroethane": "ハロゲン化物・溶媒",
    "vinyl chloride": "ハロゲン化物・溶媒",
    "allyl chloride": "ハロゲン化物・溶媒",
    "ethyl chloride": "ハロゲン化物・溶媒",
    "ethyl bromide": "ハロゲン化物・溶媒",
    "1-bromopropane": "ハロゲン化物・溶媒",
    "2-bromopropane": "ハロゲン化物・溶媒",
    "iodomethane": "ハロゲン化物・溶媒",

    # 含硫黄・含リン化合物
    "dimethyl sulfoxide": "含硫黄・含リン化合物",
    "dimethyl sulfide": "含硫黄・含リン化合物",
    "thiophene": "含硫黄・含リン化合物",
    "benzenethiol": "含硫黄・含リン化合物",
    "diethyl sulfide": "含硫黄・含リン化合物",
    "trimethyl phosphate": "含硫黄・含リン化合物",
    "triethyl phosphate": "含硫黄・含リン化合物",

    # 天然物・生体関連
    "glucose": "天然物・生体関連",
    "fructose": "天然物・生体関連",
    "sucrose": "天然物・生体関連",
    "urea": "天然物・生体関連",
    "caffeine": "天然物・生体関連",
    "nicotine": "天然物・生体関連",
    "menthol": "天然物・生体関連",
    "vanillin": "天然物・生体関連",
    "eugenol": "天然物・生体関連",
    "limonene": "天然物・生体関連",
    "pinene": "天然物・生体関連",
    "citral": "天然物・生体関連",
}


def detect_category(compound: dict) -> str:
    name_en = normalize(compound.get("name_en"))
    name_ja = normalize(compound.get("name_ja"))
    iupac = normalize(compound.get("iupac_name"))
    smiles = compound.get("smiles") or ""

    # 1. 明示マップを最優先
    for key in [name_en, iupac]:
        if key in EXPLICIT_CATEGORY_MAP:
            return EXPLICIT_CATEGORY_MAP[key]

    # 2. 日本語名で判定
    if any(word in name_ja for word in ["メタノール", "エタノール", "プロパノール", "ブタノール", "ペンタノール", "ヘキサノール", "グリコール", "グリセリン"]):
        return "アルコール"

    if any(word in name_ja for word in ["酢酸メチル", "酢酸エチル", "酢酸プロピル", "酢酸ブチル", "安息香酸メチル", "安息香酸エチル", "エステル"]):
        return "エステル"

    if any(word in name_ja for word in ["ギ酸", "酢酸", "プロピオン酸", "酪酸", "吉草酸", "安息香酸", "サリチル酸", "カルボン酸"]):
        return "カルボン酸"

    if any(word in name_ja for word in ["アセトン", "ブタノン", "シクロヘキサノン", "アセトフェノン", "ベンゾフェノン"]):
        return "ケトン"

    if any(word in name_ja for word in ["アルデヒド", "プロパナール", "ブタナール", "ベンズアルデヒド", "ホルムアルデヒド", "アセトアルデヒド"]):
        return "アルデヒド"

    if any(word in name_ja for word in ["エーテル", "テトラヒドロフラン", "ジオキサン", "アニソール"]):
        return "エーテル"

    if any(word in name_ja for word in ["ベンゼン", "トルエン", "キシレン", "フェノール", "アニリン", "ナフタレン", "スチレン", "芳香族"]):
        return "芳香族"

