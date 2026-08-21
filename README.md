# kabutam

Terminal-based stock and portfolio tracking tool for Japanese stocks.

## Features
- Fetch and manage Japanese stock data
- Track your portfolio directly from the terminal
- Lightweight and easy to use

## Installation

### For Arch Linux (via PKGBUILD)
```bash
makepkg -si
```

### For Development (Virtual Environment)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```
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

## License
This project is licensed under the GNU General Public License v3.0 or later - see the [LICENSE](LICENSE) file for details.
