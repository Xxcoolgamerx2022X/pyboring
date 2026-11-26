
import os
import sys
import time
import shlex
import random
import datetime
import getpass
import platform
from collections import deque

# ============================================================
# NEXUS LINUX
# A Python-based Linux-like operating system simulator
# ============================================================

VERSION = "6.8.12-nexus"
HOSTNAME = "nexus"
KERNEL = "Nexus Kernel"
ARCH = platform.machine()
BOOT_TIME = time.time()

GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
WHITE = "\033[97m"
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"

# ============================================================
# VIRTUAL FILESYSTEM
# ============================================================

class VirtualFS:
    def __init__(self):
        self.dirs = {"/"}
        self.files = {}

        self.mkdir("/bin")
        self.mkdir("/boot")
        self.mkdir("/dev")
        self.mkdir("/etc")
        self.mkdir("/home")
        self.mkdir("/home/user")
        self.mkdir("/lib")
        self.mkdir("/mnt")
        self.mkdir("/opt")
        self.mkdir("/proc")
        self.mkdir("/root")
        self.mkdir("/run")
        self.mkdir("/sbin")
        self.mkdir("/sys")
        self.mkdir("/tmp")
        self.mkdir("/usr")
        self.mkdir("/usr/bin")
        self.mkdir("/usr/lib")
        self.mkdir("/var")
        self.mkdir("/var/log")
        self.mkdir("/var/tmp")

        self.write("/etc/hostname", "nexus\n")
        self.write("/etc/os-release",
            'NAME="Nexus Linux"\n'
            'VERSION="6.8"\n'
            'ID=nexus\n'
            'PRETTY_NAME="Nexus Linux 6.8"\n'
        )
        self.write("/etc/issue", "Nexus Linux 6.8 \\n \\l\n")
        self.write("/etc/motd",
            "Welcome to Nexus Linux.\n"
            "Documentation: https://example.invalid\n"
        )
        self.write("/etc/passwd",
            "root:x:0:0:root:/root:/bin/bash\n"
            "user:x:1000:1000:User:/home/user:/bin/bash\n"
        )
        self.write("/home/user/.profile",
            'export USER=user\n'
            'export HOME=/home/user\n'
        )
        self.write("/var/log/boot.log", "")
        self.write("/var/log/syslog", "")

    def normalize(self, path, cwd="/"):
        if not path:
            return cwd

        if not path.startswith("/"):
            path = cwd.rstrip("/") + "/" + path

        parts = []

        for part in path.split("/"):
            if part in ("", "."):
                continue
            elif part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)

        return "/" + "/".join(parts)

    def exists(self, path):
        return path in self.dirs or path in self.files

    def is_dir(self, path):
        return path in self.dirs

    def mkdir(self, path):
        path = self.normalize(path)
        parent = os.path.dirname(path) or "/"

        if parent not in self.dirs:
            return False

        if self.exists(path):
            return False

        self.dirs.add(path)
        return True

    def write(self, path, content):
        path = self.normalize(path)
        parent = os.path.dirname(path) or "/"

        if parent not in self.dirs:
            return False

        if path in self.dirs:
            return False

        self.files[path] = str(content)
        return True

    def read(self, path):
        path = self.normalize(path)

        if path in self.files:
            return self.files[path]

        return None

    def remove(self, path):
        path = self.normalize(path)

        if path in self.files:
            del self.files[path]
            return True

        if path in self.dirs and path != "/":
            children = [
                p for p in self.dirs | self.files.keys()
                if p != path and p.startswith(path.rstrip("/") + "/")
            ]

            if children:
                return False

            self.dirs.remove(path)
            return True

        return False

    def listdir(self, path):
        path = self.normalize(path)

        if path not in self.dirs:
            return None

        result = set()

        for item in self.dirs | self.files.keys():
            if item == "/":
                continue

            parent = os.path.dirname(item.rstrip("/")) or "/"

            if parent == path:
                result.add(os.path.basename(item))

        return sorted(result)

    def copy(self, src, dst):
        src = self.normalize(src)
        dst = self.normalize(dst)

        if src not in self.files:
            return False

        return self.write(dst, self.files[src])

    def move(self, src, dst):
        src = self.normalize(src)
        dst = self.normalize(dst)

        if src not in self.files:
            return False

        if not self.write(dst, self.files[src]):
            return False

        del self.files[src]
        return True


