import os
import argparse
import shlex
import sys
import json
import base64

VFS_NAME = "VFS"

def default_vfs():
    return {
        "type": "dir",
        "mode": "rwxr-xr-x",
        "children": {
            "home": {
                "type": "dir",
                "mode": "rwxr-xr-x",
                "children": {
                    "user": {
                        "type": "dir",
                        "mode": "rwxr-xr-x",
                        "children": {
                            "readme.txt": {"type": "file", "mode": "rw-r--r--", "content": "Это VFS readme.\n"},
                            "binfile.bin": {"type": "file", "mode": "rw-------", "content_b64": base64.b64encode(b"\x00\x01\x02").decode()}
                        }
                    }
                }
            },
            "etc": {"type": "dir", "mode": "rwxr-xr-x", "children": {}},
            "var": {"type": "dir", "mode": "rwxr-xr-x", "children": {}}
        }
    }

class VFS:
    def __init__(self, root=None, name="VFS"):
        self.name = name
        self.root = root if root is not None else default_vfs()
        self.cwd = []  # path as list of components relative to root

    @staticmethod
    def load_from_json(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # В базовом варианте предполагаем, что структура уже соответствует внутреннему формату
        # Конвертируем content_b64 -> content (bytes) for files where present
        def rec(node):
            if node.get("type") == "file":
                if "content_b64" in node:
                    node["content_bytes"] = base64.b64decode(node["content_b64"])
                else:
                    node["content"] = node.get("content", "")
            elif node.get("type") == "dir":
                ch = node.get("children", {})
                for name, child in ch.items():
                    rec(child)
        rec(raw)
        return raw

    def path_to_node(self, path_list):
        node = self.root
        for comp in path_list:
            if node.get("type") != "dir":
                return None
            node = node.get("children", {}).get(comp)
            if node is None:
                return None
        return node

    def list_dir(self, path_list):
        node = self.path_to_node(path_list)
        if node is None:
            raise FileNotFoundError("No such directory")
        if node.get("type") != "dir":
            raise NotADirectoryError("Not a directory")
        return list(node.get("children", {}).items())

    def change_dir(self, target):
        # target: path string absolute (/a/b) or relative (../x)
        comps = [c for c in target.split("/") if c != ""]
        new = self.cwd.copy()
        if target.startswith("/"):
            new = []
        for comp in comps:
            if comp == ".":
                continue
            if comp == "..":
                if new:
                    new.pop()
                continue
            # descend
            node = self.path_to_node(new)
            if node is None:
                raise FileNotFoundError("Path does not exist")
            child = node.get("children", {}).get(comp)
            if child is None or child.get("type") != "dir":
                raise NotADirectoryError(f"{comp} is not a directory")
            new.append(comp)
        self.cwd = new

    def cwd_path(self):
        return "/" + "/".join(self.cwd)

    def vfs_init_default(self):
        self.root = default_vfs()
        self.cwd = []

def expand_vars(s: str) -> str:
    return os.path.expandvars(s)

def handle_cmd(vfs: VFS, tokens):
    if not tokens:
        return False
    cmd = tokens[0]
    args = tokens[1:]
    if cmd == "exit":
        print("exit")
        return True
    elif cmd == "ls":
        target = args[0] if args else "."
        # resolve target relative to cwd
        if target == ".":
            path_list = vfs.cwd
        else:
            if target.startswith("/"):
                path_list = [c for c in target.split("/") if c]
            else:
                path_list = vfs.cwd + [c for c in target.split("/") if c]
        try:
            items = vfs.list_dir(path_list)
            for name, node in items:
                typ = node.get("type")
                print(f"{name}/" if typ == "dir" else name)
        except Exception as e:
            print(f"ls: {e}")
    elif cmd == "cd":
        target = args[0] if args else "/home/user"
        try:
            vfs.change_dir(target)
        except Exception as e:
            print(f"cd: {e}")
    elif cmd == "vfs-init":
        vfs.vfs_init_default()
        print("VFS заменён на VFS по умолчанию (в памяти). Физическое представление очищено.")
    elif cmd == "echo":
        print(" ".join(args))
    else:
        print(f"Unknown or unsupported command at this stage: {cmd}")
    return False

def run_script(path, vfs):
    print(f"--- Выполнение стартового скрипта {path} ---")
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.rstrip("\n")
                if raw.strip() == "" or raw.lstrip().startswith("#"):
                    print(raw)
                    continue
                print(f"{vfs.name}> {raw}")
                expanded = expand_vars(raw)
                try:
                    tokens = shlex.split(expanded)
                except ValueError as e:
                    print(f"Parse error: {e}")
                    continue
                if handle_cmd(vfs, tokens):
                    print("Скрипт прерван командой exit.")
                    return
    except FileNotFoundError:
        print(f"Start script not found: {path}")

def main():
    parser = argparse.ArgumentParser(description="Эмулятор оболочки — этап 3 (VFS in-memory)")
    parser.add_argument("--vfs-path", help="Путь к JSON-файлу VFS", default=None)
    parser.add_argument("--start-script", help="Путь к стартовому скрипту", default=None)
    args = parser.parse_args()

    # Debug: показать параметры
    print("DEBUG: параметры запуска:")
    for k, v in vars(args).items():
        print(f"  {k}: {v}")

    if args.vfs_path:
        try:
            root = VFS.load_from_json(args.vfs_path)
            vfs = VFS(root=root, name=os.path.basename(args.vfs_path) or VFS_NAME)
            print(f"VFS загружён из {args.vfs_path}")
        except Exception as e:
            print(f"Не удалось загрузить VFS из {args.vfs_path}: {e}")
            print("Создаётся VFS по умолчанию.")
            vfs = VFS(name=VFS_NAME)
    else:
        vfs = VFS(name=VFS_NAME)
        print("VFS: использован VFS по умолчанию (в памяти).")

    if args.start_script:
        run_script(args.start_script, vfs)

    # интерактивный режим
    while True:
        try:
            raw = input(f"{vfs.name}:{vfs.cwd_path()}$ ")
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
        if handle_cmd(vfs, tokens):
            break

if __name__ == "__main__":
    main()
