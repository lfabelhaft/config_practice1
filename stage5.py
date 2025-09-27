import os
import argparse
import shlex
import sys
import json
import base64
import fnmatch
import copy

def default_vfs():
    return {
        "type": "dir",
        "mode": "rwxr-xr-x",
        "children": {
            "home": {
                "type": "dir", "mode": "rwxr-xr-x", "children": {
                    "user": {
                        "type": "dir", "mode": "rwxr-xr-x", "children": {
                            "file.txt": {"type": "file", "mode": "rw-r--r--", "content": "Hello VFS"}
                        }
                    }
                }
            },
            "tmp": {"type": "dir", "mode": "rwxrwxrwt", "children": {}}
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
        # decode base64 where present
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

    def path_to_parent_and_name(self, path_list):
        if not path_list:
            return None, None
        parent = self.root
        for comp in path_list[:-1]:
            parent = parent.get("children", {}).get(comp)
            if parent is None:
                return None, None
            if parent.get("type") != "dir":
                return None, None
        return parent, path_list[-1]

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

    def chmod(self, path_list, mode_str):
        node = self.path_to_node(path_list)
        if node is None:
            raise FileNotFoundError("No such file or directory")
        node["mode"] = mode_str

    def cp(self, src_list, dst_list):
        src_node = self.path_to_node(src_list)
        if src_node is None:
            raise FileNotFoundError("Source not found")
        dst_parent, dst_name = self.path_to_parent_and_name(dst_list)
        if dst_parent is None:
            raise FileNotFoundError("Destination parent not found")
        # if dst exists and is dir -> copy into dir with same basename
        existing = dst_parent.get("children", {}).get(dst_name)
        if existing and existing.get("type") == "dir" and src_node.get("type") == "dir":
            # copy src into this directory with same basename
            # choose new name = src basename
            new_name = src_list[-1]
            dst_parent = existing
            dst_name = new_name
        # create deep copy of node
        new_node = copy.deepcopy(src_node)
        # insert
        dst_parent.setdefault("children", {})[dst_name] = new_node

    def vfs_init_default(self):
        self.root = default_vfs()
        self.cwd = []

def expand_vars(s: str) -> str:
    return os.path.expandvars(s)

def pretty_path(vfs: VFS, path_list):
    return "/" + "/".join(path_list)

def handle_cmd(vfs: VFS, tokens):
    if not tokens:
        return False
    cmd = tokens[0]
    args = tokens[1:]
    try:
        if cmd == "exit":
            return True
        elif cmd == "ls":
            target = args[0] if args else "."
            path_list = vfs.path_list_from_str(target) if target != "." else vfs.cwd
            try:
                items = vfs.list_dir(path_list)
                for name, node in items:
                    typ = node.get("type")
                    mode = node.get("mode", "")
                    print(f"{mode}\t{'d' if typ=='dir' else '-'}\t{name}")
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
            if len(args) >= 3 and args[1] == "-name":
                start = args[0]
                pattern = args[2]
                start_list = vfs.path_list_from_str(start) if start != "." else vfs.cwd
                res = vfs.find(start_list, pattern)
                for r in res:
                    print(r)
            else:
                print("find: usage: find <path> -name <pattern>")
        elif cmd == "chmod":
            if len(args) != 2:
                print("chmod: usage: chmod <mode> <path>")
            else:
                mode_str = args[0]
                path = args[1]
                path_list = vfs.path_list_from_str(path) if path != "/" else []
                vfs.chmod(path_list, mode_str)
        elif cmd == "cp":
            if len(args) != 2:
                print("cp: usage: cp <src> <dst>")
            else:
                src = args[0]
                dst = args[1]
                src_list = vfs.path_list_from_str(src) if src != "/" else []
                dst_list = vfs.path_list_from_str(dst) if dst != "/" else []
                vfs.cp(src_list, dst_list)
        elif cmd == "vfs-init":
            vfs.vfs_init_default()
            print("VFS reset to default (in-memory).")
        else:
            print(f"Unknown command: {cmd}")
    except Exception as e:
        print(f"{cmd}: {e}")
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
                    print("Script interrupted by exit.")
                    return
    except FileNotFoundError:
        print(f"Start script not found: {path}")


def main():
    parser = argparse.ArgumentParser(description="Эмулятор оболочки — этап 5 (chmod, cp)")
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
