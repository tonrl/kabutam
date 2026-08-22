# kabutam

Terminal-based stock and portfolio tracking tool for Japanese stocks.

## Features
- Fetch and manage Japanese stock data
- Track your portfolio directly from the terminal
- Lightweight and easy to use

## Prerequisites
- Python 3.9 or later
- pass (パスワード管理ツール: 認証情報の管理に利用)
- Git (ソースからのインストール時)


## Installation

### For Arch Linux (via AUR)

#### AUR ヘルパーを使用する場合 (推奨)
```bash
yay -S kabutam
# または
paru -S kabutam
```
#### PKGBUILDからビルドする場合
```bash
git clone https://aur.archlinux.org/kabutam.git
cd kabutam
makepkg -si
```

### For Development (Virtual Environment)

```bash
git clone https://codeberg.org/tonrl/kabutam.git
cd kabutam
python -m venv .venv
source .venv/bin/activate
pip install -e .
```
## Configuration

このツールは、EDINET等のAPIキーの管理にパスワードマネージャー (`pass`) を使用します。
事前に各公式サイト（[J-Quants](https://jpx-jquants.com/) / [EDINET DB](https://edinetdb.jp/)）等でキーを取得し、`pass` コマンドで登録してください

```bash
# J-Quants API キーの登録
pass insert jpx-jquants.com/api/JPX_JQUANTS_API_KEY
# EDINET DB API キーの登録
pass insert ednetdb/api/EDNET_DB_API_KEY
```

## Usage

```bash
# ヘルプの表示
kabutam --help

# 初期化設定
kabutam --init

# 銘柄の検索・表示
kabutam -C 19670

# ポートフォリオ表示
kabutam --portfolio

# ライセンス情報の表示
kabutam --license
```
## Example output
```bash
$ kabutam --portfolio                                                                       7:48 ✔ 
===============================================================================================
ポートフォリオ
===============================================================================================
Code    Company                 Account      Shares     Avg Price         Price           Value
-----------------------------------------------------------------------------------------------
XXXXX   サンプルホールディングス 特定         1,200        190.47        233.80         280,560
XXXXX   テストカンパニー         特定           100      2,401.75      3,002.00         300,200
XXXXX   テストカンパニー         NISA           100      2,300.00      3,002.00         300,200
XXXXX   サンプル電鉄             特定           100      2,708.00      2,959.50         295,950
XXXXX   サンプル通信             NISA           100        144.00        166.10          16,610
-----------------------------------------------------------------------------------------------
取得総額       : 1,292,520 円
保有資産額     : 1,392,520 円
評価損益       : +100,000 円
評価損益率     : +7.74%
===============================================================================================
年間配当金（税引前）: 45,000 円
年間配当金（税引後）: 35,858 円
配当利回り（取得額ベース）: 3.48%
配当利回り（評価額ベース）: 3.23%
===============================================================================================
```
## License
This project is licensed under the GNU General Public License v3.0 or later - see the [LICENSE](LICENSE) file for details.
