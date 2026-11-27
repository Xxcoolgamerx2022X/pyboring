print("pyscript.net is UP: Hosted on 'https://xxcoolgamerx2022x.github.io/pyboring/' (all rights reserved)")
print("Type commands in the terminal below.")

"""A small, browser-safe shell backed by an in-memory virtual filesystem.

This intentionally does not execute operating-system commands or access the
host filesystem/network. Files created here last only until the page reloads.
"""

import ast
import datetime
import operator
import posixpath
import shlex


FILESYSTEM = {
    "/": None,
    "/home": None,
    "/home/pyodide": None,
    "/home/pyodide/README.txt": (
        "Welcome to the PyScript web shell!\n"
        "This is a safe, in-memory filesystem. Try 'help' to see commands.\n"
    ),
    "/tmp": None,
    "/workspace": None,
}
HOME = "/home/pyodide"
CURRENT_DIR = HOME
COMMAND_HISTORY = []

HELP = {
    "help": "help [command]                 Show help for every command or one command.",
    "pwd": "pwd                            Print the current virtual directory.",
    "ls": "ls [-a] [path]                 List files and directories.",
    "cd": "cd [path]                      Change virtual directory (default: home).",
    "tree": "tree [path]                    Show the virtual directory tree.",
    "cat": "cat <file>...                  Print one or more virtual files.",
    "write": "write <file> <text>            Create/replace a file with text.",
    "touch": "touch <file>...                Create empty files.",
    "mkdir": "mkdir [-p] <dir>...             Create virtual directories.",
    "rm": "rm [-r] <path>...                Remove virtual files/directories (never host files).",
    "cp": "cp <source> <destination>       Copy a virtual file.",
    "mv": "mv <source> <destination>       Move/rename a virtual file or directory.",
    "find": "find [path]                     List paths below a virtual directory.",
    "grep": "grep <text> <file>...            Find lines containing text in virtual files.",
    "head": "head [-n count] <file>            Show the first lines of a virtual file.",
    "tail": "tail [-n count] <file>            Show the last lines of a virtual file.",
    "wc": "wc <file>...                    Count lines, words, and characters.",
    "echo": "echo [text...]                  Print text.",
    "clear": "clear                           Clear the terminal when ANSI is supported.",
    "history": "history                         Show commands entered in this session.",
    "date": "date                            Show the current date and time.",
    "whoami": "whoami                          Print the simulated username.",
    "uname": "uname                           Show information about this web shell.",
    "env": "env                             Show a few simulated environment values.",
    "calc": "calc <expression>               Safely calculate basic arithmetic.",
    "about": "about                           Explain the shell's browser-safe limits.",
    "exit": "exit                            End the shell session.",
    "quit": "quit                            Alias for exit.",
}


def resolve_path(path):
    """Resolve a user path inside the virtual filesystem."""
    if not path or path == "~":
        path = HOME
    elif path.startswith("~/"):
        path = posixpath.join(HOME, path[2:])
    elif not path.startswith("/"):
        path = posixpath.join(CURRENT_DIR, path)
    return posixpath.normpath(path)


def is_directory(path):
    return path in FILESYSTEM and FILESYSTEM[path] is None


def is_file(path):
    return path in FILESYSTEM and FILESYSTEM[path] is not None


def children(path, include_hidden=False):
    prefix = "/" if path == "/" else path.rstrip("/") + "/"
    found = {}
    for item in FILESYSTEM:
        if item == path or not item.startswith(prefix):
            continue
        remainder = item[len(prefix):]
        if not remainder:
            continue
        name = remainder.split("/", 1)[0]
        if not include_hidden and name.startswith("."):
            continue
        child_path = posixpath.join(path, name) if path != "/" else "/" + name
        found[name] = child_path
    return sorted(found.items(), key=lambda pair: (not is_directory(pair[1]), pair[0].lower()))


def require_file(path):
    if not is_file(path):
        if is_directory(path):
            print("{}: is a directory".format(path))
        else:
            print("{}: no such file".format(path))
        return False
    return True


def command_ls(args):
    include_hidden = "-a" in args
    paths = [arg for arg in args if arg != "-a"] or ["."]
    for raw_path in paths:
        path = resolve_path(raw_path)
        if is_file(path):
            print(posixpath.basename(path))
        elif not is_directory(path):
            print("ls: cannot access '{}': no such path".format(raw_path))
        else:
            if len(paths) > 1:
                print("{}:".format(raw_path))
            entries = children(path, include_hidden)
            if entries:
                print("  ".join(name + ("/" if is_directory(child) else "")
                                 for name, child in entries))
            if len(paths) > 1:
                print()


