
import sys
import time
import shlex
import random
import datetime
from collections import deque

# ============================================================
# NEXUS LINUX
# Browser-hosted Python operating system
# ============================================================

VERSION = "6.8.12-nexus"
HOSTNAME = "nexus"
ARCH = "wasm32"
RAM = 4096

GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
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

        for path in [
            "/bin", "/boot", "/dev", "/etc", "/home",
            "/home/user", "/lib", "/mnt", "/opt", "/proc",
            "/root", "/run", "/sbin", "/sys", "/tmp",
            "/usr", "/usr/bin", "/usr/lib", "/var",
            "/var/log", "/var/tmp"
        ]:
            self.mkdir(path)

        self.write("/etc/hostname", "nexus\n")
        self.write("/etc/os-release",
            'NAME="Nexus Linux"\n'
            'VERSION="6.8"\n'
            'ID=nexus\n'
            'PRETTY_NAME="Nexus Linux 6.8"\n'
        )
        self.write("/etc/passwd",
            "root:x:0:0:root:/root:/bin/bash\n"
            "user:x:1000:1000:User:/home/user:/bin/bash\n"
        )
        self.write("/etc/motd",
            "Welcome to Nexus Linux 6.8.\n"
            "This system is running on PyScript.\n"
        )
        self.write("/var/log/boot.log", "")

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

    def mkdir(self, path):
        path = self.normalize(path)
        parent = path.rsplit("/", 1)[0] or "/"

        if parent not in self.dirs or self.exists(path):
            return False

        self.dirs.add(path)
        return True

    def write(self, path, content):
        path = self.normalize(path)
        parent = path.rsplit("/", 1)[0] or "/"

        if parent not in self.dirs or path in self.dirs:
            return False

        self.files[path] = str(content)
        return True

    def read(self, path):
        return self.files.get(self.normalize(path))

    def remove(self, path):
        path = self.normalize(path)

        if path in self.files:
            del self.files[path]
            return True

        if path in self.dirs and path != "/":
            prefix = path.rstrip("/") + "/"

            if any(p.startswith(prefix) for p in self.files | self.dirs):
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

            parent = item.rsplit("/", 1)[0] or "/"

            if parent == path:
                result.add(item.rsplit("/", 1)[-1])

        return sorted(result)

    def copy(self, src, dst):
        content = self.read(src)

        if content is None:
            return False

        return self.write(dst, content)

    def move(self, src, dst):
        content = self.read(src)

        if content is None or not self.write(dst, content):
            return False

        del self.files[self.normalize(src)]
        return True


# ============================================================
# KERNEL
# ============================================================

class Kernel:
    def __init__(self):
        self.logs = deque(maxlen=1000)
        self.processes = []
        self.pid = 1
        self.start_time = time.monotonic()
        self.ram_used = 384

    def log(self, message, level="info"):
        elapsed = time.monotonic() - self.start_time

        line = f"[{elapsed:8.3f}] {message}"
        self.logs.append(line)

        colors = {
            "info": "",
            "ok": GREEN,
            "warn": YELLOW,
            "error": RED
        }

        print(colors[level] + line + RESET)

    def add_process(self, name, user="root"):
        self.processes.append({
            "pid": self.pid,
            "user": user,
            "state": "S",
            "name": name
        })
        self.pid += 1

    def boot(self):
        self.start_time = time.monotonic()

        print(CYAN + BOLD + "NEXUS SYSTEM FIRMWARE v2.4" + RESET)
        print("Nexus Virtual Machine")
        print("CPU: WebAssembly Runtime")
        print("Memory: 4096 MiB")
        print("Storage: Nexus Virtual Disk")
        print()

        print("Nexus Bootloader 2.1")
        print("Loading /boot/vmlinuz...")
        print("Loading /boot/initramfs.img...")
        print("Starting kernel...")
        print()

        self.log("Linux version " + VERSION + " (" + ARCH + ")")
        self.log("Command line: BOOT_IMAGE=/boot/vmlinuz root=/dev/sda1")
        self.log("BIOS-provided physical RAM map:")
        self.log("Memory: 4194304K available")
        self.log("Kernel command line parsed")
        self.log("DMI: Nexus Virtual Platform")
        self.log("smp: Bringing up secondary CPUs ...")
        self.log("clocksource: switched to monotonic")
        self.log("PCI: Probing virtual hardware")
        self.log("NET: Registered PF_INET protocol family")
        self.log("TCP: Hash tables configured")
        self.log("VFS: Mounted root (nexusfs filesystem)")
        self.log("Freeing unused kernel memory")
        self.log("Run /sbin/init as init process")

        print()

        self.log("systemd[1]: systemd 256 running in system mode")

        services = [
            "Journal Service",
            "Device Manager",
            "Temporary Files",
            "Kernel Parameters",
            "Kernel Modules",
            "Local File Systems",
            "Login Service",
            "Network Manager",
            "Cron Service",
            "Virtual Console",
            "Multi-User System"
        ]

        for service in services:
            duration = random.randint(12, 140)
            self.log(
                f"systemd[1]: Started {service}.",
                "ok"
            )

        self.log("systemd[1]: Reached target Multi-User System.")
        self.log("systemd[1]: Startup finished in 2.841s.")

        for name in [
            "systemd", "kthreadd", "systemd-journald",
            "systemd-udevd", "NetworkManager", "cron", "getty"
        ]:
            self.add_process(name)

        print()
        print(GREEN + BOLD + "Nexus Linux 6.8" + RESET)
        print("Kernel:", VERSION)
        print("System ready.")
        print()


