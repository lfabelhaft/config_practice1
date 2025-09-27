import os
import argparse
import shlex
import sys
import json
import base64
import fnmatch

def default_vfs():
    return {
        "type": "dir",
        "mode": "rwxr-xr-x",
        "children": {
            "a": {"type": "dir", "mode": "rwxr-xr-x", "children": {
                "file1.txt": {"type": "file", "mode": "rw-r--r--", "content": "file1"},
                "b": {"type": "dir", "mode": "rwxr-xr-x", "children": {
                    "file2.log": {"type": "file", "mode": "rw-r--r--", "content": "file2"}
                }}
            }},
            "readme.md": {"type": "file", "mode": "rw-r--r--", "content": "readme"}
        }
    }

class VFS:
    def __init__(self, root=None, name="VFS"):
        self.name = name
        self.root = root if root is not None else default_vfs()
        self.cwd = []

    @staticmethod
    def load_from_json(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        def rec(node):
            if node.get("type") == "file":
                if "content_b64" in node:
                    node["content_bytes"] = base64.b64decode(node["content_b64"])
                else:
                    node["content"] = node.get("content", "")
            elif node.get("type") == "dir":
                for child in node.get("children", {}).values():
                    rec(child)
        rec(raw)
        return raw

    def path_list_from_str(self, pstr):
        if pstr.startswith("/"):
            comps = [c for c in pstr.split("/") if c]
            return comps
        return self.cwd + [c for c in pstr.split("/") if c]

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
        if target == "":
            return
        if target.startswith("/"):
            comps = [c for c in target.split("/") if c]
            new = []
        else:
            comps = [c for c in target.split("/") if c]
            new = self.cwd.copy()
        for c in comps:
            if c == ".":
                continue
            if c == "..":
                if new:
                    new.pop()
                continue
            node = self.path_to_node(new)
            if node is None:
                raise FileNotFoundError("Path does not exist")
            child = node.get("children", {}).get(c)
            if child is None or child.get("type") != "dir":
                raise NotADirectoryError(f"{c} is not a directory")
            new.append(c)
        self.cwd = new

    def cwd_path(self):
        return "/" + "/".join(self.cwd)

    def find(self, start_path_list, pattern):
        start_node = self.path_to_node(start_path_list)
        if start_node is None:
            raise FileNotFoundError("Start path not found")
        results = []
        def rec(node, path_prefix):
            if node.get("type") == "dir":
                for name, child in node.get("children", {}).items():
                    p = path_prefix + [name]
                    if fnmatch.fnmatch(name, pattern):
                        results.append("/" + "/".join(p))
                    rec(child, p)
        rec(start_node, start_path_list.copy())
        return results

def expand_vars(s: str) -> str:
    return os.path.expandvars(s)

def handle_cmd(vfs: VFS, tokens):
    if not tokens:
        return False
    cmd = tokens[0]
    args = tokens[1:]
    if cmd == "exit":
        return True
    elif cmd == "ls":
        target = args[0] if args else "."
        try:
            path_list = vfs.path_list_from_str(target) if target != "." else vfs.cwd
            items = vfs.list_dir(path_list)
            for name, node in items:
                typ = node.get("type")
                print(f"{name}/" if typ == "dir" else name)
        except Exception as e:
            print(f"ls: {e}")
    elif cmd == "cd":
        target = args[0] if args else "/"
        try:
            vfs.change_dir(target)
        except Exception as e:
            print(f"cd: {e}")
    elif cmd == "echo":
        print(" ".join(args))
    elif cmd == "find":
        if not args:
            print("find: usage: find <path> -name <pattern>")
            return False
        if len(args) >= 3 and args[1] == "-name":
            start = args[0]
            pattern = args[2]
            try:
                start_list = vfs.path_list_from_str(start) if start != "." else vfs.cwd
                res = vfs.find(start_list, pattern)
                for r in res:
                    print(r)
            except Exception as e:
                print(f"find: {e}")
        else:
            print("find: unsupported arguments (supported: find <path> -name <pattern>)")
    else:
        print(f"Unknown command: {cmd}")
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
                print(f"{vfs.name}:{vfs.cwd_path()}$ {raw}")
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
    parser = argparse.ArgumentParser(description="Эмулятор оболочки — этап 4 (ls, cd, echo, find)")
    parser.add_argument("--vfs-path", help="Путь к JSON-файлу VFS", default=None)
    parser.add_argument("--start-script", help="Путь к стартовому скрипту", default=None)
    args = parser.parse_args()

    print("DEBUG: параметры запуска:")
    for k, v in vars(args).items():
        print(f"  {k}: {v}")

    if args.vfs_path:
        try:
            root = VFS.load_from_json(args.vfs_path)
            vfs = VFS(root=root, name=os.path.basename(args.vfs_path) or "VFS")
            print(f"VFS загружён из {args.vfs_path}")
        except Exception as e:
            print(f"Не удалось загрузить VFS: {e}")
            vfs = VFS()
    else:
        vfs = VFS()

    if args.start_script:
        run_script(args.start_script, vfs)

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