def command_tree(path, prefix=""):
    entries = children(path, include_hidden=True)
    for index, (name, child) in enumerate(entries):
        last = index == len(entries) - 1
        print(prefix + ("└── " if last else "├── ") + name + ("/" if is_directory(child) else ""))
        if is_directory(child):
            command_tree(child, prefix + ("    " if last else "│   "))


def mkdir_one(path, parents=False):
    if path == "/":
        return True
    if path in FILESYSTEM:
        print("mkdir: '{}': already exists".format(path))
        return False
    parent = posixpath.dirname(path) or "/"
    if parent not in FILESYSTEM:
        if not parents:
            print("mkdir: '{}': parent directory does not exist (use -p)".format(path))
            return False
        if not mkdir_one(parent, parents=True):
            return False
    if not is_directory(parent):
        print("mkdir: '{}': parent is not a directory".format(path))
        return False
    FILESYSTEM[path] = None
    return True


def remove_path(path, recursive=False):
    if path not in FILESYSTEM:
        print("rm: '{}': no such path".format(path))
        return
    if path == "/":
        print("rm: refusing to remove the virtual root")
        return
    if is_directory(path):
        descendants = [item for item in FILESYSTEM if item.startswith(path.rstrip("/") + "/")]
        if descendants and not recursive:
            print("rm: '{}': directory is not empty (use -r)".format(path))
            return
        if CURRENT_DIR == path or CURRENT_DIR.startswith(path.rstrip("/") + "/"):
            print("rm: cannot remove the current directory or one of its parents")
            return
        for item in sorted(descendants, key=len, reverse=True):
            del FILESYSTEM[item]
    del FILESYSTEM[path]