# ============================================================
# KERNEL
# ============================================================

class Kernel:
    def __init__(self):
        self.logs = deque(maxlen=1000)
        self.processes = []
        self.pid = 1
        self.booted = False
        self.start_time = time.time()

        self.cpu = ARCH
        self.ram = 4096
        self.used_ram = 384

        self.devices = [
            "cpu0",
            "cpu1",
            "tty0",
            "tty1",
            "sda",
            "loop0",
            "eth0",
            "rtc0"
        ]

    def log(self, message, level="info"):
        elapsed = time.monotonic() - self.start_time

        line = (
            f"[{elapsed:8.3f}] "
            f"{message}"
        )

        self.logs.append(line)

        colors = {
            "info": WHITE,
            "ok": GREEN,
            "warn": YELLOW,
            "error": RED
        }

        print(colors.get(level, WHITE) + line + RESET)

    def add_process(self, name, user="root", state="S"):
        process = {
            "pid": self.pid,
            "user": user,
            "state": state,
            "name": name,
            "cpu": round(random.uniform(0, 2), 1),
            "mem": random.randint(1, 40)
        }

        self.processes.append(process)
        self.pid += 1

    def boot(self):
        self.start_time = time.monotonic()

        print("\033[2J\033[H", end="")
        print(f"{CYAN}{BOLD}NEXUS SYSTEM FIRMWARE v2.4{RESET}")
        print("Copyright (C) Nexus Systems")
        print()
        time.sleep(0.3)

        print("Nexus BIOS initializing...")
        time.sleep(0.2)

        print("CPU:", self.cpu)
        print("Memory:", self.ram, "MiB")
        print("Storage: Nexus Virtual Disk")
        time.sleep(0.3)

        print()
        print("Nexus Bootloader 2.1")
        print("Loading /boot/vmlinuz...")
        time.sleep(0.3)
        print("Loading /boot/initramfs.img...")
        time.sleep(0.2)
        print("Starting kernel...")
        time.sleep(0.3)
        print()

        self.log("Linux version " + VERSION + " (" + ARCH + ")")
        self.log("Command line: BOOT_IMAGE=/boot/vmlinuz root=/dev/sda1")
        self.log("BIOS-provided physical RAM map:")
        self.log("Memory: 4194304K available")
        self.log("Kernel command line parsed")
        self.log("DMI: Nexus Virtual Machine / Virtual Platform")
        self.log("smp: Bringing up secondary CPUs ...")
        self.log("smp: Brought up 2 CPUs")
        self.log("clocksource: switched to tsc")
        self.log("PCI: Probing PCI hardware")
        self.log("ACPI: Interpreter enabled")
        self.log("NET: Registered PF_INET protocol family")
        self.log("TCP: Hash tables configured")
        self.log("VFS: Mounted root (nexusfs filesystem)")
        self.log("EXT4-fs: mounted filesystem on /dev/sda1")
        self.log("Freeing unused kernel memory")
        self.log("Run /sbin/init as init process")

        print()
        time.sleep(0.3)

        self.log("systemd[1]: systemd 256 running in system mode")
        self.log("systemd[1]: Detected architecture " + ARCH)

        services = [
            ("systemd-journald.service", "Journal Service"),
            ("systemd-udevd.service", "Device Manager"),
            ("systemd-tmpfiles-setup.service", "Temporary Files"),
            ("systemd-sysctl.service", "Kernel Parameters"),
            ("systemd-modules-load.service", "Kernel Modules"),
            ("systemd-remount-fs.service", "Remount Root Filesystem"),
            ("local-fs.target", "Local File Systems"),
            ("systemd-logind.service", "Login Service"),
            ("NetworkManager.service", "Network Manager"),
            ("cron.service", "Regular Background Program Processing"),
            ("getty@tty1.service", "Virtual Console"),
            ("multi-user.target", "Multi-User System"),
        ]

        for service, description in services:
            duration = random.randint(12, 140)
            self.log(
                f"systemd[1]: Started {description} ({service}).",
                "ok"
            )
            time.sleep(0.08)

        print()
        self.log("systemd[1]: Reached target Graphical Interface.")
        self.log("systemd[1]: Startup finished in 2.841s.")
        print()

        self.add_process("systemd")
        self.add_process("kthreadd")
        self.add_process("systemd-journald")
        self.add_process("systemd-udevd")
        self.add_process("NetworkManager")
        self.add_process("cron")
        self.add_process("getty")

        self.booted = True

        print(f"{GREEN}{BOLD}Nexus Linux 6.8{RESET}")
        print("Kernel:", VERSION)
        print("System ready.")
        print()

        time.sleep(0.3)


