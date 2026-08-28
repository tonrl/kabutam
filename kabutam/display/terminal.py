from wcwidth import wcswidth

# ------------------------------------------------------------
# 表示テキスト
# ------------------------------------------------------------


def fit_text(text, width):
    """
    端末上でwidthカラムに収まるように文字列を整形する。
    長ければ末尾を…にする。
    """
    text = str(text)

    if wcswidth(text) <= width:
        return text + " " * (width - wcswidth(text))

    result = ""

    for char in text:
        char_width = wcswidth(char)

        if wcswidth(result) + char_width + 1 > width:
            break

        result += char

    return result + "…"


def fit_number(value, width, decimals=1):
    """
    数値を端末表示用に整形する。
    Noneなら '-' を表示する。
    """
    if value is None:
        return f"{'-':>{width}}"

    return f"{value:>{width},.{decimals}f}"