# ============================================================
# NEXUS OS
# ============================================================

class NexusOS:
    def __init__(self):
        self.fs = VirtualFS()
        self.kernel = Kernel()

        self.user = "user"
        self.uid = 1000
        self.cwd = "/home/user"
        self.root = False
        self.running = True
        self.reboot_requested = False

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

    def resolve(self, path):
        return self.fs.normalize(path, self.cwd)

    def prompt(self):
        symbol = "#" if self.root else "$"
        cwd = self.cwd

        if cwd == self.env["HOME"]:
            cwd = "~"
        elif cwd.startswith(self.env["HOME"] + "/"):
            cwd = "~" + cwd[len(self.env["HOME"]):]

        return (
            GREEN + self.user + "@" + HOSTNAME +
            RESET + ":" + BLUE + cwd +
            RESET + symbol + " "
        )

    def error(self, message):
        print(RED + "bash: " + message + RESET)

    # ========================================================
    # FILESYSTEM COMMANDS
    # ========================================================

    def cmd_ls(self, args):
        path = self.resolve(args[0]) if args else self.cwd
        items = self.fs.listdir(path)

        if items is None:
            self.error(f"{path}: No such directory")
            return

        for item in items:
            full = self.resolve(path + "/" + item)

            if self.fs.exists(full) and full in self.fs.dirs:
                print(BLUE + BOLD + item + "/" + RESET, end="  ")
            else:
                print(item, end="  ")

        print()

    def cmd_cd(self, args):
        path = args[0] if args else self.env["HOME"]
        target = self.resolve(path)

        if target not in self.fs.dirs:
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
            content = self.fs.read(self.resolve(path))

            if content is None:
                self.error(f"cat: {path}: No such file")
            else:
                print(content, end="")

        print()

    def cmd_touch(self, args):
        for path in args:
            target = self.resolve(path)

            if not self.fs.exists(target):
                if not self.fs.write(target, ""):
                    self.error(f"touch: cannot create '{path}'")

    def cmd_mkdir(self, args):
        for path in args:
            if not self.fs.mkdir(self.resolve(path)):
                self.error(f"mkdir: cannot create '{path}'")

    def cmd_rm(self, args):
        for path in args:
            if not self.fs.remove(self.resolve(path)):
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

    def cmd_tree(self, args):
        root = self.resolve(args[0]) if args else self.cwd

        if root not in self.fs.dirs:
            self.error("tree: invalid directory")
            return

        print(root)

        def walk(path, prefix=""):
            items = self.fs.listdir(path) or []

            for index, item in enumerate(items):
                last = index == len(items) - 1
                full = self.resolve(path + "/" + item)

                print(prefix + ("└── " if last else "├── ") + item)

                if full in self.fs.dirs:
                    walk(
                        full,
                        prefix + ("    " if last else "│   ")
                    )

        walk(root)

    def cmd_find(self, args):
        root = self.resolve(args[0]) if args else self.cwd

        if root not in self.fs.dirs:
            self.error("find: invalid directory")
            return

        def walk(path):
            for item in self.fs.listdir(path) or []:
                full = self.resolve(path + "/" + item)
                print(full)

                if full in self.fs.dirs:
                    walk(full)

        walk(root)

    # ========================================================
    # SYSTEM COMMANDS
    # ========================================================

    def cmd_uname(self, args):
        if "-a" in args:
            print(
                f"Linux {HOSTNAME} {VERSION} "
                f"#1 SMP PREEMPT_DYNAMIC {ARCH} GNU/Linux"
            )
        else:
            print("Linux")

    def cmd_hostname(self, args):
        print(HOSTNAME)

    def cmd_whoami(self, args):
        print(self.user)

    def cmd_id(self, args):
        print(
            f"uid={self.uid}({self.user}) "
            f"gid={self.uid}({self.user})"
        )

    def cmd_date(self, args):
        print(datetime.datetime.now().astimezone())

    def cmd_uptime(self, args):
        elapsed = int(time.monotonic() - self.kernel.start_time)
        hours, rem = divmod(elapsed, 3600)
        minutes, seconds = divmod(rem, 60)

        print(
            f"up {hours}:{minutes:02}, "
            f"{len(self.kernel.processes)} processes, "
            "load average: 0.08, 0.04, 0.02"
        )

    def cmd_free(self, args):
        print("               total        used        free")
        print(
            f"Mem:        {RAM:8}    "
            f"{self.kernel.ram_used:8}    "
            f"{RAM - self.kernel.ram_used:8}"
        )
        print("Swap:          2048           0        2048")

    def cmd_df(self, args):
        print("Filesystem      Size  Used Avail Use% Mounted on")
        print("/dev/sda1        20G  2.1G   17G  12% /")
        print("tmpfs           2.0G  4.0M  2.0G   1% /run")

    def cmd_ps(self, args):
        print("  PID USER       STAT COMMAND")

        for p in self.kernel.processes:
            print(
                f"{p['pid']:5} {p['user']:<10} "
                f"{p['state']:<4} {p['name']}"
            )

    def cmd_top(self, args):
        print("Nexus Linux - top")
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

    # ========================================================
    # SHELL
    # ========================================================

    def cmd_echo(self, args):
        print(" ".join(args))

    def cmd_clear(self, args):
        print("\033[2J\033[H", end="")

    def cmd_help(self, args):
        print("""
Nexus Linux 6.8

Filesystem:
  ls [path]       List files
  cd [path]       Change directory
  pwd             Print working directory
  cat file        Read file
  touch file      Create file
  mkdir dir       Create directory
  rm file         Remove file
  cp src dst      Copy file
  mv src dst      Move file
  tree [path]     Directory tree
  find [path]     Find files

System:
  uname [-a]      Kernel information
  hostname        Hostname
  uptime          Uptime
  free            Memory usage
  df              Disk usage
  ps              Processes
  top             Process monitor
  dmesg           Kernel messages
  date            Date and time
  whoami          Current user
  id              User information
  env             Environment

Shell:
  echo            Print text
  export          Set environment variable
  history         Command history
  clear           Clear terminal
  help            Help
  su              Switch to root
  exit            Exit shell

System:
  reboot          Restart
  shutdown        Power off
""")

    # ========================================================
    # PRIVILEGES
    # ========================================================

    def cmd_su(self, args):
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
        else:
            self.running = False

    def cmd_reboot(self, args):
        print("Broadcast message: System is rebooting now!")
        self.reboot_requested = True
        self.running = False

    def cmd_shutdown(self, args):
        print("System halted.")
        self.running = False
        self.reboot_requested = False

    # ========================================================
    # COMMAND DISPATCHER
    # ========================================================

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
            "tree": self.cmd_tree,
            "find": self.cmd_find,
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
            "echo": self.cmd_echo,
            "clear": self.cmd_clear,
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
        system = NexusOS()
        system.kernel.boot()

        print("Nexus Linux 6.8")
        print("nexus login: user")
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
                system.running = False

        if not system.reboot_requested:
            print("Connection to nexus closed.")
            break


main()