# ============================================================
# OPERATING SYSTEM
# ============================================================

class NexusOS:
    def __init__(self):
        self.fs = VirtualFS()
        self.kernel = Kernel()

        self.user = "user"
        self.uid = 1000
        self.cwd = "/home/user"

        self.hostname = HOSTNAME
        self.running = True
        self.root = False

        self.history = []
        self.env = {
            "HOME": "/home/user",
            "USER": "user",
            "SHELL": "/bin/bash",
            "PATH": "/bin:/sbin:/usr/bin",
            "HOSTNAME": HOSTNAME,
            "TERM": "xterm-256color",
            "PWD": "/home/user"
        }

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    def output(self, message=""):
        print(message)

    def error(self, message):
        print(f"{RED}bash: {message}{RESET}")

    def resolve(self, path):
        return self.fs.normalize(path, self.cwd)

    def prompt(self):
        symbol = "#" if self.root else "$"

        home = self.env["HOME"]

        display_cwd = self.cwd

        if display_cwd == home:
            display_cwd = "~"
        elif display_cwd.startswith(home + "/"):
            display_cwd = "~" + display_cwd[len(home):]

        return (
            f"{GREEN}{self.user}@{self.hostname}"
            f"{RESET}:{BLUE}{display_cwd}"
            f"{RESET}{symbol} "
        )

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    def cmd_help(self, args):
        print(f"""
{BOLD}Nexus Linux commands{RESET}

Filesystem:
  ls [path]          List directory contents
  cd [path]          Change directory
  pwd                Print working directory
  cat file           Read a file
  touch file         Create a file
  mkdir dir          Create directory
  rm file            Remove file
  cp src dst         Copy file
  mv src dst         Move file
  tree [path]        Display filesystem tree
  find [path]        Find files

System:
  uname [-a]         Kernel information
  hostname           Display hostname
  uptime             System uptime
  free               Memory information
  df                 Filesystem usage
  ps                 Process list
  top                Process monitor
  dmesg              Kernel messages
  whoami             Current user
  id                 User information
  date               Current date and time
  env                Environment variables

Shell:
  echo [text]        Print text
  export KEY=value   Set environment variable
  history            Command history
  clear              Clear screen
  help               Display this help
  su                 Switch to root
  exit               Exit shell

System control:
  reboot             Restart system
  shutdown           Shut down system
""")

    def cmd_ls(self, args):
        path = self.resolve(args[0]) if args else self.cwd

        items = self.fs.listdir(path)

        if items is None:
            self.error(f"{path}: No such directory")
            return

        for item in items:
            full = self.resolve(path + "/" + item)

            if self.fs.is_dir(full):
                print(f"{BLUE}{BOLD}{item}/{RESET}", end="  ")
            else:
                print(item, end="  ")

        print()

    def cmd_cd(self, args):
        path = args[0] if args else self.env["HOME"]
        target = self.resolve(path)

        if not self.fs.is_dir(target):
            self.error(f"cd: {path}: No such directory")
            return

        self.cwd = target
        self.env["PWD"] = target

    def cmd_pwd(self, args):
        print(self.cwd)

    def cmd_cat(self, args):
        if not args:
            self.error("cat: missing operand")
            return

        for path in args:
            target = self.resolve(path)
            content = self.fs.read(target)

            if content is None:
                self.error(f"cat: {path}: No such file")
            else:
                print(content, end="")

        print()

    def cmd_touch(self, args):
        if not args:
            self.error("touch: missing operand")
            return

        for path in args:
            target = self.resolve(path)

            if self.fs.exists(target):
                continue

            if not self.fs.write(target, ""):
                self.error(f"touch: cannot create '{path}'")

    def cmd_mkdir(self, args):
        if not args:
            self.error("mkdir: missing operand")
            return

        for path in args:
            target = self.resolve(path)

            if not self.fs.mkdir(target):
                self.error(f"mkdir: cannot create directory '{path}'")

    def cmd_rm(self, args):
        if not args:
            self.error("rm: missing operand")
            return

        for path in args:
            target = self.resolve(path)

            if not self.fs.remove(target):
                self.error(f"rm: cannot remove '{path}'")

    def cmd_cp(self, args):
        if len(args) != 2:
            self.error("cp: usage: cp SOURCE DEST")
            return

        if not self.fs.copy(
            self.resolve(args[0]),
            self.resolve(args[1])
        ):
            self.error("cp: operation failed")

    def cmd_mv(self, args):
        if len(args) != 2:
            self.error("mv: usage: mv SOURCE DEST")
            return

        if not self.fs.move(
            self.resolve(args[0]),
            self.resolve(args[1])
        ):
            self.error("mv: operation failed")

    def cmd_echo(self, args):
        print(" ".join(args))

    def cmd_uname(self, args):
        if "-a" in args:
            print(
                f"Linux {self.hostname} {VERSION} "
                f"#1 SMP PREEMPT_DYNAMIC {ARCH} GNU/Linux"
            )
        else:
            print("Linux")

    def cmd_hostname(self, args):
        print(self.hostname)

    def cmd_whoami(self, args):
        print(self.user)

    def cmd_id(self, args):
        print(
            f"uid={self.uid}({self.user}) "
            f"gid={self.uid}({self.user}) "
            f"groups={self.uid}({self.user})"
        )

    def cmd_date(self, args):
        print(datetime.datetime.now().astimezone().strftime(
            "%a %b %d %H:%M:%S %Z %Y"
        ))

    def cmd_uptime(self, args):
        elapsed = int(time.time() - BOOT_TIME)

        days, rem = divmod(elapsed, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)

        print(
            f"up {days} days, {hours}:{minutes:02}, "
            f"{self.kernel.pid} processes, "
            f"load average: 0.08, 0.04, 0.02"
        )

    def cmd_free(self, args):
        print("               total        used        free")
        print(
            f"Mem:        {self.kernel.ram:8}    "
            f"{self.kernel.used_ram:8}    "
            f"{self.kernel.ram - self.kernel.used_ram:8}"
        )
        print(
            f"Swap:       {2048:8}    "
            f"{0:8}    {2048:8}"
        )

    def cmd_df(self, args):
        print("Filesystem      Size  Used Avail Use% Mounted on")
        print("/dev/sda1        20G  2.1G   17G  12% /")
        print("tmpfs           2.0G  4.0M  2.0G   1% /run")
        print("tmpfs           2.0G     0  2.0G   0% /dev/shm")

    def cmd_ps(self, args):
        print("  PID USER       STAT COMMAND")

        for process in self.kernel.processes:
            print(
                f"{process['pid']:5} "
                f"{process['user']:<10} "
                f"{process['state']:<4} "
                f"{process['name']}"
            )

    def cmd_top(self, args):
        print("Nexus Linux - top")
        print()
        print(f"Tasks: {len(self.kernel.processes)} total")
        print("CPU: 2.4% user, 0.8% system, 96.8% idle")
        print()
        self.cmd_ps([])

    def cmd_dmesg(self, args):
        for line in self.kernel.logs:
            print(line)

    def cmd_env(self, args):
        for key, value in self.env.items():
            print(f"{key}={value}")

    def cmd_export(self, args):
        if not args or "=" not in args[0]:
            self.error("export: usage: export KEY=value")
            return

        key, value = args[0].split("=", 1)
        self.env[key] = value

    def cmd_history(self, args):
        for i, command in enumerate(self.history, 1):
            print(f"{i:5}  {command}")

    def cmd_clear(self, args):
        print("\033[2J\033[H", end="")

    def cmd_tree(self, args):
        root = self.resolve(args[0]) if args else self.cwd

        if not self.fs.is_dir(root):
            self.error("tree: not a directory")
            return

        print(root)

        def walk(path, prefix=""):
            items = self.fs.listdir(path) or []

            for index, item in enumerate(items):
                last = index == len(items) - 1
                branch = "└── " if last else "├── "
                full = self.resolve(path + "/" + item)

                print(prefix + branch + item)

                if self.fs.is_dir(full):
                    walk(
                        full,
                        prefix + ("    " if last else "│   ")
                    )

        walk(root)

    def cmd_find(self, args):
        root = self.resolve(args[0]) if args else self.cwd

        if not self.fs.is_dir(root):
            self.error("find: invalid directory")
            return

        def walk(path):
            for item in self.fs.listdir(path) or []:
                full = self.resolve(path + "/" + item)
                print(full)

                if self.fs.is_dir(full):
                    walk(full)

        walk(root)

    # --------------------------------------------------------
    # ROOT / SYSTEM CONTROL
    # --------------------------------------------------------

    def cmd_su(self, args):
        if self.root:
            print("Already root.")
            return

        self.root = True
        self.user = "root"
        self.uid = 0
        self.env["USER"] = "root"
        self.env["HOME"] = "/root"
        self.cwd = "/root"
        self.env["PWD"] = self.cwd

    def cmd_exit(self, args):
        if self.root:
            self.root = False
            self.user = "user"
            self.uid = 1000
            self.env["USER"] = "user"
            self.env["HOME"] = "/home/user"
            self.cwd = "/home/user"
            self.env["PWD"] = self.cwd
            return

        self.running = False

    def cmd_reboot(self, args):
        print("Broadcast message: System is rebooting now!")
        time.sleep(0.5)

        self.kernel = Kernel()
        self.cwd = "/home/user"
        self.root = False
        self.user = "user"
        self.uid = 1000
        self.running = False

        self.reboot_requested = True

    def cmd_shutdown(self, args):
        print("Powering off...")
        time.sleep(0.5)
        self.running = False
        self.reboot_requested = False

    # --------------------------------------------------------
    # COMMAND INTERPRETER
    # --------------------------------------------------------

    def execute(self, command):
        command = command.strip()

        if not command:
            return

        self.history.append(command)

        try:
            parts = shlex.split(command)
        except ValueError as exc:
            self.error(str(exc))
            return

        if not parts:
            return

        name = parts[0]
        args = parts[1:]

        commands = {
            "help": self.cmd_help,
            "ls": self.cmd_ls,
            "cd": self.cmd_cd,
            "pwd": self.cmd_pwd,
            "cat": self.cmd_cat,
            "touch": self.cmd_touch,
            "mkdir": self.cmd_mkdir,
            "rm": self.cmd_rm,
            "cp": self.cmd_cp,
            "mv": self.cmd_mv,
            "echo": self.cmd_echo,
            "uname": self.cmd_uname,
            "hostname": self.cmd_hostname,
            "whoami": self.cmd_whoami,
            "id": self.cmd_id,
            "date": self.cmd_date,
            "uptime": self.cmd_uptime,
            "free": self.cmd_free,
            "df": self.cmd_df,
            "ps": self.cmd_ps,
            "top": self.cmd_top,
            "dmesg": self.cmd_dmesg,
            "env": self.cmd_env,
            "export": self.cmd_export,
            "history": self.cmd_history,
            "clear": self.cmd_clear,
            "tree": self.cmd_tree,
            "find": self.cmd_find,
            "su": self.cmd_su,
            "exit": self.cmd_exit,
            "reboot": self.cmd_reboot,
            "shutdown": self.cmd_shutdown
        }

        if name in commands:
            commands[name](args)
        else:
            self.error(f"{name}: command not found")


# ============================================================
# MAIN
# ============================================================

def main():
    while True:
        os.system("")

        system = NexusOS()
        system.reboot_requested = False

        system.kernel.boot()

        print(f"{CYAN}Nexus Linux 6.8{RESET}")
        print("nexus login: ", end="", flush=True)

        # Simulated login
        print("user")
        time.sleep(0.2)

        print("Last login: Fri Nov 27 09:42:11 on tty1")
        print()

        print(system.fs.read("/etc/motd"))

        system.running = True

        while system.running:
            try:
                command = input(system.prompt())
                system.execute(command)

            except KeyboardInterrupt:
                print("^C")

            except EOFError:
                print()
                system.running = False

        if not system.reboot_requested:
            print("Connection to nexus closed.")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSystem halted.")
