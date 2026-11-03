"""
英語名からカタカナ系統名を生成するスクリプト (Phase 1.7)

Wikidata 等の公開DBに日本語名が存在しない化合物について、英語の系統名を
規則的にカタカナ転写する。辞書断片で完全に分解できた名前だけを変換し、
分解できない名前は変換しない（name_ja は空のまま）。
生成した行には name_ja_generated=1 の印を付け、実在の日本語名と区別する。
既存の name_ja は上書きしない。再実行しても安全。

使い方:
    python generate_katakana_names.py            # 分析のみ（DBは変更しない）
    python generate_katakana_names.py --apply    # DBに反映する
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from collections import Counter

import db as dblayer

# ---------------------------------------------------------------------------
# 断片辞書（英語断片 -> カタカナ）。長いキーから貪欲に一致させる。
# ---------------------------------------------------------------------------
FRAGMENTS: dict[str, str] = {
    # 倍数接頭辞・構造接頭辞
    "mono": "モノ", "di": "ジ", "tri": "トリ", "tetra": "テトラ", "penta": "ペンタ",
    "hexa": "ヘキサ", "hepta": "ヘプタ", "octa": "オクタ", "nona": "ノナ", "deca": "デカ",
    "undeca": "ウンデカ", "dodeca": "ドデカ", "bis": "ビス", "tris": "トリス",
    "cyclo": "シクロ", "bicyclo": "ビシクロ", "spiro": "スピロ", "homo": "ホモ",
    "nor": "ノル", "neo": "ネオ", "iso": "イソ", "endo": "エンド", "exo": "エキソ",
    "cis": "シス", "trans": "トランス", "meso": "メソ", "syn": "シン", "anti": "アンチ",
    # 官能基・置換基
    "hydroxy": "ヒドロキシ", "dihydroxy": "ジヒドロキシ", "trihydroxy": "トリヒドロキシ",
    "oxo": "オキソ", "dioxo": "ジオキソ", "trioxo": "トリオキソ",
    "amino": "アミノ", "diamino": "ジアミノ", "imino": "イミノ", "amido": "アミド",
    "acetamido": "アセトアミド", "methoxy": "メトキシ", "ethoxy": "エトキシ",
    "propoxy": "プロポキシ", "butoxy": "ブトキシ", "phenoxy": "フェノキシ",
    "chloro": "クロロ", "dichloro": "ジクロロ", "trichloro": "トリクロロ",
    "fluoro": "フルオロ", "difluoro": "ジフルオロ", "trifluoro": "トリフルオロ",
    "bromo": "ブロモ", "dibromo": "ジブロモ", "iodo": "ヨード", "diiodo": "ジヨード",
    "nitro": "ニトロ", "dinitro": "ジニトロ", "nitroso": "ニトロソ",
    "cyano": "シアノ", "dicyano": "ジシアノ", "isocyano": "イソシアノ",
    "azido": "アジド", "diazo": "ジアゾ", "azo": "アゾ", "hydrazino": "ヒドラジノ",
    "mercapto": "メルカプト", "sulfanyl": "スルファニル", "thiomethyl": "チオメチル",
    "methylthio": "メチルチオ", "ethylthio": "エチルチオ",
    "carboxy": "カルボキシ", "carboxylic": "カルボン", "carbonyl": "カルボニル",
    "formyl": "ホルミル", "acetyl": "アセチル", "propionyl": "プロピオニル",
    "butyryl": "ブチリル", "benzoyl": "ベンゾイル", "acryloyl": "アクリロイル",
    "hydroxymethyl": "ヒドロキシメチル", "aminomethyl": "アミノメチル",
    "chloromethyl": "クロロメチル", "trifluoromethyl": "トリフルオロメチル",
    "dimethylamino": "ジメチルアミノ", "diethylamino": "ジエチルアミノ",
    "methylamino": "メチルアミノ", "ethylamino": "エチルアミノ",
    "phosphoryl": "ホスホリル", "hydroxyphosphoryl": "ヒドロキシホスホリル",
    "phosphono": "ホスホノ", "sulfo": "スルホ", "sulfamoyl": "スルファモイル",
    "carbamoyl": "カルバモイル", "thiocarbamoyl": "チオカルバモイル",
    "guanidino": "グアニジノ", "ureido": "ウレイド", "acet": "アセト",
    "ylidene": "イリデン", "methylidene": "メチリデン", "ethylidene": "エチリデン",
    "propylidene": "プロピリデン", "benzylidene": "ベンジリデン",
    "carboxamide": "カルボキサミド", "carbamide": "カルバミド",
    "diene": "ジエン", "triene": "トリエン", "tetraene": "テトラエン",
    "hydrogen": "水素", "dihydrogen": "二水素",
    "eicosa": "エイコサ", "docosa": "ドコサ", "tetracosa": "テトラコサ",
    "tricosa": "トリコサ", "heneicosa": "ヘンエイコサ", "noic": "ン",
    "pyridin": "ピリジン", "pyrrolo": "ピロロ", "imidazo": "イミダゾ",
    "pyrazolo": "ピラゾロ", "triazolo": "トリアゾロ", "thiazolo": "チアゾロ",
    "oxazolo": "オキサゾロ", "pyrido": "ピリド", "thieno": "チエノ", "furo": "フロ",
    "indolo": "インドロ", "benzimidazo": "ベンズイミダゾ", "quinolin": "キノリン",
    "thiourea": "チオ尿素", "selenourea": "セレノ尿素",
    "eicosenoic": "エイコセン", "eicosadienoic": "エイコサジエン",
    "eicosatrienoic": "エイコサトリエン", "eicosatetraenoic": "エイコサテトラエン",
    "eicosapentaenoic": "エイコサペンタエン", "docosenoic": "ドコセン",
    "docosahexaenoic": "ドコサヘキサエン", "docosapentaenoic": "ドコサペンタエン",
    "tetracosenoic": "テトラコセン", "arachidonic": "アラキドン",
    "nervonic": "ネルボン", "erucic": "エルカ", "brassidic": "ブラシジン",
    "vaccenic": "バクセン", "palmitoleic": "パルミトレイン", "myristic": "ミリスチン",
    "myristoleic": "ミリストレイン", "lauric": "ラウリン", "capric": "カプリン",
    "caprylic": "カプリル", "caproic": "カプロン", "margaric": "マルガリン",
    "arachidic": "アラキジン", "behenic": "ベヘン", "lignoceric": "リグノセリン",
    "cerotic": "セロチン", "montanic": "モンタン", "melissic": "メリシン",
    "undecenoic": "ウンデセン", "undecanoic": "ウンデカン",
    "phosphonic": "ホスホン", "phosphon": "ホスホン", "sulfonic": "スルホン",
    "sulfon": "スルホン", "boronic": "ボロン", "arsonic": "アルソン",
    "phosphinic": "ホスフィン", "carboxyl": "カルボキシル", "glycol": "グリコール",
    "quinone": "キノン", "guanidine": "グアニジン", "aniline": "アニリン",
    "icosa": "イコサ", "icosanoic": "イコサン", "icosenoic": "イコセン",
    # アミノ酸
    "histidine": "ヒスチジン", "histidin": "ヒスチジン", "lysine": "リシン",
    "lysin": "リシン", "arginine": "アルギニン", "arginin": "アルギニン",
    "asparagine": "アスパラギン", "asparagin": "アスパラギン",
    "glutamine": "グルタミン", "glutamin": "グルタミン", "serine": "セリン",
    "serin": "セリン", "threonine": "スレオニン", "threonin": "スレオニン",
    "cysteine": "システイン", "cystein": "システイン", "cystine": "シスチン",
    "methionine": "メチオニン", "methionin": "メチオニン",
    "tyrosine": "チロシン", "tyrosin": "チロシン", "tryptophan": "トリプトファン",
    "proline": "プロリン", "prolin": "プロリン", "glycine": "グリシン",
    "glycin": "グリシン", "alanine": "アラニン", "alanin": "アラニン",
    "valine": "バリン", "valin": "バリン", "leucine": "ロイシン", "leucin": "ロイシン",
    "isoleucine": "イソロイシン", "isoleucin": "イソロイシン",
    "phenylalanine": "フェニルアラニン", "phenylalanin": "フェニルアラニン",
    "hydroxyproline": "ヒドロキシプロリン", "sarcosine": "サルコシン",
    "homocysteine": "ホモシステイン", "ornithine": "オルニチン",
    "citrulline": "シトルリン", "taurine": "タウリン",
    "aspartic": "アスパラギン", "glutamic": "グルタミン",
    "phosphatidyl": "ホスファチジル", "phosphatidylcholine": "ホスファチジルコリン",
    "sphingosine": "スフィンゴシン", "ceramide": "セラミド",
    "prostaglandin": "プロスタグランジン", "thromboxane": "トロンボキサン",
    "leukotriene": "ロイコトリエン", "bilirubin": "ビリルビン",
    "biliverdin": "ビリベルジン", "heme": "ヘム", "haem": "ヘム",
    "chlorophyll": "クロロフィル", "carotene": "カロテン",
    "lycopene": "リコペン", "lutein": "ルテイン", "zeaxanthin": "ゼアキサンチン",
    "pyrimidin": "ピリミジン", "carboxylate": "カルボン酸",
    "phosphonate": "ホスホン酸", "boronate": "ボロン酸", "arsonate": "アルソン酸",
    "carbamate": "カルバマート", "dithiocarbamate": "ジチオカルバマート",
    "thiocarbamate": "チオカルバマート", "carbamic": "カルバミン",
    "methan": "メタン", "ethan": "エタン", "propan": "プロパン", "butan": "ブタン",
    "pentan": "ペンタン", "hexan": "ヘキサン", "heptan": "ヘプタン", "octan": "オクタン",
    "nonan": "ノナン", "decan": "デカン", "cyclohexan": "シクロヘキサン",
    "dioic": "二", "trioic": "三", "enoic": "エン", "ynoic": "イン",
    "octadeca": "オクタデカ", "hexadeca": "ヘキサデカ", "tetradeca": "テトラデカ",
    "pentadeca": "ペンタデカ", "heptadeca": "ヘプタデカ", "nonadeca": "ノナデカ",
    "trideca": "トリデカ", "henicosa": "ヘンイコサ",
    "dotriaconta": "ドトリアコンタ", "dotriacont": "ドトリアコント",
    "tetratriaconta": "テトラトリアコンタ", "hexatriaconta": "ヘキサトリアコンタ",
    "pentatriaconta": "ペンタトリアコンタ", "triaconta": "トリアコンタ",
    "triacont": "トリアコント", "hentriaconta": "ヘントリアコンタ",
    "furanosyl": "フラノシル", "pyranosyl": "ピラノシル",
    "ribofuranosyl": "リボフラノシル", "glucopyranosyl": "グルコピラノシル",
    "galactopyranosyl": "ガラクトピラノシル", "mannopyranosyl": "マンノピラノシル",
    "xylopyranosyl": "キシロピラノシル", "glucosyl": "グルコシル",
    "galactosyl": "ガラクトシル", "ribosyl": "リボシル", "glycosyl": "グリコシル",
    "glucuronosyl": "グルクロノシル", "oxiran": "オキシラン", "oxirane": "オキシラン",
    "thiiran": "チイラン", "aziridine": "アジリジン", "aziridin": "アジリジン",
    "anilino": "アニリノ", "anilide": "アニリド", "cyanamide": "シアナミド",
    "sulfanilamide": "スルファニルアミド", "acetazolamide": "アセタゾラミド",
    "tetrakis": "テトラキス", "pentakis": "ペンタキス", "hexakis": "ヘキサキス",
    "coenzyme": "コエンザイム", "aminium": "アミニウム", "ium": "イウム",
    "pyridinium": "ピリジニウム", "imidazolium": "イミダゾリウム",
    "piperidinium": "ピペリジニウム", "pyrrolidinium": "ピロリジニウム",
    "morpholinium": "モルホリニウム", "quinolinium": "キノリニウム",
    "isoquinolinium": "イソキノリニウム", "benzimidazolium": "ベンズイミダゾリウム",
    "thiazolium": "チアゾリウム", "triazolium": "トリアゾリウム",
    "pyrazolium": "ピラゾリウム", "oxazolium": "オキサゾリウム",
    "phosphonium": "ホスホニウム", "sulfonium": "スルホニウム",
    "arsonium": "アルソニウム", "iodonium": "ヨードニウム",
    "diazonium": "ジアゾニウム", "hydrazinium": "ヒドラジニウム",
    "guanidinium": "グアニジニウム", "anilinium": "アニリニウム",
    "porphyrin": "ポルフィリン", "porphin": "ポルフィン", "chlorin": "クロリン",
    "pheophytin": "フェオフィチン", "hydrazine": "ヒドラジン", "hydrazin": "ヒドラジン",
    "ate": "酸",
    "carbaldehyde": "カルバルデヒド", "tetrone": "テトロン", "oxido": "オキシド",
    "phenol": "フェノール",
    "azepane": "アゼパン", "azepan": "アゼパン", "azepine": "アゼピン",
    "oxepane": "オキセパン", "oxepin": "オキセピン", "thiepane": "チエパン",
    "dehydro": "デヒドロ", "imine": "イミン", "fluoren": "フルオレン",
    "xanthen": "キサンテン", "tetrol": "テトラオール",
    "amphetamine": "アンフェタミン", "methamphetamine": "メタンフェタミン",
    "morpholin": "モルホリン", "siloxane": "シロキサン", "silane": "シラン",
    "silyl": "シリル", "undecan": "ウンデカン", "undecen": "ウンデセン",
    "undecyl": "ウンデシル",

    "tetrahydroxy": "テトラヒドロキシ", "dienoic": "ジエン", "trienoic": "トリエン",
    "tetraenoic": "テトラエン", "pentaenoic": "ペンタエン", "diynoic": "ジイン",
    "oate": "酸", "yn": "イン", "diyn": "ジイン", "idene": "イデン",
    "hydroxymethylidene": "ヒドロキシメチリデン",
    "benzimidazol": "ベンズイミダゾール", "benzothiazol": "ベンゾチアゾール",
    "benzoxazol": "ベンゾオキサゾール", "benzotriazol": "ベンゾトリアゾール",
    "tetrazol": "テトラゾール", "isoxazol": "イソオキサゾール",
    "benzodioxol": "ベンゾジオキソール", "benzodioxole": "ベンゾジオキソール",
    "acetol": "アセトール", "diazole": "ジアゾール", "diazol": "ジアゾール",
    "dithiole": "ジチオール", "dithiol": "ジチオール", "thione": "チオン",
    "carboximidamide": "カルボキシイミドアミド", "imidamide": "イミドアミド",
    "pentofuranosyl": "ペントフラノシル", "pentopyranosyl": "ペントピラノシル",
    "octacosa": "オクタコサ", "hexacosa": "ヘキサコサ", "heptacosa": "ヘプタコサ",
    "nonacosa": "ノナコサ", "pentacosa": "ペンタコサ",
    "azaniumyl": "アザニウムイル", "azanium": "アザニウム",
    "carboxylato": "カルボキシラト", "disulfanyl": "ジスルファニル",
    "ethylene": "エチレン", "propylene": "プロピレン", "butylene": "ブチレン",
    "methylene": "メチレン", "phenylene": "フェニレン",
    "tridecane": "トリデカン", "tetradecane": "テトラデカン",
    "pentadecane": "ペンタデカン", "hexadecane": "ヘキサデカン",
    "heptadecane": "ヘプタデカン", "octadecane": "オクタデカン",
    "nonadecane": "ノナデカン", "eicosane": "エイコサン", "icosane": "イコサン",
    "docosane": "ドコサン", "tetracosane": "テトラコサン",
    "triacontane": "トリアコンタン", "octacosane": "オクタコサン",
    "tetradecan": "テトラデカン", "pentadecan": "ペンタデカン",
    "hexadecan": "ヘキサデカン", "heptadecan": "ヘプタデカン",
    "octadecan": "オクタデカン", "eicosan": "エイコサン",
    "chromen": "クロメン", "inden": "インデン", "pteridin": "プテリジン",
    "corrin": "コリン", "piperazin": "ピペラジン", "morphinan": "モルフィナン",
    "cholic": "コール", "deoxycholic": "デオキシコール",
    "chenodeoxycholic": "ケノデオキシコール", "ursodeoxycholic": "ウルソデオキシコール",
    "lithocholic": "リトコール", "hyocholic": "ヒオコール", "muricholic": "ムリコール",
    "glycocholic": "グリココール", "taurocholic": "タウロコール",
    "morphine": "モルヒネ", "codeine": "コデイン", "cocaine": "コカイン",
    "atropine": "アトロピン", "scopolamine": "スコポラミン", "quinine": "キニン",
    "quinidine": "キニジン", "strychnine": "ストリキニン", "ephedrine": "エフェドリン",
    "pseudoephedrine": "プソイドエフェドリン", "lobeline": "ロベリン",
    "cytisine": "シチシン", "sparteine": "スパルテイン", "coniine": "コニイン",
    "brucine": "ブルシン", "thebaine": "テバイン", "papaverine": "パパベリン",
    "berberine": "ベルベリン", "emetine": "エメチン", "tubocurarine": "ツボクラリン",
    "zabicyclo": "ザビシクロ", "azenyl": "アゼニル", "ose": "オース",
    "ulose": "ウロース", "itol": "イトール", "glucitol": "グルシトール",
    "carbamimidoyl": "カルバムイミドイル",
    # 炭化水素基（アルキル等）
    "methyl": "メチル", "dimethyl": "ジメチル", "trimethyl": "トリメチル", "tetramethyl": "テトラメチル",
    "ethyl": "エチル", "diethyl": "ジエチル", "triethyl": "トリエチル",
    "propyl": "プロピル", "dipropyl": "ジプロピル", "isopropyl": "イソプロピル",
    "butyl": "ブチル", "dibutyl": "ジブチル", "pentyl": "ペンチル", "hexyl": "ヘキシル",
    "heptyl": "ヘプチル", "octyl": "オクチル", "nonyl": "ノニル", "decyl": "デシル",
    "dodecyl": "ドデシル", "hexadecyl": "ヘキサデシル", "octadecyl": "オクタデシル",
    "vinyl": "ビニル", "allyl": "アリル", "phenyl": "フェニル", "diphenyl": "ジフェニル",
    "benzyl": "ベンジル", "benzhydryl": "ベンズヒドリル", "naphthyl": "ナフチル",
    "phenethyl": "フェネチル", "styryl": "スチリル", "cinnamyl": "シンナミル",
    "ethenyl": "エテニル", "propenyl": "プロペニル", "butenyl": "ブテニル",
    "pentenyl": "ペンテニル", "hexenyl": "ヘキセニル", "ethynyl": "エチニル",
    "propynyl": "プロピニル", "allenyl": "アレニル", "isopropenyl": "イソプロペニル",
    "cyclopropyl": "シクロプロピル", "cyclobutyl": "シクロブチル",
    "cyclopentyl": "シクロペンチル", "cyclohexyl": "シクロヘキシル",
    "cycloheptyl": "シクロヘプチル", "cyclooctyl": "シクロオクチル",
    "hydroxyphenyl": "ヒドロキシフェニル", "aminophenyl": "アミノフェニル",
    "chlorophenyl": "クロロフェニル", "nitrophenyl": "ニトロフェニル",
    "methoxyphenyl": "メトキシフェニル", "tolyl": "トリル", "xylyl": "キシリル",
    "mesityl": "メシチル", "cumyl": "クミル", "trityl": "トリチル",
    # 親水素化物・環系
    "methane": "メタン", "ethane": "エタン", "propane": "プロパン", "butane": "ブタン",
    "pentane": "ペンタン", "hexane": "ヘキサン", "heptane": "ヘプタン", "octane": "オクタン",
    "nonane": "ノナン", "decane": "デカン", "undecane": "ウンデカン", "dodecane": "ドデカン",
    "ethene": "エテン", "propene": "プロペン", "butene": "ブテン", "pentene": "ペンテン",
    "hexene": "ヘキセン", "heptene": "ヘプテン", "octene": "オクテン", "nonene": "ノネン",
    "decene": "デセン", "ethyne": "エチン", "propyne": "プロピン", "butyne": "ブチン",
    "pentyne": "ペンチン", "hexyne": "ヘキシン",
    "benzene": "ベンゼン", "toluene": "トルエン", "xylene": "キシレン",
    "naphthalene": "ナフタレン", "anthracene": "アントラセン", "phenanthrene": "フェナントレン",
    "phenanthren": "フェナントレン", "fluorene": "フルオレン", "pyrene": "ピレン",
    "chrysene": "クリセン", "coronene": "コロネン", "azulene": "アズレン",
    "biphenyl": "ビフェニル", "terphenyl": "ターフェニル", "styrene": "スチレン",
    "indene": "インデン", "indane": "インダン", "tetralin": "テトラリン",
    "cyclopropane": "シクロプロパン", "cyclobutane": "シクロブタン",
    "cyclopentane": "シクロペンタン", "cyclohexane": "シクロヘキサン",
    "cycloheptane": "シクロヘプタン", "cyclooctane": "シクロオクタン",
    "cyclopentene": "シクロペンテン", "cyclohexene": "シクロヘキセン",
    "cycloheptene": "シクロヘプテン", "cyclooctene": "シクロオクテン",
    "cyclopentadiene": "シクロペンタジエン", "cyclohexadiene": "シクロヘキサジエン",
    "adamantane": "アダマンタン", "norbornane": "ノルボルナン", "norbornene": "ノルボルネン",
    "decalin": "デカリン", "pinane": "ピナン", "bornane": "ボルナン", "camphane": "カンファン",
    # 複素環
    "furan": "フラン", "pyran": "ピラン", "thiophene": "チオフェン", "pyrrole": "ピロール",
    "pyrrol": "ピロール", "pyridine": "ピリジン", "pyrimidine": "ピリミジン",
    "pyrazine": "ピラジン", "pyridazine": "ピリダジン", "triazine": "トリアジン",
    "purine": "プリン", "purin": "プリン", "pteridine": "プテリジン",
    "indole": "インドール", "indol": "インドール", "indazole": "インダゾール",
    "benzimidazole": "ベンズイミダゾール", "imidazole": "イミダゾール",
    "imidazol": "イミダゾール", "pyrazole": "ピラゾール", "pyrazol": "ピラゾール",
    "oxazole": "オキサゾール", "oxazol": "オキサゾール", "isoxazole": "イソオキサゾール",
    "thiazole": "チアゾール", "thiazol": "チアゾール", "isothiazole": "イソチアゾール",
    "triazole": "トリアゾール", "triazol": "トリアゾール", "tetrazole": "テトラゾール",
    "oxadiazole": "オキサジアゾール", "thiadiazole": "チアジアゾール",
    "quinoline": "キノリン", "isoquinoline": "イソキノリン", "quinazoline": "キナゾリン",
    "quinoxaline": "キノキサリン", "acridine": "アクリジン", "carbazole": "カルバゾール",
    "phenazine": "フェナジン", "phenothiazine": "フェノチアジン",
    "piperidine": "ピペリジン", "piperazine": "ピペラジン", "morpholine": "モルホリン",
    "thiomorpholine": "チオモルホリン", "pyrrolidine": "ピロリジン",
    "pyrrolidin": "ピロリジン", "piperidin": "ピペリジン", "dioxane": "ジオキサン",
    "dioxolane": "ジオキソラン", "oxolane": "オキソラン", "thiolane": "チオラン",
    "oxane": "オキサン", "oxan": "オキサン", "thiane": "チアン", "oxetane": "オキセタン",
    "azetidine": "アゼチジン", "oxazoline": "オキサゾリン", "thiazoline": "チアゾリン",
    "imidazoline": "イミダゾリン", "pyrroline": "ピロリン", "indoline": "インドリン",
    "benzofuran": "ベンゾフラン", "benzothiophene": "ベンゾチオフェン",
    "benzothiazole": "ベンゾチアゾール", "benzoxazole": "ベンゾオキサゾール",
    "benzotriazole": "ベンゾトリアゾール", "coumarin": "クマリン", "chromene": "クロメン",
    "xanthene": "キサンテン", "thioxanthene": "チオキサンテン",
    # 塩基・生体分子系
    "adenine": "アデニン", "adenin": "アデニン", "guanine": "グアニン", "guanin": "グアニン",
    "thymine": "チミン", "cytosine": "シトシン", "cytosin": "シトシン", "uracil": "ウラシル",
    "xanthine": "キサンチン", "xanthin": "キサンチン", "hypoxanthine": "ヒポキサンチン",
    "caffeine": "カフェイン", "theobromine": "テオブロミン", "nicotine": "ニコチン",
    "adenosine": "アデノシン", "guanosine": "グアノシン", "cytidine": "シチジン",
    "uridine": "ウリジン", "thymidine": "チミジン", "inosine": "イノシン",
    # ステロイド・テルペン系ステム
    "androstane": "アンドロスタン", "androstan": "アンドロスタン",
    "androst": "アンドロスト", "estrane": "エストラン", "estran": "エストラン",
    "estr": "エストル", "pregnane": "プレグナン", "pregnan": "プレグナン",
    "pregn": "プレグン", "cholestane": "コレスタン", "cholestan": "コレスタン",
    "cholest": "コレスト", "cholane": "コラン", "cholan": "コラン",
    "lanostane": "ラノスタン", "lanost": "ラノスト", "gonane": "ゴナン", "gonan": "ゴナン",
    "oleanane": "オレアナン", "ursane": "ウルサン", "lupane": "ルパン",
    # 官能基サフィックス・語
    "acid": "酸", "ester": "エステル", "ether": "エーテル", "anhydride": "無水物",
    "peroxide": "過酸化物", "hydroperoxide": "ヒドロペルオキシド",
    "aldehyde": "アルデヒド", "ketone": "ケトン", "alcohol": "アルコール",
    "amine": "アミン", "amide": "アミド", "imide": "イミド", "nitrile": "ニトリル",
    "hydrazide": "ヒドラジド", "hydrazone": "ヒドラゾン", "oxime": "オキシム",
    "semicarbazone": "セミカルバゾン", "thiosemicarbazone": "チオセミカルバゾン",
    "lactone": "ラクトン", "lactam": "ラクタム", "sultone": "スルトン",
    "glycoside": "グリコシド", "glucoside": "グルコシド", "galactoside": "ガラクトシド",
    "glucuronide": "グルクロニド", "vitamin": "ビタミン",
    "dione": "ジオン", "trione": "トリオン", "diol": "ジオール", "triol": "トリオール",
    "tetraol": "テトラオール", "diamine": "ジアミン", "triamine": "トリアミン",
    # 糖・その他生体
    "glucose": "グルコース", "galactose": "ガラクトース", "fructose": "フルクトース",
    "mannose": "マンノース", "ribose": "リボース", "deoxyribose": "デオキシリボース",
    "xylose": "キシロース", "arabinose": "アラビノース", "rhamnose": "ラムノース",
    "fucose": "フコース", "sucrose": "スクロース", "lactose": "ラクトース",
    "maltose": "マルトース", "cellobiose": "セロビオース", "trehalose": "トレハロース",
    "glycerol": "グリセロール", "glyceraldehyde": "グリセルアルデヒド",
    "inositol": "イノシトール", "sorbitol": "ソルビトール", "mannitol": "マンニトール",
    "xylitol": "キシリトール", "erythritol": "エリスリトール",
    "choline": "コリン", "carnitine": "カルニチン", "betaine": "ベタイン",
    "creatine": "クレアチン", "creatinine": "クレアチニン", "urea": "尿素",
    "cholesterol": "コレステロール", "ergosterol": "エルゴステロール",
    "testosterone": "テストステロン", "estradiol": "エストラジオール",
    "progesterone": "プロゲステロン", "cortisol": "コルチゾール",
    "retinol": "レチノール", "tocopherol": "トコフェロール",
    # 元素・金属（語として現れる場合）
    "sodium": "ナトリウム", "potassium": "カリウム", "calcium": "カルシウム",
    "magnesium": "マグネシウム", "barium": "バリウム", "strontium": "ストロンチウム",
    "lithium": "リチウム", "ammonium": "アンモニウム", "zinc": "亜鉛", "iron": "鉄",
    "copper": "銅", "silver": "銀", "aluminum": "アルミニウム", "aluminium": "アルミニウム",
    "lead": "鉛", "tin": "スズ", "mercury": "水銀", "manganese": "マンガン",
    "nickel": "ニッケル", "cobalt": "コバルト", "chromium": "クロム",
    "cadmium": "カドミウム", "beryllium": "ベリリウム", "cesium": "セシウム",
    "caesium": "セシウム", "rubidium": "ルビジウム", "boron": "ホウ素",
    "disodium": "ジナトリウム", "dipotassium": "ジカリウム", "dicalcium": "ジカルシウム",
    # 短いステム（長い一致の後に使う）
    "benz": "ベンズ", "benzo": "ベンゾ", "phen": "フェン", "naphth": "ナフト",
    "anthra": "アントラ", "cyclopenta": "シクロペンタ", "cyclohexa": "シクロヘキサ",
    "cyclohepta": "シクロヘプタ", "cyclobuta": "シクロブタ", "cyclopropa": "シクロプロパ",
    "aza": "アザ", "azabicyclo": "アザビシクロ", "diaza": "ジアザ", "triaza": "トリアザ",
    "oxa": "オキサ", "dioxa": "ジオキサ", "thia": "チア", "dithia": "ジチア",
    "selena": "セレナ", "sila": "シラ", "bora": "ボラ", "phospha": "ホスファ",
    "hydro": "ヒドロ", "dihydro": "ジヒドロ", "tetrahydro": "テトラヒドロ",
    "hexahydro": "ヘキサヒドロ", "perhydro": "ペルヒドロ",
    "oxolan": "オキソラン", "dioxolan": "ジオキソラン", "thiazolidin": "チアゾリジン",
    "oxazolidin": "オキサゾリジン", "imidazolidin": "イミダゾリジン",
    "pyrrolizidin": "ピロリジジン", "tropane": "トロパン", "tropan": "トロパン",
    "quinuclidine": "キヌクリジン", "granatane": "グラナタン",
    "meth": "メト", "eth": "エト", "prop": "プロプ", "but": "ブト", "pent": "ペント",
    "hex": "ヘキス", "hept": "ヘプト", "oct": "オクト", "non": "ノン", "dec": "デク",
    "yl": "イル", "enyl": "エニル", "dienyl": "ジエニル", "diyl": "ジイル",
    "ene": "エン", "en": "エン", "ane": "アン", "an": "アン", "dien": "ジエン",
    "trien": "トリエン", "yne": "イン", "ol": "オール", "one": "オン", "al": "アール",
    "oyl": "オイル", "thio": "チオ", "dithio": "ジチオ", "oxy": "オキシ",
    "peroxy": "ペルオキシ", "epoxy": "エポキシ", "keto": "ケト", "aldo": "アルド",
    "gluco": "グルコ", "galacto": "ガラクト", "manno": "マンノ", "ribo": "リボ",
    "arabino": "アラビノ", "xylo": "キシロ", "deoxy": "デオキシ",
    "aceto": "アセト", "propano": "プロパノ", "butano": "ブタノ", "pentano": "ペンタノ",
    "hexano": "ヘキサノ", "heptano": "ヘプタノ", "octano": "オクタノ",
    "ole": "オレ", "aminoaceto": "アミノアセト",
}

# -oic acid 用ステム（"butanoic" + "acid" -> ブタン + 酸）
OIC_STEMS: dict[str, str] = {
    "methanoic": "メタン", "ethanoic": "エタン", "propanoic": "プロパン",
    "butanoic": "ブタン", "pentanoic": "ペンタン", "hexanoic": "ヘキサン",
    "heptanoic": "ヘプタン", "octanoic": "オクタン", "nonanoic": "ノナン",
    "decanoic": "デカン", "undecanoic": "ウンデカン", "dodecanoic": "ドデカン",
    "tridecanoic": "トリデカン", "tetradecanoic": "テトラデカン",
    "pentadecanoic": "ペンタデカン", "hexadecanoic": "ヘキサデカン",
    "heptadecanoic": "ヘプタデカン", "octadecanoic": "オクタデカン",
    "propenoic": "プロペン", "butenoic": "ブテン", "pentenoic": "ペンテン",
    "hexenoic": "ヘキセン", "octenoic": "オクテン", "hexadecenoic": "ヘキサデセン",
    "octadecenoic": "オクタデセン", "octadecadienoic": "オクタデカジエン",
    "benzoic": "安息香", "acetic": "酢", "formic": "ギ", "propionic": "プロピオン",
    "butyric": "酪", "isobutyric": "イソ酪", "valeric": "吉草", "isovaleric": "イソ吉草",
    "lactic": "乳", "malic": "リンゴ", "citric": "クエン", "tartaric": "酒石",
    "succinic": "コハク", "fumaric": "フマル", "maleic": "マレイン", "oxalic": "シュウ",
    "salicylic": "サリチル", "phthalic": "フタル", "isophthalic": "イソフタル",
    "terephthalic": "テレフタル", "oleic": "オレイン", "stearic": "ステアリン",
    "palmitic": "パルミチン", "linoleic": "リノール", "linolenic": "リノレン",
    "acrylic": "アクリル", "methacrylic": "メタクリル", "uric": "尿",
    "glycolic": "グリコール", "pyruvic": "ピルビン", "malonic": "マロン",
    "glutaric": "グルタル", "adipic": "アジピン", "pimelic": "ピメリン",
    "suberic": "スベリン", "azelaic": "アゼライン", "sebacic": "セバシン",
    "cinnamic": "ケイ皮", "gallic": "没食子", "tannic": "タンニン",
    "ascorbic": "アスコルビン", "deoxyribonucleic": "デオキシリボ核酸",
    "ribonucleic": "リボ核酸", "nicotinic": "ニコチン", "folic": "葉",
    "pantothenic": "パントテン", "orotic": "オロト", "barbituric": "バルビツール",
    "hippuric": "馬尿", "anthranilic": "アントラニル", "sulfanilic": "スルファニル",
    "picric": "ピクリン", "boric": "ホウ", "silicic": "ケイ", "carbonic": "炭",
    "sulfuric": "硫", "sulphuric": "硫", "sulfurous": "亜硫", "nitric": "硝",
    "nitrous": "亜硝", "phosphoric": "リン", "phosphorous": "亜リン",
    "hydrochloric": "塩", "hydrobromic": "臭化水素", "hydrofluoric": "フッ化水素",
    "chloric": "塩素", "perchloric": "過塩素", "chromic": "クロム",
    "permanganic": "過マンガン", "manganic": "マンガン", "arsenic": "ヒ",
    "selenic": "セレン", "telluric": "テルル", "vanadic": "バナジン",
    "molybdic": "モリブデン", "tungstic": "タングステン", "stannic": "スズ",
    "ferric": "鉄", "ferrous": "鉄", "cupric": "銅", "zincic": "亜鉛",
}

# 塩の陰イオン語（語末に来たら先頭へ回す）
ANIONS: dict[str, str] = {
    "chloride": "塩化", "bromide": "臭化", "iodide": "ヨウ化", "fluoride": "フッ化",
    "sulfide": "硫化", "disulfide": "二硫化", "sulfate": "硫酸", "sulfite": "亜硫酸",
    "bisulfate": "硫酸水素", "bisulfite": "亜硫酸水素", "thiosulfate": "チオ硫酸",
    "nitrate": "硝酸", "nitrite": "亜硝酸", "phosphate": "リン酸", "phosphite": "亜リン酸",
    "carbonate": "炭酸", "bicarbonate": "炭酸水素", "hydroxide": "水酸化",
    "oxide": "酸化", "dioxide": "二酸化", "peroxide": "過酸化",
    "cyanide": "シアン化", "thiocyanate": "チオシアン酸", "cyanate": "シアン酸",
    "chlorate": "塩素酸", "perchlorate": "過塩素酸", "chlorite": "亜塩素酸",
    "bromate": "臭素酸", "iodate": "ヨウ素酸", "permanganate": "過マンガン酸",
    "chromate": "クロム酸", "dichromate": "二クロム酸", "manganate": "マンガン酸",
    "silicate": "ケイ酸", "borate": "ホウ酸", "arsenate": "ヒ酸", "arsenite": "亜ヒ酸",
    "selenate": "セレン酸", "selenite": "亜セレン酸", "tellurite": "亜テルル酸",
    "vanadate": "バナジン酸", "molybdate": "モリブデン酸", "tungstate": "タングステン酸",
    "stannate": "スズ酸", "aluminate": "アルミン酸", "zincate": "亜鉛酸",
    "ferrate": "鉄酸", "perrhenate": "過レニウム酸", "rhenate": "レニウム酸",
    "acetate": "酢酸", "formate": "ギ酸", "oxalate": "シュウ酸", "citrate": "クエン酸",
    "tartrate": "酒石酸", "benzoate": "安息香酸", "lactate": "乳酸",
    "salicylate": "サリチル酸", "malate": "リンゴ酸", "succinate": "コハク酸",
    "fumarate": "フマル酸", "maleate": "マレイン酸", "oleate": "オレイン酸",
    "stearate": "ステアリン酸", "palmitate": "パルミチン酸", "propionate": "プロピオン酸",
    "butyrate": "酪酸", "valerate": "吉草酸", "acrylate": "アクリル酸",
    "methacrylate": "メタクリル酸", "phthalate": "フタル酸", "ascorbate": "アスコルビン酸",
    "gluconate": "グルコン酸", "glutamate": "グルタミン酸", "aspartate": "アスパラギン酸",
    "glycinate": "グリシン", "urate": "尿酸", "orotate": "オロト酸",
    "pantothenate": "パントテン酸", "nicotinate": "ニコチン酸", "folate": "葉酸",
    "sulfamate": "スルファミン酸", "carbamate": "カルバミン酸",
    "dithiocarbamate": "ジチオカルバミン酸", "xanthate": "キサントゲン酸",
    "phenoxide": "フェノキシド", "methoxide": "メトキシド", "ethoxide": "エトキシド",
    "hydrogensulfate": "硫酸水素", "hydrogensulfite": "亜硫酸水素",
    "dihydrogenphosphate": "リン酸二水素", "hydrogenphosphate": "リン酸水素",
    "hydrosulfide": "硫化水素", "azide": "アジ化", "amide": "アミド",
    "hydride": "水素化", "borohydride": "水素化ホウ素", "hypochlorite": "次亜塩素酸",
    "hypophosphite": "次亜リン酸", "phosphinate": "ホスフィン酸",
    "sulfonate": "スルホン酸", "sulphate": "硫酸", "sulphite": "亜硫酸",
    "sulphide": "硫化", "methanesulfonate": "メタンスルホン酸",
    "tosylate": "トシル酸", "mesylate": "メシル酸", "triflate": "トリフラート",
    "picrate": "ピクリン酸", "perbromate": "過臭素酸", "periodate": "過ヨウ素酸",
    "hexafluorophosphate": "ヘキサフルオロリン酸", "tetrafluoroborate": "テトラフルオロホウ酸",
    "tetraphenylborate": "テトラフェニルホウ酸", "tetrafluoroborate": "テトラフルオロホウ酸",
}

# -oate 塩（カルボン酸塩など）は OIC_STEMS から自動生成して陰イオン語に加える
for _k, _v in list(OIC_STEMS.items()):
    if _k.endswith("ic"):
        ANIONS.setdefault(_k[:-2] + "ate", _v + "酸")

# 塩の語順判定用：無機塩とみなす単純な語
SIMPLE_WORDS = {
    "sodium", "potassium", "calcium", "magnesium", "barium", "strontium",
    "lithium", "ammonium", "zinc", "iron", "copper", "silver", "aluminum",
    "aluminium", "lead", "tin", "mercury", "manganese", "nickel", "cobalt",
    "chromium", "cadmium", "beryllium", "cesium", "caesium", "rubidium",
    "disodium", "dipotassium", "dicalcium", "hydrogen", "dihydrogen",
    "ferric", "ferrous", "cupric", "cuprous", "stannic", "stannous",
    "methyl", "ethyl", "propyl", "butyl", "dimethyl", "diethyl", "trimethyl",
    "triethyl", "dipropyl", "tripropyl", "dibutyl", "tributyl", "phenyl",
    "benzyl", "vinyl", "allyl", "tetramethylammonium", "tetraethylammonium",
    "tetrabutylammonium", "bisulfate",
}
METAL_WORDS = {
    "sodium", "potassium", "calcium", "magnesium", "barium", "strontium",
    "lithium", "ammonium", "zinc", "iron", "copper", "silver", "aluminum",
    "aluminium", "lead", "tin", "mercury", "manganese", "nickel", "cobalt",
    "chromium", "cadmium", "disodium", "dipotassium", "dicalcium",
    "ferric", "ferrous", "cupric", "cuprous", "tetramethylammonium",
    "tetraethylammonium", "tetrabutylammonium",
}
# リン酸系は有機エステルでは語末に置く（グルコース6-リン酸 型）
PHOSPHATE_FAMILY = {
    "phosphate", "phosphite", "dihydrogenphosphate", "hydrogenphosphate",
    "phosphinate", "hypophosphite", "diphosphate", "triphosphate",
    "pyrophosphate", "monophosphate",
}
ANIONS.update({
    "diphosphate": "二リン酸", "triphosphate": "三リン酸",
    "pyrophosphate": "ピロリン酸", "monophosphate": "一リン酸",
    "thiophosphate": "チオリン酸",
})

# 塩酸塩など、語末に付けたままにする塩
SUFFIX_SALTS: dict[str, str] = {
    "hydrochloride": "塩酸塩", "dihydrochloride": "二塩酸塩",
    "hydrobromide": "臭化水素酸塩", "hydroiodide": "ヨウ化水素酸塩",
    "hydrofluoride": "フッ化水素酸塩", "hemisulfate": "硫酸塩",
}

GREEK: dict[str, str] = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "omicron": "ο",
    "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ",
    "phi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
}

# そのまま通す語（立体記述子など）
KEEP_WORDS = {"tert", "sec", "dl", "d", "l", "r", "s", "e", "z", "n", "o", "m", "p",
              "endo", "exo"}  # endo/exo は辞書にもあるが単独語でも通す

ALL_FRAG = {**FRAGMENTS, **OIC_STEMS}
_KEYS_BY_HEAD: dict[str, list[str]] = {}
for _k in sorted(ALL_FRAG.keys(), key=len, reverse=True):
    _KEYS_BY_HEAD.setdefault(_k[0], []).append(_k)


def convert_run(run: str) -> str | None:
    """英字の連続（小文字化済み）を断片辞書で貪欲に変換。失敗したら None。"""
    out = []
    i = 0
    while i < len(run):
        for key in _KEYS_BY_HEAD.get(run[i], []):
            if run.startswith(key, i):
                out.append(ALL_FRAG[key])
                i += len(key)
                break
        else:
            return None
    return "".join(out)


def convert_word(word: str) -> str | None:
    """ハイフン等で区切られた1語を変換。失敗したら None。"""
    parts = re.split(r"([^A-Za-z]+)", word)
    out = []
    for part in parts:
        if not part:
            continue
        if not part.isalpha():
            out.append(part)
            continue
        low = part.lower()
        if len(part) == 1:
            out.append(part)  # 位置番号・指示水素などの1文字記号はそのまま通す
            continue
        if len(part) == 2 and part.isalpha() and not part.islower() and not part.isupper():
            out.append(part)  # 3aR のような立体記述子（小文字+大文字）はそのまま通す
            continue
        if low in ANIONS:
            out.append(ANIONS[low])
            continue
        if low in SUFFIX_SALTS:
            out.append(SUFFIX_SALTS[low])
            continue
        if low == "salt":
            out.append("塩")
            continue
        if low in GREEK:
            out.append(GREEK[low])
            continue
        if low in KEEP_WORDS and len(low) <= 4:
            out.append(part)  # 原形のまま（DL, tert など）
            continue
        conv = convert_run(low)
        if conv is None:
            return None
        out.append(conv)
    return "".join(out)


def convert_name(name: str) -> str | None:
    """化合物名全体を変換。塩の語順処理を含む。失敗したら None。"""
    if not name or " and " in name.lower():
        return None
    if name.rstrip().endswith("-"):
        return None  # CAS式の逆転表記（末尾に置換基がぶら下がる形）は変換しない

    # 環縮合記述子（[de,g] や [3,2-d] など）は変換せずそのまま保持する
    spans: list[str] = []

    def _keep(m: re.Match) -> str:
        spans.append(m.group(0))
        return f"§{len(spans) - 1}§"

    name = re.sub(r"\[[a-z0-9,.'\-]{1,14}\]", _keep, name)

    result = _convert_name_inner(name)
    if result is None:
        return None
    for i, span in enumerate(spans):
        result = result.replace(f"§{i}§", span)
    return result


def _convert_name_inner(name: str) -> str | None:

    # "dihydrogen phosphate" / "hydrogen phosphate" の句処理
    mph = re.search(r"\b(di)?hydrogen phosphate\b", name, flags=re.I)
    if mph:
        anion = "リン酸二水素" if mph.group(1) else "リン酸水素"
        rest_words = (name[: mph.start()] + name[mph.end() :]).split()
        if rest_words and all(
            w.lower().strip(",;()") in SIMPLE_WORDS for w in rest_words
        ):
            conv_rest = [convert_word(w) for w in rest_words]
            if all(r is not None for r in conv_rest):
                return anion + "".join(r for r in conv_rest if r)
        name = name[: mph.start()] + anion + name[mph.end() :]

    words = name.split()
    if not words:
        return None

    last = words[-1]
    m = re.search(r"([A-Za-z]+)$", last)
    # 末尾の陰イオン語として扱うのは、語そのものが陰イオン語の場合だけ
    # （例: "5-phosphate" は可、"...amino)acetate" のような複合語は不可）
    if m and len(words) >= 2 and re.fullmatch(r"[0-9,.\-()]*", last[: m.start()]):
        tail = m.group(1).lower()
        prefix = last[: m.start()]  # 例: "6-phosphate" の "6-"
        if tail in SUFFIX_SALTS:
            rest = [convert_word(w) for w in words[:-1]]
            if any(r is None for r in rest):
                return None
            return "".join(r for r in rest if r) + prefix + SUFFIX_SALTS[tail]
        if tail in ANIONS:
            rest_words = words[:-1]
            rest_conv = [convert_word(w) for w in rest_words]
            if any(r is None for r in rest_conv):
                return None
            rest_lower = [w.lower().strip(",;()") for w in rest_words]
            is_simple = all(w in SIMPLE_WORDS for w in rest_lower)
            if tail in PHOSPHATE_FAMILY and not is_simple:
                pass  # 有機リン酸エステルは語末のまま通常変換へ
            elif is_simple:
                # 無機塩: 陰イオン + 水素（二水素） + 残り の順
                hydro = "".join(
                    c for w, c in zip(rest_lower, rest_conv) if w in ("hydrogen", "dihydrogen")
                )
                others = "".join(
                    c for w, c in zip(rest_lower, rest_conv) if w not in ("hydrogen", "dihydrogen")
                )
                return ANIONS[tail] + hydro + others
            elif rest_lower[0] in METAL_WORDS and len(words) >= 3:
                # Sodium dodecyl sulfate 型: 中間 + 陰イオン + 金属
                return "".join(rest_conv[1:]) + ANIONS[tail] + rest_conv[0]
            else:
                return ANIONS[tail] + prefix + "".join(rest_conv)

    conv = [convert_word(w) for w in words]
    if any(c is None for c in conv):
        return None
    return "".join(c for c in conv if c)


def first_unknown_fragment(name: str) -> str | None:
    """変換に失敗した名前について、最初に詰まった英字断片を返す（辞書拡張用）。"""
    for word in name.split():
        if convert_word(word) is not None:
            continue
        for part in re.split(r"[^A-Za-z]+", word):
            if not part:
                continue
            low = part.lower()
            if len(low) <= 1:
                continue
            if low in ANIONS or low in SUFFIX_SALTS or low in GREEK or low == "salt":
                continue
            if low in KEEP_WORDS and len(low) <= 4:
                continue
            # 断片辞書で進めるところまで進み、詰まった位置から先を返す
            i = 0
            stuck = False
            while i < len(low):
                matched = False
                for key in _KEYS_BY_HEAD.get(low[i], []):
                    if low.startswith(key, i):
                        i += len(key)
                        matched = True
                        break
                if not matched:
                    stuck = True
                    break
            if stuck:
                return low[i : i + 14]
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = dblayer.connect()
    try:
        rows = con.execute(
            "SELECT id, name_en FROM compounds "
            "WHERE (name_ja IS NULL OR name_ja='') AND name_en IS NOT NULL AND name_en != ''"
        ).fetchall()
        print(f"candidates: {len(rows)}")

        converted: list[tuple[int, str, str]] = []
        failed_fragments: Counter = Counter()
        for row in rows:
            result = convert_name(row["name_en"])
            if result:
                converted.append((row["id"], row["name_en"], result))
            else:
                frag = first_unknown_fragment(row["name_en"])
                if frag:
                    failed_fragments[frag] += 1

        print(f"convertible: {len(converted)} / {len(rows)}")
        print("sample conversions:")
        for _, en, ja in converted[:15]:
            print(f"  {en} -> {ja}")
        print("top unconverted fragments:")
        for seg, cnt in failed_fragments.most_common(40):
            print(f"  {seg}: {cnt}")

        if args.apply:
            cols = [r[1] for r in con.execute("PRAGMA table_info(compounds)").fetchall()]
            if "name_ja_generated" not in cols:
                con.execute("ALTER TABLE compounds ADD COLUMN name_ja_generated INTEGER DEFAULT 0")
            for cid_, _en, ja in converted:
                con.execute(
                    "UPDATE compounds SET name_ja=?, name_ja_generated=1 WHERE id=? AND (name_ja IS NULL OR name_ja='')",
                    (ja, cid_),
                )
            con.commit()
            total = con.execute("SELECT COUNT(*) FROM compounds WHERE name_ja IS NOT NULL AND name_ja != ''").fetchone()[0]
            gen = con.execute("SELECT COUNT(*) FROM compounds WHERE name_ja_generated=1").fetchone()[0]
            print(f"applied. name_ja total: {total} (generated: {gen})")
    finally:
        con.close()


if __name__ == "__main__":
    main()
