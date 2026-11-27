
import sys
import time
import shlex
import random
import datetime
from collections import deque

# ============================================================
# ELKS 0.9.2 - PYTHON SIMULATION
# 8086 / 8088 PC environment
# ============================================================

VERSION = "0.9.2"
KERNEL_VERSION = "0.9.2"
HOSTNAME = "elks"
ARCH = "i8086"

RAM = 640 * 1024
HEAP_SIZE = 5246

RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
BLUE = "\033[34m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GRAY = "\033[90m"
BOLD = "\033[1m"

# ============================================================
# TERMINAL
# ============================================================

def sleep(seconds=0.05):
    time.sleep(seconds)


def clear():
    print("\033[2J\033[H", end="")


def message(text):
    print(text)


# ============================================================
# VIRTUAL FILESYSTEM
# ============================================================

class FileSystem:

    def __init__(self):
        self.dirs = {"/"}
        self.files = {}
        self.mounts = {
            "/": "/dev/fd0"
        }

        directories = [
            "/bin",
            "/dev",
            "/etc",
            "/home",
            "/lib",
            "/mnt",
            "/proc",
            "/root",
            "/tmp",
            "/usr",
            "/var",
            "/var/log",
            "/boot"
        ]

        for path in directories:
            self.mkdir(path)

        self.write("/Linux", "ELKS KERNEL IMAGE")
        self.write("/bootopts", "# ELKS boot options\n")
        self.write("/etc/hostname", "elks\n")

        self.write("/etc/issue",
            "ELKS 0.9.2 \\n \\l\n"
        )

        self.write("/etc/motd",
            "Welcome to ELKS.\n"
            "Embeddable Linux Kernel Subset.\n"
        )

        self.write("/etc/passwd",
            "root:x:0:0:root:/root:/bin/sh\n"
            "toor:x:0:0:root:/root:/bin/sash\n"
        )

        self.write("/etc/inittab",
            "id:1:initdefault:\n"
            "c1:15:respawn:/bin/getty /dev/tty1\n"
        )

        self.write("/etc/profile",
            "PATH=/bin:/usr/bin:/sbin\n"
            "HOME=/root\n"
            "TERM=ansi\n"
        )

        self.write("/etc/rc.sys",
            "#!/bin/sh\n"
            "echo Starting system initialization\n"
            "mount -a\n"
        )

        self.write("/etc/mount.cfg", "")
        self.write("/etc/net.cfg", "")
        self.write("/var/log/messages", "")

        commands = [
            "ash", "sh", "sash", "init", "getty",
            "login", "ls", "cat", "echo", "pwd",
            "cd", "mkdir", "rmdir", "rm", "cp",
            "mv", "touch", "more", "grep", "mount",
            "umount", "sync", "reboot", "shutdown",
            "ps", "meminfo", "uname", "date",
            "df", "du", "free", "printenv", "env",
            "hostname", "whoami", "id", "kill",
            "sleep", "true", "false", "which",
            "find", "head", "tail", "wc", "sort",
            "init", "mount", "net", "netstat",
            "arp", "telnet", "ftp", "ping",
            "ifconfig", "fdisk", "mkfs", "mkfat",
            "sys", "man", "vi", "kilo", "chmem",
            "tty", "time", "hd", "uname", "dmesg"
        ]

        for command in commands:
            self.write("/bin/" + command, "[ELKS executable]")

        for device in [
            "console", "tty1", "tty2", "tty3",
            "ttyS0", "ttyS1", "ttyS2", "ttyS3",
            "fd0", "fd1", "hda", "hda1",
            "hda2", "hdb", "hdb1", "hdc",
            "rd0", "rd1", "ssd", "null",
            "zero", "mem", "port"
        ]:
            self.write("/dev/" + device, "")

    def normalize(self, path, cwd="/"):
        if not path:
            return cwd

        if not path.startswith("/"):
            path = cwd.rstrip("/") + "/" + path

        parts = []

        for part in path.split("/"):
            if part in ("", "."):
                continue

            if part == "..":
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

        if parent not in self.dirs:
            return False

        if self.exists(path):
            return False

        self.dirs.add(path)
        return True

    def write(self, path, data):
        path = self.normalize(path)
        parent = path.rsplit("/", 1)[0] or "/"

        if parent not in self.dirs or path in self.dirs:
            return False

        self.files[path] = str(data)
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

            for item in self.files.keys() | self.dirs:
                if item.startswith(prefix):
                    return False

            self.dirs.remove(path)
            return True

        return False

    def listdir(self, path):
        path = self.normalize(path)

        if path not in self.dirs:
            return None

        result = []

        for item in self.dirs | self.files.keys():
            if item == "/":
                continue

            parent = item.rsplit("/", 1)[0] or "/"

            if parent == path:
                result.append(item.rsplit("/", 1)[-1])

        return sorted(set(result))

    def copy(self, src, dst):
        data = self.read(src)

        if data is None:
            return False

        return self.write(dst, data)

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
# ELKS KERNEL
# ============================================================

class Kernel:

    def __init__(self):
        self.logs = deque(maxlen=500)
        self.processes = []
        self.pid = 1

        self.runlevel = 1
        self.boot_time = time.monotonic()

        self.memory_total = RAM
        self.memory_used = 176 * 1024

        self.heap_used = HEAP_SIZE

        self.hostname = HOSTNAME
        self.root_device = "/dev/fd0"
        self.filesystem = "Minix V1"

    def log(self, text):
        elapsed = time.monotonic() - self.boot_time

        line = f"[{elapsed:6.2f}] {text}"
        self.logs.append(line)

        print(line)

    def add_process(self, name, user="root", tty="", state="S"):
        self.processes.append({
            "pid": self.pid,
            "grp": self.pid,
            "tty": tty,
            "user": user,
            "state": state,
            "cpu": random.randint(0, 3),
            "heap": random.randint(0, 2048),
            "free": random.randint(1000, 4000),
            "size": random.randint(8000, 16000),
            "name": name
        })

        self.pid += 1

    def boot(self):

        self.boot_time = time.monotonic()

        # ----------------------------------------------------
        # BIOS
        # ----------------------------------------------------

        print(CYAN + BOLD + "SeaBIOS (version rel-1.16.3)" + RESET)
        print("Machine UUID 00000000-0000-0000-0000-000000000000")
        print("iPXE (http://ipxe.org)")

        sleep()

        print("Booting from Hard Disk...")
        sleep()

        # ----------------------------------------------------
        # BOOTLOADER
        # ----------------------------------------------------

        print()
        print("ELKS boot loader")

        print("Loading /Linux", end=" ")

        for _ in range(12):
            print(".", end="", flush=True)
            sleep(0.025)

        print()
        print("Loading boot options...")
        sleep()

        # ----------------------------------------------------
        # KERNEL
        # ----------------------------------------------------

        print()
        print("ELKS " + KERNEL_VERSION)
        print("Copyright (C) ELKS contributors")
        print()

        self.log("ELKS kernel " + KERNEL_VERSION)
        self.log("CPU: Intel 8086 compatible processor")
        self.log("CPU: 16-bit real mode")
        self.log("Memory: 640 KB conventional memory")
        self.log("Memory: 655360 bytes available")
        self.log("Initializing kernel heap")
        self.log("Kernel heap initialized")
        self.log("Initializing task table")
        self.log("Initializing scheduler")
        self.log("Initializing timer")
        self.log("Initializing interrupt handlers")
        self.log("Initializing console driver")
        self.log("Console: tty1")
        self.log("Initializing keyboard driver")
        self.log("Keyboard: PC/XT compatible")
        self.log("Initializing floppy disk driver")
        self.log("fd0: 1.44 MB floppy disk")
        self.log("Initializing hard disk driver")
        self.log("hda: virtual hard disk")
        self.log("Initializing block devices")
        self.log("Initializing character devices")
        self.log("Initializing TTY subsystem")
        self.log("Initializing buffer cache")
        self.log("Initializing filesystem subsystem")
        self.log("VFS: root device " + self.root_device)
        self.log("MINIX filesystem detected")
        self.log("VFS: Mounted root filesystem")
        self.log("Root filesystem mounted read-write")
        self.log("Freeing unused kernel memory")

        # ----------------------------------------------------
        # INIT
        # ----------------------------------------------------

        print()

        self.log("Starting /bin/init")
        self.log("init: reading /etc/inittab")
        self.log("init: default runlevel 1")
        self.log("init: executing /etc/rc.sys")

        self.log("rc.sys: system initialization complete")
        self.log("init: starting console getty")

        self.add_process("/bin/init 1")
        self.add_process("/bin/getty /dev/tty1")

        self.log("init: system ready")

        print()


# ============================================================
# ELKS SHELL
# ============================================================

class ELKS:

    def __init__(self):
        self.fs = FileSystem()
        self.kernel = Kernel()

        self.user = "root"
        self.uid = 0

        self.cwd = "/root"
        self.shell = "/bin/sh"

        self.env = {
            "HOME": "/root",
            "USER": "root",
            "SHELL": "/bin/sh",
            "PATH": "/bin:/usr/bin:/sbin",
            "HOSTNAME": HOSTNAME,
            "TERM": "ansi"
        }

        self.history = []
        self.running = True
        self.reboot_requested = False

    def resolve(self, path):
        return self.fs.normalize(path, self.cwd)

    def error(self, text):
        print(text)

    def prompt(self):
        symbol = "#" if self.uid == 0 else "$"

        return (
            CYAN + self.env["HOSTNAME"] +
            RESET + symbol + " "
        )

    # ========================================================
    # FILESYSTEM
    # ========================================================

    def cmd_ls(self, args):
        path = self.resolve(args[0]) if args else self.cwd

        items = self.fs.listdir(path)

        if items is None:
            self.error("ls: cannot access " + path)
            return

        for item in items:
            full = self.resolve(path + "/" + item)

            if full in self.fs.dirs:
                print(BLUE + item + "/" + RESET, end="  ")
            else:
                print(item, end="  ")

        print()

    def cmd_cd(self, args):
        path = args[0] if args else self.env["HOME"]
        target = self.resolve(path)

        if target not in self.fs.dirs:
            self.error("cd: " + path + ": not a directory")
            return

        self.cwd = target

    def cmd_pwd(self, args):
        print(self.cwd)

    def cmd_cat(self, args):
        if not args:
            self.error("cat: missing operand")
            return

        for path in args:
            data = self.fs.read(self.resolve(path))

            if data is None:
                self.error("cat: " + path + ": No such file")
            else:
                print(data, end="")

        print()

    def cmd_touch(self, args):
        for path in args:
            target = self.resolve(path)

            if not self.fs.exists(target):
                if not self.fs.write(target, ""):
                    self.error("touch: cannot create " + path)

    def cmd_mkdir(self, args):
        for path in args:
            if not self.fs.mkdir(self.resolve(path)):
                self.error("mkdir: cannot create " + path)

    def cmd_rmdir(self, args):
        for path in args:
            if not self.fs.remove(self.resolve(path)):
                self.error("rmdir: failed to remove " + path)

    def cmd_rm(self, args):
        for path in args:
            if not self.fs.remove(self.resolve(path)):
                self.error("rm: cannot remove " + path)

    def cmd_cp(self, args):
        if len(args) != 2:
            self.error("usage: cp source destination")
            return

        if not self.fs.copy(
            self.resolve(args[0]),
            self.resolve(args[1])
        ):
            self.error("cp: failed")

    def cmd_mv(self, args):
        if len(args) != 2:
            self.error("usage: mv source destination")
            return

        if not self.fs.move(
            self.resolve(args[0]),
            self.resolve(args[1])
        ):
            self.error("mv: failed")

    def cmd_find(self, args):
        root = self.resolve(args[0]) if args else self.cwd

        if root not in self.fs.dirs:
            self.error("find: invalid path")
            return

        def walk(path):
            for item in self.fs.listdir(path) or []:
                full = self.resolve(path + "/" + item)
                print(full)

                if full in self.fs.dirs:
                    walk(full)

        walk(root)

    # ========================================================
    # FILE UTILITIES
    # ========================================================

    def cmd_grep(self, args):
        if len(args) < 2:
            self.error("usage: grep pattern file")
            return

        pattern = args[0]
        data = self.fs.read(self.resolve(args[1]))

        if data is None:
            self.error("grep: cannot open " + args[1])
            return

        for line in data.splitlines():
            if pattern in line:
                print(line)

    def cmd_head(self, args):
        if not args:
            return

        data = self.fs.read(self.resolve(args[0]))

        if data is not None:
            print("\n".join(data.splitlines()[:10]))

    def cmd_tail(self, args):
        if not args:
            return

        data = self.fs.read(self.resolve(args[0]))

        if data is not None:
            print("\n".join(data.splitlines()[-10:]))

    def cmd_wc(self, args):
        if not args:
            return

        data = self.fs.read(self.resolve(args[0]))

        if data is not None:
            lines = data.splitlines()
            print(len(lines), len(data.split()), len(data), args[0])

    def cmd_more(self, args):
        self.cmd_cat(args)

    def cmd_echo(self, args):
        print(" ".join(args))

    # ========================================================
    # SYSTEM INFORMATION
    # ========================================================

    def cmd_uname(self, args):
        if "-a" in args:
            print(
                f"ELKS {HOSTNAME} {VERSION} "
                f"{ARCH} 8086"
            )
        else:
            print("ELKS")

    def cmd_hostname(self, args):
        print(self.env["HOSTNAME"])

    def cmd_whoami(self, args):
        print(self.user)

    def cmd_id(self, args):
        print(f"uid={self.uid}({self.user})")

    def cmd_date(self, args):
        print(datetime.datetime.now().strftime(
            "%a %b %d %H:%M:%S %Y"
        ))

    def cmd_printenv(self, args):
        for key, value in self.env.items():
            print(f"{key}={value}")

    def cmd_meminfo(self, args):
        used = self.kernel.memory_used
        free = RAM - used

        print("  HEAP   TYPE  SIZE")
        print("  eb8a   SEG     12")
        print("  eb9e   SEG     12")
        print("  ec02   TTY    128")
        print("  ec8a   TTY     64")
        print("  ecd2   SEG     12")
        print("  f102   TTY     64")
        print()
        print(f"Total heap   {self.kernel.heap_used}")
        print(f"Total mem    {RAM}")
        print(
            f"Memory usage {RAM // 1024}KB total, "
            f"{used // 1024}KB used, "
            f"{free // 1024}KB free"
        )

    def cmd_ps(self, args):
        print(
            "  PID   GRP  TTY USER STAT CPU  "
            "HEAP  FREE   SIZE COMMAND"
        )

        for p in self.kernel.processes:
            print(
                f"{p['pid']:5} "
                f"{p['grp']:5} "
                f"{p['tty']:4} "
                f"{p['user']:<5} "
                f"{p['state']:4} "
                f"{p['cpu']:3} "
                f"{p['heap']:5} "
                f"{p['free']:5} "
                f"{p['size']:6} "
                f"{p['name']}"
            )

    def cmd_df(self, args):
        print("Filesystem     Size  Used Avail Mounted on")
        print("/dev/fd0       1.4M  620K  820K /")

    def cmd_du(self, args):
        print("Filesystem usage: simulated")

    def cmd_free(self, args):
        self.cmd_meminfo(args)

    def cmd_tty(self, args):
        print("/dev/tty1")

    def cmd_dmesg(self, args):
        for line in self.kernel.logs:
            print(line)

    # ========================================================
    # PROCESS / SYSTEM MANAGEMENT
    # ========================================================

    def cmd_sync(self, args):
        print("sync: buffers synchronized")

    def cmd_reboot(self, args):
        print("Rebooting system...")
        self.running = False
        self.reboot_requested = True

    def cmd_shutdown(self, args):
        print("System halted.")
        self.running = False
        self.reboot_requested = False

    def cmd_sleep(self, args):
        duration = float(args[0]) if args else 1
        time.sleep(min(duration, 10))

    def cmd_true(self, args):
        pass

    def cmd_false(self, args):
        pass

    def cmd_which(self, args):
        if not args:
            return

        path = "/bin/" + args[0]

        if self.fs.exists(path):
            print(path)
        else:
            print(args[0] + ": not found")

    # ========================================================
    # FILESYSTEM MOUNTING
    # ========================================================

    def cmd_mount(self, args):
        if not args:
            for mount, device in self.fs.mounts.items():
                print(f"{device} on {mount} type {self.kernel.filesystem}")
            return

        if len(args) < 2:
            self.error("usage: mount device directory")
            return

        device = args[0]
        target = self.resolve(args[1])

        if target not in self.fs.dirs:
            self.error("mount: mount point does not exist")
            return

        self.fs.mounts[target] = device
        print(f"mount: {device} mounted on {target}")

    def cmd_umount(self, args):
        if not args:
            self.error("usage: umount device")
            return

        device = args[0]

        for mount, mounted_device in list(self.fs.mounts.items()):
            if mounted_device == device:
                if mount == "/":
                    self.error("umount: cannot unmount root")
                    return

                del self.fs.mounts[mount]
                print("umount: " + device + " unmounted")
                return

        self.error("umount: device not mounted")

    # ========================================================
    # INIT / RUNLEVELS
    # ========================================================

    def cmd_init(self, args):
        if not args:
            print("init: usage: init runlevel")
            return

        try:
            level = int(args[0])
        except ValueError:
            self.error("init: invalid runlevel")
            return

        if level < 1 or level > 6:
            self.error("init: invalid runlevel")
            return

        self.kernel.runlevel = level
        print(f"init: switching to runlevel {level}")

        if level == 1:
            print("init: single-user console")
        elif level == 2:
            print("init: single-user serial")
        elif level == 3:
            print("init: multiuser console and serial")
        elif level == 4:
            print("init: multiuser serial")
        elif level == 5:
            print("init: multiuser console")
        elif level == 6:
            print("init: all consoles and serial ports")

    # ========================================================
    # NETWORKING
    # ========================================================

    def cmd_net(self, args):
        if args and args[0] == "start":
            print("Starting networking on ne0")
            print("ktcp: network interface initialized")
            print("ktcp: ip 10.0.2.15")
            print("ktcp: gateway 10.0.2.2")
            print("Starting daemons 'telnetd' 'ftpd -d'")
        elif args and args[0] == "stop":
            print("Stopping networking")
        else:
            print("usage: net start | stop")

    def cmd_netstat(self, args):
        print("Active Internet connections")
        print("Proto Local Address Foreign Address State")
        print("tcp   0.0.0.0:23    0.0.0.0:*       LISTEN")

    def cmd_arp(self, args):
        print("IP address       HW type     HW address")
        print("10.0.2.2         ether       52:55:0a:00:02:02")

    def cmd_ifconfig(self, args):
        print("ne0: flags=UP,BROADCAST,RUNNING")
        print("     inet 10.0.2.15")
        print("     netmask 255.255.255.0")

    # ========================================================
    # PRIVILEGES
    # ========================================================

    def cmd_su(self, args):
        self.user = "root"
        self.uid = 0
        self.env["USER"] = "root"
        self.env["HOME"] = "/root"
        self.cwd = "/root"

    # ========================================================
    # SHELL
    # ========================================================

    def cmd_help(self, args):
        print("""
ELKS shell

Filesystem:
  ls       cd       pwd      cat
  mkdir    rmdir    rm       cp
  mv       touch    find     grep
  head     tail     more     wc

System:
  uname    hostname whoami   id
  date     ps       meminfo  dmesg
  df       du       mount    umount
  sync     init     reboot   shutdown

Network:
  net      netstat  arp      ifconfig

Shell:
  echo     printenv env      which
  sleep    true     false    help
  su       exit
""")

    def cmd_export(self, args):
        if not args or "=" not in args[0]:
            self.error("usage: export NAME=value")
            return

        key, value = args[0].split("=", 1)
        self.env[key] = value

    def cmd_history(self, args):
        for i, command in enumerate(self.history, 1):
            print(f"{i:4} {command}")

    def cmd_clear(self, args):
        clear()

    def cmd_exit(self, args):
        self.running = False

    # ========================================================
    # COMMAND DISPATCH
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
            "ls": self.cmd_ls,
            "cd": self.cmd_cd,
            "pwd": self.cmd_pwd,
            "cat": self.cmd_cat,
            "touch": self.cmd_touch,
            "mkdir": self.cmd_mkdir,
            "rmdir": self.cmd_rmdir,
            "rm": self.cmd_rm,
            "cp": self.cmd_cp,
            "mv": self.cmd_mv,
            "find": self.cmd_find,
            "grep": self.cmd_grep,
            "head": self.cmd_head,
            "tail": self.cmd_tail,
            "wc": self.cmd_wc,
            "more": self.cmd_more,
            "echo": self.cmd_echo,
            "uname": self.cmd_uname,
            "hostname": self.cmd_hostname,
            "whoami": self.cmd_whoami,
            "id": self.cmd_id,
            "date": self.cmd_date,
            "printenv": self.cmd_printenv,
            "env": self.cmd_printenv,
            "meminfo": self.cmd_meminfo,
            "free": self.cmd_free,
            "ps": self.cmd_ps,
            "df": self.cmd_df,
            "du": self.cmd_du,
            "tty": self.cmd_tty,
            "dmesg": self.cmd_dmesg,
            "sync": self.cmd_sync,
            "reboot": self.cmd_reboot,
            "shutdown": self.cmd_shutdown,
            "sleep": self.cmd_sleep,
            "true": self.cmd_true,
            "false": self.cmd_false,
            "which": self.cmd_which,
            "mount": self.cmd_mount,
            "umount": self.cmd_umount,
            "init": self.cmd_init,
            "net": self.cmd_net,
            "netstat": self.cmd_netstat,
            "arp": self.cmd_arp,
            "ifconfig": self.cmd_ifconfig,
            "su": self.cmd_su,
            "help": self.cmd_help,
            "export": self.cmd_export,
            "history": self.cmd_history,
            "clear": self.cmd_clear,
            "exit": self.cmd_exit
        }

        if name in commands:
            commands[name](args)
            return

        if self.fs.exists(self.resolve(name)):
            print(name + ": cannot execute simulated binary")
            return

        self.error(name + ": command not found")


# ============================================================
# LOGIN / BOOT
# ============================================================

def main():

    while True:
        system = ELKS()

        system.kernel.boot()

        print()
        print(system.fs.read("/etc/issue"), end="")

        print("elks login: ", end="", flush=True)

        try:
            username = input().strip()
        except (EOFError, KeyboardInterrupt):
            break

        if username not in ("root", "toor", "user"):
            print("Login incorrect")
            continue

        system.user = "root" if username == "root" else username
        system.uid = 0 if username in ("root", "toor") else 1000

        if username == "toor":
            system.shell = "/bin/sash"

        print()
        print(system.fs.read("/etc/motd"))
        print()

        system.kernel.add_process(
            "-" + system.shell,
            system.user,
            "1"
        )

        while system.running:
            try:
                command = input(system.prompt())
                system.execute(command)

            except KeyboardInterrupt:
                print("^C")

            except EOFError:
                system.running = False

        if not system.reboot_requested:
            break


main()
