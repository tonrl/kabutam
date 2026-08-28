import sys
import time


def show_spinner(stop_event, current_ref, total, status_ref):
    if not sys.stderr.isatty():
        return
    symbols = ["⠉⠉", "⠈⠙", "⠀⠹", "⠀⢸", "⠀⣰", "⢀⣠", "⣀⣀", "⣄⡀", "⣆⠀", "⡇⠀", "⠏⠀", "⠋⠁"]

    i = 0

    while not stop_event.is_set():
        current = current_ref[0] if current_ref else 0
        status = status_ref[0]
        if status:
            message = status
        else:
            message = " 処理中..."
        if total is not None:
            counter_str = f"({current} / {total}) "
        else:
            counter_str = ""

        print(
            f"\r\033[K {symbols[i % len(symbols)]} {counter_str}{message} ",
            end="",
            flush=True,
            file=sys.stderr,
        )

        i += 1
        time.sleep(0.1)
    print("\r\033[K", end="", flush=True, file=sys.stderr)
