def build_compound_catalog():
    catalog = []

    def add(category, name_en, name_ja):
        catalog.append({
            "category": category,
            "name_en": name_en,
            "name_ja": name_ja
        })

    # 炭化水素
    hydrocarbons = [
        ("methane", "メタン"),
        ("ethane", "エタン"),
        ("propane", "プロパン"),
        ("butane", "ブタン"),
        ("pentane", "ペンタン"),
        ("hexane", "ヘキサン"),
        ("heptane", "ヘプタン"),
        ("octane", "オクタン"),
        ("nonane", "ノナン"),
        ("decane", "デカン"),
        ("undecane", "ウンデカン"),
        ("dodecane", "ドデカン"),
        ("cyclopentane", "シクロペンタン"),
        ("cyclohexane", "シクロヘキサン"),
        ("cycloheptane", "シクロヘプタン"),
        ("methylcyclohexane", "メチルシクロヘキサン")
    ]
    for en, ja in hydrocarbons:
        add("炭化水素", en, ja)

    # 不飽和炭化水素
    unsaturated = [
        ("ethene", "エチレン"),
        ("propene", "プロピレン"),
        ("1-butene", "1-ブテン"),
        ("2-butene", "2-ブテン"),
        ("1-pentene", "1-ペンテン"),
        ("1-hexene", "1-ヘキセン"),
        ("ethyne", "アセチレン"),
        ("propyne", "プロピン"),
        ("1-butyne", "1-ブチン"),
        ("2-butyne", "2-ブチン")
    ]
    for en, ja in unsaturated:
        add("不飽和炭化水素", en, ja)

    # アルコール
    alcohols = [
        ("methanol", "メタノール"),
        ("ethanol", "エタノール"),
        ("1-propanol", "1-プロパノール"),
        ("2-propanol", "2-プロパノール"),
        ("1-butanol", "1-ブタノール"),
        ("2-butanol", "2-ブタノール"),
        ("tert-butanol", "tert-ブタノール"),
        ("1-pentanol", "1-ペンタノール"),
        ("2-pentanol", "2-ペンタノール"),
        ("1-hexanol", "1-ヘキサノール"),
        ("cyclohexanol", "シクロヘキサノール"),
        ("benzyl alcohol", "ベンジルアルコール"),
        ("ethylene glycol", "エチレングリコール"),
        ("glycerol", "グリセリン")
    ]
    for en, ja in alcohols:
        add("アルコール", en, ja)

    # エーテル
    ethers = [
        ("dimethyl ether", "ジメチルエーテル"),
        ("diethyl ether", "ジエチルエーテル"),
        ("methyl tert-butyl ether", "メチルtert-ブチルエーテル"),
        ("tetrahydrofuran", "テトラヒドロフラン"),
        ("1,4-dioxane", "1,4-ジオキサン"),
        ("anisole", "アニソール"),
        ("phenetole", "フェネトール")
    ]
    for en, ja in ethers:
        add("エーテル", en, ja)

    # アルデヒド
    aldehydes = [
        ("formaldehyde", "ホルムアルデヒド"),
        ("acetaldehyde", "アセトアルデヒド"),
        ("propanal", "プロパナール"),
        ("butanal", "ブタナール"),
        ("pentanal", "ペンタナール"),
        ("hexanal", "ヘキサナール"),
        ("benzaldehyde", "ベンズアルデヒド"),
        ("salicylaldehyde", "サリチルアルデヒド"),
        ("cinnamaldehyde", "シンナムアルデヒド"),
        ("furfural", "フルフラール")
    ]
    for en, ja in aldehydes:
        add("アルデヒド", en, ja)

    # ケトン
    ketones = [
        ("acetone", "アセトン"),
        ("2-butanone", "2-ブタノン"),
        ("2-pentanone", "2-ペンタノン"),
        ("3-pentanone", "3-ペンタノン"),
        ("cyclopentanone", "シクロペンタノン"),
        ("cyclohexanone", "シクロヘキサノン"),
        ("acetophenone", "アセトフェノン"),
        ("benzophenone", "ベンゾフェノン"),
        ("camphor", "カンファー")
    ]
    for en, ja in ketones:
        add("ケトン", en, ja)

    # カルボン酸
    acids = [
        ("formic acid", "ギ酸"),
        ("acetic acid", "酢酸"),
        ("propionic acid", "プロピオン酸"),
        ("butyric acid", "酪酸"),
        ("valeric acid", "吉草酸"),
        ("hexanoic acid", "ヘキサン酸"),
        ("benzoic acid", "安息香酸"),
        ("salicylic acid", "サリチル酸"),
        ("phthalic acid", "フタル酸"),
        ("terephthalic acid", "テレフタル酸"),
        ("lactic acid", "乳酸"),
        ("citric acid", "クエン酸"),
        ("oxalic acid", "シュウ酸"),
        ("malonic acid", "マロン酸"),
        ("succinic acid", "コハク酸"),
        ("adipic acid", "アジピン酸")
    ]
    for en, ja in acids:
        add("カルボン酸", en, ja)

    # エステル
    esters = [
        ("methyl formate", "ギ酸メチル"),
        ("ethyl formate", "ギ酸エチル"),
        ("methyl acetate", "酢酸メチル"),
        ("ethyl acetate", "酢酸エチル"),
        ("propyl acetate", "酢酸プロピル"),
        ("butyl acetate", "酢酸ブチル"),
        ("isoamyl acetate", "酢酸イソアミル"),
        ("methyl propionate", "プロピオン酸メチル"),
        ("ethyl propionate", "プロピオン酸エチル"),
        ("methyl butyrate", "酪酸メチル"),
        ("ethyl butyrate", "酪酸エチル"),
        ("methyl benzoate", "安息香酸メチル"),
        ("ethyl benzoate", "安息香酸エチル"),
        ("benzyl acetate", "酢酸ベンジル"),
        ("ethyl lactate", "乳酸エチル")
    ]
    for en, ja in esters:
        add("エステル", en, ja)

    # 芳香族
    aromatics = [
        ("benzene", "ベンゼン"),
        ("toluene", "トルエン"),
        ("ethylbenzene", "エチルベンゼン"),
        ("styrene", "スチレン"),
        ("xylene", "キシレン"),
        ("o-xylene", "o-キシレン"),
        ("m-xylene", "m-キシレン"),
        ("p-xylene", "p-キシレン"),
        ("phenol", "フェノール"),
        ("cresol", "クレゾール"),
        ("o-cresol", "o-クレゾール"),
        ("m-cresol", "m-クレゾール"),
        ("p-cresol", "p-クレゾール"),
        ("aniline", "アニリン"),
        ("nitrobenzene", "ニトロベンゼン"),
        ("chlorobenzene", "クロロベンゼン"),
        ("bromobenzene", "ブロモベンゼン"),
        ("iodobenzene", "ヨードベンゼン"),
        ("naphthalene", "ナフタレン"),
        ("anthracene", "アントラセン"),
        ("phenanthrene", "フェナントレン"),
        ("biphenyl", "ビフェニル"),
        ("benzonitrile", "ベンゾニトリル"),
        ("benzyl chloride", "塩化ベンジル"),
        ("benzyl bromide", "臭化ベンジル")
    ]
    for en, ja in aromatics:
        add("芳香族", en, ja)

    # アミン・窒素化合物
    nitrogen = [
        ("methylamine", "メチルアミン"),
        ("ethylamine", "エチルアミン"),
        ("propylamine", "プロピルアミン"),
        ("diethylamine", "ジエチルアミン"),
        ("triethylamine", "トリエチルアミン"),
        ("pyridine", "ピリジン"),
        ("pyrrole", "ピロール"),
        ("imidazole", "イミダゾール"),
        ("indole", "インドール"),
        ("quinoline", "キノリン"),
        ("acetonitrile", "アセトニトリル"),
        ("propionitrile", "プロピオニトリル"),
        ("acrylonitrile", "アクリロニトリル"),
        ("benzamide", "ベンズアミド"),
        ("acetamide", "アセトアミド"),
        ("acetanilide", "アセトアニリド")
    ]
    for en, ja in nitrogen:
        add("アミン・窒素化合物", en, ja)

    # ハロゲン化物・溶媒
    halogen_solvents = [
        ("chloroform", "クロロホルム"),
        ("dichloromethane", "ジクロロメタン"),
        ("carbon tetrachloride", "四塩化炭素"),
        ("1,2-dichloroethane", "1,2-ジクロロエタン"),
        ("vinyl chloride", "塩化ビニル"),
        ("allyl chloride", "塩化アリル"),
        ("ethyl chloride", "塩化エチル"),
        ("ethyl bromide", "臭化エチル"),
        ("1-bromopropane", "1-ブロモプロパン"),
        ("2-bromopropane", "2-ブロモプロパン"),
        ("iodomethane", "ヨードメタン")
    ]
    for en, ja in halogen_solvents:
        add("ハロゲン化物・溶媒", en, ja)

    # 含硫黄・含リン化合物
    sulfur_phosphorus = [
        ("dimethyl sulfoxide", "ジメチルスルホキシド"),
        ("dimethyl sulfide", "ジメチルスルフィド"),
        ("thiophene", "チオフェン"),
        ("benzenethiol", "ベンゼンチオール"),
        ("diethyl sulfide", "ジエチルスルフィド"),
        ("trimethyl phosphate", "リン酸トリメチル"),
        ("triethyl phosphate", "リン酸トリエチル")
    ]
    for en, ja in sulfur_phosphorus:
        add("含硫黄・含リン化合物", en, ja)

    # 天然物・生体関連
    biomolecules = [
        ("glucose", "グルコース"),
        ("fructose", "フルクトース"),
        ("sucrose", "スクロース"),
        ("urea", "尿素"),
        ("caffeine", "カフェイン"),
        ("nicotine", "ニコチン"),
        ("menthol", "メントール"),
        ("vanillin", "バニリン"),
        ("eugenol", "オイゲノール"),
        ("limonene", "リモネン"),
        ("pinene", "ピネン"),
        ("citral", "シトラール")
    ]
    for en, ja in biomolecules:
        add("天然物・生体関連", en, ja)

    # 追加候補：200件到達用
    extra = [
        ("isobutane", "イソブタン", "炭化水素"),
        ("isopentane", "イソペンタン", "炭化水素"),
        ("neopentane", "ネオペンタン", "炭化水素"),
        ("2-methylpentane", "2-メチルペンタン", "炭化水素"),
        ("3-methylpentane", "3-メチルペンタン", "炭化水素"),
        ("2,2-dimethylbutane", "2,2-ジメチルブタン", "炭化水素"),
        ("2,3-dimethylbutane", "2,3-ジメチルブタン", "炭化水素"),

        ("1-heptanol", "1-ヘプタノール", "アルコール"),
        ("2-heptanol", "2-ヘプタノール", "アルコール"),
        ("1-octanol", "1-オクタノール", "アルコール"),
        ("2-octanol", "2-オクタノール", "アルコール"),
        ("allyl alcohol", "アリルアルコール", "アルコール"),
        ("propargyl alcohol", "プロパルギルアルコール", "アルコール"),

        ("ethyl acetoacetate", "アセト酢酸エチル", "エステル"),
        ("dimethyl carbonate", "炭酸ジメチル", "エステル"),
        ("diethyl carbonate", "炭酸ジエチル", "エステル"),
        ("dimethyl oxalate", "シュウ酸ジメチル", "エステル"),
        ("diethyl oxalate", "シュウ酸ジエチル", "エステル"),

        ("maleic acid", "マレイン酸", "カルボン酸"),
        ("fumaric acid", "フマル酸", "カルボン酸"),
        ("glutaric acid", "グルタル酸", "カルボン酸"),
        ("tartaric acid", "酒石酸", "カルボン酸"),
        ("mandelic acid", "マンデル酸", "カルボン酸"),

        ("hydroquinone", "ヒドロキノン", "芳香族"),
        ("catechol", "カテコール", "芳香族"),
        ("resorcinol", "レゾルシノール", "芳香族"),
        ("benzyl alcohol", "ベンジルアルコール", "アルコール"),
        ("benzyl acetate", "酢酸ベンジル", "エステル"),
        ("benzylamine", "ベンジルアミン", "アミン・窒素化合物"),
        ("phenethylamine", "フェネチルアミン", "アミン・窒素化合物"),

        ("morpholine", "モルホリン", "アミン・窒素化合物"),
        ("piperidine", "ピペリジン", "アミン・窒素化合物"),
        ("piperazine", "ピペラジン", "アミン・窒素化合物"),
        ("anilide", "アニリド", "アミン・窒素化合物"),

        ("ethyl chloroformate", "クロロギ酸エチル", "ハロゲン化物・溶媒"),
        ("benzoyl chloride", "塩化ベンゾイル", "ハロゲン化物・溶媒"),
        ("acetyl chloride", "塩化アセチル", "ハロゲン化物・溶媒"),

        ("dimethylformamide", "ジメチルホルムアミド", "アミン・窒素化合物"),
        ("dimethylacetamide", "ジメチルアセトアミド", "アミン・窒素化合物"),
        ("nitromethane", "ニトロメタン", "アミン・窒素化合物"),
        ("nitroethane", "ニトロエタン", "アミン・窒素化合物"),

        ("ethyl mercaptan", "エタンチオール", "含硫黄・含リン化合物"),
        ("dimethyl disulfide", "ジメチルジスルフィド", "含硫黄・含リン化合物"),
        ("diphenyl sulfide", "ジフェニルスルフィド", "含硫黄・含リン化合物"),

        ("acetylacetone", "アセチルアセトン", "ケトン"),
        ("methyl isobutyl ketone", "メチルイソブチルケトン", "ケトン"),
        ("diacetyl", "ジアセチル", "ケトン")
    ]

    for en, ja, category in extra:
        add(category, en, ja)

    # 重複除去
    seen = set()
    unique = []

    for item in catalog:
        key = item["name_en"].lower()
        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique