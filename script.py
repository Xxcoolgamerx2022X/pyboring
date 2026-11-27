
import sys
import os
import shlex
import asyncio
from datetime import datetime
from js import document
from pyodide.ffi import create_proxy


# ============================================================
# terminal output
# ============================================================

terminal = document.getElementById("terminal")
command_input = document.getElementById("command")


class TerminalWriter:
    def write(self, text):
        if not text:
            return 0

        terminal.textContent += str(text)
        terminal.scrollTop = terminal.scrollHeight
        return len(text)

    def flush(self):
        pass

    def isatty(self):
        return True


sys.stdout = TerminalWriter()
sys.stderr = TerminalWriter()


def clear_screen():
    terminal.textContent = ""


# ============================================================
# virtual filesystem
# ============================================================

class File:
    def __init__(self, content=""):
        self.content = content


class Directory:
    def __init__(self):
        self.entries = {}


root = Directory()
cwd = "/"

def get_path(path):
    if not path:
        return cwd

    if path.startswith("/"):
        parts = []
    else:
        parts = [p for p in cwd.split("/") if p]

    for part in path.split("/"):
        if part in ("", "."):
            continue
        elif part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)

    return "/" + "/".join(parts)


def resolve(path):
    path = get_path(path)

    if path == "/":
        return root

    current = root

    for part in path.strip("/").split("/"):
        if not isinstance(current, Directory):
            return None

        current = current.entries.get(part)

        if current is None:
            return None

    return current


def parent_directory(path):
    path = get_path(path)
    parent = os.path.dirname(path)
    name = os.path.basename(path)

    if not parent:
        parent = "/"

    return resolve(parent), name


def make_directory(path):
    parent, name = parent_directory(path)

    if not isinstance(parent, Directory):
        return False

    if name in parent.entries:
        return False

    parent.entries[name] = Directory()
    return True


def make_file(path, content=""):
    parent, name = parent_directory(path)

    if not isinstance(parent, Directory):
        return False

    parent.entries[name] = File(content)
    return True


def seed_filesystem():
    make_directory("/bin")
    make_directory("/dev")
    make_directory("/etc")
    make_directory("/home")
    make_directory("/home/root")
    make_directory("/proc")
    make_directory("/tmp")
    make_directory("/var")
    make_directory("/var/log")

    make_file("/etc/hostname", "elks")
    make_file("/etc/issue", "ELKS 0.9.2")
    make_file("/etc/os-release",
              "NAME=ELKS\nVERSION=0.9.2\n")
    make_file("/var/log/boot.log", "ELKS boot log\n")
    make_file("/home/root/readme.txt",
              "Welcome to ELKS.\n")


seed_filesystem()


# ============================================================
# kernel / system state
# ============================================================

hostname = "elks"
username = "root"
kernel_version = "0.9.2"
system_time = datetime.now()

uptime_seconds = 0
command_history = []

running = True


# ============================================================
# boot sequence
# ============================================================

def boot():
    print("SeaBIOS (version 1.16.3)")
    print("Machine UUID 00000000-0000-0000-0000-000000000000")
    print()
    print("Booting from Hard Disk...")
    print()
    print("ELKS bootloader")
    print("Loading kernel...")
    print()
    print("ELKS 0.9.2")
    print("16-bit x86 kernel")
    print()
    print("Initializing memory...")
    print("Initializing kernel...")
    print("Initializing process management...")
    print("Initializing filesystem...")
    print("Initializing device drivers...")
    print()
    print("Mounting root filesystem...")
    print("Starting init...")
    print()
    print("ELKS system ready.")
    print()


# ============================================================
# shell commands
# ============================================================

def cmd_help(args):
    print("Available commands:")
    print()
    print("  help       show this help")
    print("  clear      clear the terminal")
    print("  ls         list directory contents")
    print("  cd         change directory")
    print("  pwd        print working directory")
    print("  cat        display a file")
    print("  mkdir      create a directory")
    print("  touch      create an empty file")
    print("  echo       display text")
    print("  uname      system information")
    print("  hostname   show hostname")
    print("  whoami     show current user")
    print("  date       display date")
    print("  uptime     show uptime")
    print("  free       memory information")
    print("  ps         process list")
    print("  dmesg      kernel messages")
    print("  reboot     restart system")
    print("  exit       close shell")


def cmd_ls(args):
    path = args[0] if args else cwd
    target = resolve(path)

    if target is None:
        print(f"ls: {path}: No such file or directory")
        return

    if isinstance(target, File):
        print(os.path.basename(path))
        return

    for name, item in sorted(target.entries.items()):
        suffix = "/" if isinstance(item, Directory) else ""
        print(name + suffix)


def cmd_cd(args):
    global cwd

    path = args[0] if args else "/home/root"
    target_path = get_path(path)
    target = resolve(target_path)

    if target is None:
        print(f"cd: {path}: No such file or directory")
    elif not isinstance(target, Directory):
        print(f"cd: {path}: Not a directory")
    else:
        cwd = target_path


def cmd_pwd(args):
    print(cwd)


def cmd_cat(args):
    if not args:
        print("cat: missing file operand")
        return

    for path in args:
        target = resolve(path)

        if target is None:
            print(f"cat: {path}: No such file or directory")
        elif isinstance(target, Directory):
            print(f"cat: {path}: Is a directory")
        else:
            print(target.content, end="")


def cmd_mkdir(args):
    if not args:
        print("mkdir: missing operand")
        return

    for path in args:
        if not make_directory(path):
            print(f"mkdir: cannot create directory '{path}'")


def cmd_touch(args):
    if not args:
        print("touch: missing file operand")
        return

    for path in args:
        if resolve(path) is None:
            if not make_file(path):
                print(f"touch: cannot create '{path}'")


def cmd_echo(args):
    print(" ".join(args))


def cmd_uname(args):
    if "-a" in args:
        print(f"ELKS {hostname} 0.9.2 i8086")
    elif "-r" in args:
        print(kernel_version)
    elif "-n" in args:
        print(hostname)
    else:
        print("ELKS")


def cmd_hostname(args):
    print(hostname)


def cmd_whoami(args):
    print(username)


def cmd_date(args):
    print(datetime.now().strftime("%a %b %d %H:%M:%S %Y"))


def cmd_uptime(args):
    print(f"up {uptime_seconds} seconds")


def cmd_free(args):
    print("              total       used       free")
    print("Memory:       640K        128K       512K")


def cmd_ps(args):
    print("PID  TTY  STAT  COMMAND")
    print("  1  -    S     init")
    print("  2  -    S     [kflush]")
    print("  3  -    S     /bin/sh")


KERNEL_MESSAGES = [
    "ELKS kernel booting",
    "CPU: 8086 compatible",
    "Memory: 640 KB conventional memory",
    "Kernel: initializing",
    "VFS: mounting root filesystem",
    "init: starting system",
]


def cmd_dmesg(args):
    for message in KERNEL_MESSAGES:
        print(f"[    0.000] {message}")


def cmd_clear(args):
    clear_screen()


def cmd_reboot(args):
    clear_screen()
    boot()
    cmd_help([])


def cmd_exit(args):
    print("Shell terminated.")
    command_input.disabled = True


COMMANDS = {
    "help": cmd_help,
    "ls": cmd_ls,
    "cd": cmd_cd,
    "pwd": cmd_pwd,
    "cat": cmd_cat,
    "mkdir": cmd_mkdir,
    "touch": cmd_touch,
    "echo": cmd_echo,
    "uname": cmd_uname,
    "hostname": cmd_hostname,
    "whoami": cmd_whoami,
    "date": cmd_date,
    "uptime": cmd_uptime,
    "free": cmd_free,
    "ps": cmd_ps,
    "dmesg": cmd_dmesg,
    "clear": cmd_clear,
    "reboot": cmd_reboot,
    "exit": cmd_exit,
}


# ============================================================
# shell
# ============================================================

def prompt():
    return f"{username}@{hostname}:{cwd}# "


def execute(command):
    command = command.strip()

    if not command:
        return

    try:
        parts = shlex.split(command)
    except ValueError as error:
        print(f"sh: {error}")
        return

    name = parts[0]
    args = parts[1:]

    if name in COMMANDS:
        try:
            COMMANDS[name](args)
        except Exception as error:
            print(f"{name}: internal error: {error}")

    else:
        print(f"sh: {name}: command not found")


def on_keydown(event):
    if event.key != "Enter":
        return

    command = command_input.value
    command_input.value = ""

    print(prompt() + command)

    if command.strip():
        command_history.append(command)

    execute(command)

    command_input.focus()


# Keep the proxy alive for as long as the page is running.
keydown_proxy = create_proxy(on_keydown)
command_input.addEventListener("keydown", keydown_proxy)


# ============================================================
# startup
# ============================================================

boot()
print("Type 'help' for available commands.")
print()

command_input.focus()
