import os
import argparse
import shlex
import sys

VFS_NAME = "VFS"

def expand_vars(s: str) -> str:
    return os.path.expandvars(s)

def handle_cmd(tokens):
    if not tokens:
        return False
    cmd = tokens[0]
    args = tokens[1:]
    if cmd == "exit":
        print("exit")
        return True
    elif cmd in ("ls", "cd"):
        print(f"[stub] {cmd} called with args: {args}")
    elif cmd == "echo":
        print(" ".join(args))
    else:
        print(f"Unknown command: {cmd}")
    return False

def run_script(path):
    print(f"--- Выполнение стартового скрипта {path} ---")
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.rstrip("\n")
                if raw.strip() == "" or raw.lstrip().startswith("#"):
                    # комментарий — отображаем, но не выполняем
                    print(raw)
                    continue
                # показываем как будто пользователь ввёл эту строку
                print(f"{VFS_NAME}> {raw}")
                expanded = expand_vars(raw)
                try:
                    tokens = shlex.split(expanded)
                except ValueError as e:
                    print(f"Parse error: {e}")
                    continue
                should_exit = handle_cmd(tokens)
                if should_exit:
                    print("Скрипт прерван командой exit.")
                    return
    except FileNotFoundError:
        print(f"Start script not found: {path}")

def repl():
    while True:
        try:
            raw = input(f"{VFS_NAME}> ")
        except EOFError:
            print()
            break
        raw = raw.strip()
        if raw == "":
            continue
        expanded = expand_vars(raw)
        try:
            tokens = shlex.split(expanded)
        except ValueError as e:
            print(f"Parse error: {e}")
            continue
        if handle_cmd(tokens):
            break

def main():
    parser = argparse.ArgumentParser(description="Эмулятор оболочки — этап 2 (CLI параметры, стартовый скрипт)")
    parser.add_argument("--vfs-path", help="Путь к физическому расположению VFS (для отладки)", default=None)
    parser.add_argument("--start-script", help="Путь к стартовому скрипту", default=None)
    args = parser.parse_args()

    # Отладочный вывод всех параметров (требование этапа 2)
    print("DEBUG: параметры запуска:")
    for k, v in vars(args).items():
        print(f"  {k}: {v}")

    if args.start_script:
        run_script(args.start_script)

    print("Вход в интерактивный режим. Для выхода - exit или Ctrl-D.")
    repl()

if __name__ == "__main__":
    main()