def safe_calculate(expression):
    """Evaluate arithmetic syntax only; never use Python eval()."""
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.Num):  # Compatibility with older Python versions.
            return node.n
        if isinstance(node, ast.UnaryOp) and type(node.op) in operators:
            return operators[type(node.op)](visit(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("exponent is too large")
            result = operators[type(node.op)](left, right)
            if isinstance(result, (int, float)) and abs(result) > 1e100:
                raise ValueError("result is too large")
            return result
        raise ValueError("only numeric literals and +, -, *, /, //, %, ** are allowed")

    return visit(ast.parse(expression, mode="eval"))


def run_command(command_line):
    global CURRENT_DIR
    try:
        args = shlex.split(command_line)
    except ValueError as error:
        print("parse error: {}".format(error))
        return True
    if not args:
        return True

    COMMAND_HISTORY.append(command_line)
    name, argv = args[0], args[1:]

    if name in ("exit", "quit"):
        print("Goodbye!")
        return False
    if name == "help":
        if argv:
            key = argv[0]
            print(HELP.get(key, "No help available for '{}'. Try 'help'.".format(key)))
        else:
            print("Available commands (virtual/browser-safe shell):")
            for key in sorted(HELP):
                print("  " + HELP[key])
        return True
    if name == "pwd":
        print(CURRENT_DIR)
    elif name == "ls":
        command_ls(argv)
    elif name == "cd":
        target = resolve_path(argv[0]) if argv else HOME
        if is_directory(target):
            CURRENT_DIR = target
        else:
            print("cd: '{}': no such directory".format(argv[0] if argv else target))
    elif name == "tree":
        target = resolve_path(argv[0]) if argv else CURRENT_DIR
        if not is_directory(target):
            print("tree: '{}': not a directory".format(target))
        else:
            print(target + ("/" if target != "/" else ""))
            command_tree(target)
    elif name == "echo":
        print(" ".join(argv))
    elif name == "cat":
        if not argv:
            print("usage: cat <file>...")
        for raw in argv:
            path = resolve_path(raw)
            if require_file(path):
                print(FILESYSTEM[path], end="" if FILESYSTEM[path].endswith("\n") else "\n")
    elif name == "write":
        if len(argv) < 2:
            print("usage: write <file> <text>")
        else:
            path = resolve_path(argv[0])
            parent = posixpath.dirname(path) or "/"
            if not is_directory(parent):
                print("write: parent directory does not exist")
            elif is_directory(path):
                print("write: '{}' is a directory".format(path))
            else:
                FILESYSTEM[path] = " ".join(argv[1:]) + "\n"
    elif name == "touch":
        if not argv:
            print("usage: touch <file>...")
        for raw in argv:
            path = resolve_path(raw)
            parent = posixpath.dirname(path) or "/"
            if not is_directory(parent):
                print("touch: '{}': parent directory does not exist".format(raw))
            elif is_directory(path):
                print("touch: '{}': is a directory".format(raw))
            elif path not in FILESYSTEM:
                FILESYSTEM[path] = ""
    elif name == "mkdir":
        parents = "-p" in argv
        paths = [item for item in argv if item != "-p"]
        if not paths:
            print("usage: mkdir [-p] <dir>...")
        for raw in paths:
            mkdir_one(resolve_path(raw), parents)
    elif name == "rm":
        recursive = "-r" in argv or "-rf" in argv
        paths = [item for item in argv if item not in ("-r", "-f", "-rf")]
        if not paths:
            print("usage: rm [-r] <path>...")
        for raw in paths:
            remove_path(resolve_path(raw), recursive)
    elif name in ("cp", "mv"):
        if len(argv) != 2:
            print("usage: {} <source> <destination>".format(name))
        else:
            source, destination = resolve_path(argv[0]), resolve_path(argv[1])
            if not is_file(source) and not is_directory(source):
                print("{}: source does not exist".format(name))
            elif is_directory(source):
                print("{}: directory operations are not supported".format(name))
            else:
                if is_directory(destination):
                    destination = posixpath.join(destination, posixpath.basename(source))
                if not is_directory(posixpath.dirname(destination) or "/"):
                    print("{}: destination parent does not exist".format(name))
                elif is_directory(destination):
                    print("{}: destination is a directory".format(name))
                else:
                    FILESYSTEM[destination] = FILESYSTEM[source]
                    if name == "mv":
                        del FILESYSTEM[source]
    elif name == "find":
        target = resolve_path(argv[0]) if argv else CURRENT_DIR
        if not is_directory(target):
            print("find: '{}': not a directory".format(target))
        else:
            print(target)
            for item in sorted(FILESYSTEM):
                if item.startswith(target.rstrip("/") + "/"):
                    print(item)
    elif name == "grep":
        if len(argv) < 2:
            print("usage: grep <text> <file>...")
        else:
            needle = argv[0]
            for raw in argv[1:]:
                path = resolve_path(raw)
                if require_file(path):
                    for number, line in enumerate(FILESYSTEM[path].splitlines(), 1):
                        if needle in line:
                            print("{}:{}:{}".format(raw, number, line))
    elif name in ("head", "tail"):
        count = 10
        remaining = list(argv)
        if len(remaining) >= 2 and remaining[0] == "-n":
            try:
                count = max(0, int(remaining[1]))
            except ValueError:
                print("{}: line count must be an integer".format(name))
                return True
            remaining = remaining[2:]
        if len(remaining) != 1:
            print("usage: {} [-n count] <file>".format(name))
        else:
            path = resolve_path(remaining[0])
            if require_file(path):
                lines = FILESYSTEM[path].splitlines()
                selected = lines[:count] if name == "head" else (lines[-count:] if count else [])
                for line in selected:
                    print(line)
    elif name == "wc":
        if not argv:
            print("usage: wc <file>...")
        for raw in argv:
            path = resolve_path(raw)
            if require_file(path):
                text = FILESYSTEM[path]
                print("{} {} {} {}".format(len(text.splitlines()), len(text.split()), len(text), raw))
    elif name == "history":
        for index, entry in enumerate(COMMAND_HISTORY, 1):
            print("{:>4}  {}".format(index, entry))
    elif name == "date":
        print(datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
    elif name == "whoami":
        print("pyodide")
    elif name == "uname":
        print("PyScript Web Shell (simulated browser environment)")
    elif name == "env":
        print("HOME={}".format(HOME))
        print("PWD={}".format(CURRENT_DIR))
        print("SHELL=pyboring-web-shell")
    elif name == "calc":
        if not argv:
            print("usage: calc <arithmetic expression>")
        else:
            try:
                print(safe_calculate(" ".join(argv)))
            except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError) as error:
                print("calc: {}".format(error))
    elif name == "clear":
        print("\033[2J\033[H", end="")
    elif name == "about":
        print("A lightweight shell simulation running in the browser.")
        print("Files live only in this page's memory. No OS commands, host files, or network access are exposed.")
    else:
        print("{}: command not found. Type 'help' for available commands.".format(name))
    return True


while True:
    try:
        command = input("{} $ ".format(CURRENT_DIR))
        if not run_command(command):
            break
    except EOFError:
        print("Terminal input is unavailable. Reload the page and keep this tab in focus.")
        break
    except KeyboardInterrupt:
        print("\nUse 'exit' to leave the shell.")
    except Exception as error:
        # Keep a bad command from terminating the interactive shell.
        print("shell error: {}".format(error))
