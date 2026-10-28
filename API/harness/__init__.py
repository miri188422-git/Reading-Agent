"""API harness. Every runtime action is printed with the file that performed it."""


def say(file: str, msg: str) -> None:
    print(f"[{file}] {msg}")