import os
import shlex

VFS_NAME = "VFS"  # показывается в приглашении

def expand_vars(s: str) -> str:
    # Подстановка переменных окружения: $HOME, ${USER} и т.п.
    return os.path.expandvars(s)

def handle_cmd(tokens):
    if not tokens:
        return
    cmd = tokens[0]
    args = tokens[1:]
    if cmd == "exit":
        print("exit")
        raise SystemExit(0)
    elif cmd in ("ls", "cd"):
        # заглушки: просто выводят имя и аргументы
        print(f"[stub] {cmd} called with args: {args}")
    else:
        print(f"Unknown command: {cmd}")

def repl():
    while True:
        try:
            raw = input(f"{VFS_NAME}> ")
        except EOFError:
            print()
            break
        # предварительная обработка
        raw = raw.strip()
        if raw == "":
            continue
        # expand variables inside the whole line
        expanded = expand_vars(raw)
        try:
            tokens = shlex.split(expanded)
        except ValueError as e:
            print(f"Parse error: {e}")
            continue
        try:
            handle_cmd(tokens)
        except SystemExit:
            break
        except Exception as e:
            print(f"Error executing command: {e}")

if __name__ == "__main__":
    print("Мини-REPL эмулятора (Этап 1). Поддерживается $VAR подстановка.")
    print("Команды-заглушки: ls, cd. Для выхода: exit (или Ctrl-D).")
    repl()
