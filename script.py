print("pyscript.net is UP: Hosted on 'https://xxcoolgamerx2022x.github.io/pyboring/' (all rights reserved)")
print("Type 'help' to see browser and runtime diagnostics.")

"""A small read-only diagnostics shell for the PyScript-hosted web page.

This is not an operating-system shell. It does not execute OS commands,
inspect the host filesystem, or make network requests. Browser information is
read on a best-effort basis because PyScript may run this script in a worker,
where DOM access is unavailable.
"""

import ast
import datetime
import operator
import platform
import shlex
import sys
from urllib.parse import urlsplit

COMMAND_HISTORY = []

HELP = {
    "help": "help [command]       Show available commands or command help.",
    "about": "about                Explain what this browser shell can access.",
    "debug": "debug                Print a compact page/runtime diagnostic report.",
    "page": "page                 Show the current page URL, title, and load state.",
    "browser": "browser              Show browser capabilities and online status.",
    "runtime": "runtime              Show Python, Pyodide, and PyScript runtime details.",
    "resources": "resources [count]    List recent page resource timing entries.",
    "timing": "timing               Show navigation timing milestones.",
    "links": "links [count]         List links in the current page (if DOM access is available).",
    "history": "history              Show commands entered in this session.",
    "date": "date                 Show the current date and time.",
    "echo": "echo [text...]       Print text.",
    "calc": "calc <expression>    Safely calculate basic arithmetic.",
    "clear": "clear                Clear the terminal when ANSI is supported.",
    "exit": "exit                 End the shell session.",
    "quit": "quit                 Alias for exit.",
}


def _js_module():
    """Return Pyodide's JavaScript bridge, or None outside a browser runtime."""
    try:
        import js
        return js
    except Exception:
        return None


def _get(obj, name, default=None):
    try:
        value = getattr(obj, name)
        return default if value is None else value
    except Exception:
        return default


def _safe_url(value):
    """Hide URL query strings and fragments, which may contain private tokens."""
    text = str(value)
    try:
        parts = urlsplit(text)
        if not parts.scheme and not parts.netloc:
            return text
        shown = parts.scheme + ":"
        if parts.netloc:
            shown += "//" + parts.netloc
        shown += parts.path
        if parts.query:
            shown += "?[query omitted]"
        if parts.fragment:
            shown += "#[fragment omitted]"
        return shown
    except Exception:
        return "[URL unavailable]"


def _document():
    js = _js_module()
    return _get(js, "document") if js is not None else None


def _navigator():
    js = _js_module()
    return _get(js, "navigator") if js is not None else None


def _performance():
    js = _js_module()
    return _get(js, "performance") if js is not None else None


def _browser_unavailable():
    print("Page DOM APIs are unavailable in this execution context.")
    print("PyScript may be running this shell in a worker; runtime diagnostics still work.")


def command_page():
    js = _js_module()
    doc = _document()
    location = _get(js, "location") if js is not None else None
    if doc is None or location is None:
        _browser_unavailable()
        return
    print("URL:         {}".format(_safe_url(_get(location, "href", "unavailable"))))
    print("Origin:      {}".format(_get(location, "origin", "unavailable")))
    print("Title:       {}".format(_get(doc, "title", "")))
    print("Ready state: {}".format(_get(doc, "readyState", "unavailable")))
    print("Visibility:  {}".format(_get(doc, "visibilityState", "unavailable")))


def command_browser():
    nav = _navigator()
    if nav is None:
        _browser_unavailable()
        return
    print("Online:         {}".format(bool(_get(nav, "onLine", False))))
    print("Language:       {}".format(_get(nav, "language", "unavailable")))
    print("Platform hint:  {}".format(_get(nav, "platform", "unavailable")))
    print("Cookies enabled:{}".format(" {}".format(bool(_get(nav, "cookieEnabled", False)))))
    js = _js_module()
    print("Secure context: {}".format(bool(_get(js, "isSecureContext", False))))
    print("Cross-origin isolated: {}".format(bool(_get(js, "crossOriginIsolated", False))))
    connection = _get(nav, "connection")
    if connection is not None:
        print("Connection:     {} ({}); effective type {}".format(
            _get(connection, "type", "unknown"),
            _get(connection, "downlink", "unknown"),
            _get(connection, "effectiveType", "unknown"),
        ))


def command_runtime():
    print("Python:      {}".format(sys.version.split()[0]))
    print("Implementation: {}".format(platform.python_implementation()))
    print("Platform:    {}".format(platform.platform()))
    pyodide = sys.modules.get("pyodide")
    pyscript = sys.modules.get("pyscript")
    print("Pyodide:     {}".format(_get(pyodide, "__version__", "not detected")))
    print("PyScript:    {}".format(_get(pyscript, "__version__", "not detected")))
    print("Execution:   {}".format("browser JavaScript bridge available" if _js_module() else "Python-only context"))


def _resource_entries():
    performance = _performance()
    if performance is None:
        return None
    try:
        return performance.getEntriesByType("resource")
    except Exception:
        return None


def command_resources(count=20):
    entries = _resource_entries()
    if entries is None:
        _browser_unavailable()
        return
    try:
        length = len(entries)
    except Exception:
        length = int(_get(entries, "length", 0))
    if length == 0:
        print("No resource timing entries are available.")
        return
    start = max(0, length - count)
    for index in range(start, length):
        try:
            entry = entries[index]
            duration = float(_get(entry, "duration", 0))
            size = _get(entry, "transferSize")
            size_text = "unknown" if size is None else "{} B".format(size)
            status = _get(entry, "responseStatus")
            status_text = "" if not status else " status={}".format(status)
            print("{:.1f} ms  {:>10}  {}{}".format(
                duration, size_text, _get(entry, "initiatorType", "resource"), status_text
            ))
            print("  {}".format(_safe_url(_get(entry, "name", ""))))
        except Exception as error:
            print("Resource entry {} unavailable: {}".format(index, error))


def command_timing():
    performance = _performance()
    if performance is None:
        _browser_unavailable()
        return
    try:
        entries = performance.getEntriesByType("navigation")
        if len(entries) == 0:
            print("Navigation timing is not available.")
            return
        nav = entries[0]
        for label, field in (
            ("DNS lookup", "domainLookupEnd"),
            ("Connection established", "connectEnd"),
            ("Request started", "requestStart"),
            ("First response byte", "responseStart"),
            ("Response complete", "responseEnd"),
            ("DOM interactive", "domInteractive"),
            ("DOMContentLoaded", "domContentLoadedEventEnd"),
            ("Page load complete", "loadEventEnd"),
        ):
            value = float(_get(nav, field, 0) or 0)
            if value:
                print("{:<23} {:>9.1f} ms".format(label + ":", value))
            else:
                print("{:<23} unavailable (or not reached)".format(label + ":"))
    except Exception as error:
        print("timing: could not read navigation timing: {}".format(error))


def command_links(count=30):
    doc = _document()
    if doc is None:
        _browser_unavailable()
        return
    try:
        anchors = doc.querySelectorAll("a[href]")
        total = len(anchors)
        if total == 0:
            print("No links found on this page.")
            return
        for index in range(min(total, count)):
            anchor = anchors[index]
            label = " ".join(str(_get(anchor, "textContent", "")).split())
            href = _safe_url(_get(anchor, "href", ""))
            print("{}  {}".format(href, ("— " + label[:100]) if label else ""))
        if total > count:
            print("... {} more link(s); use 'links {}' to show more.".format(total - count, total))
    except Exception as error:
        print("links: could not inspect page links: {}".format(error))


def command_debug():
    print("=== Page ===")
    command_page()
    print("\n=== Browser ===")
    command_browser()
    print("\n=== Python runtime ===")
    command_runtime()
    print("\n=== Recent resources ===")
    command_resources(10)


def safe_calculate(expression):
    """Evaluate small arithmetic expressions without Python eval()."""
    if len(expression) > 200:
        raise ValueError("expression is too long")
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 40:
        raise ValueError("expression is too complex")
    operators = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod, ast.Pow: operator.pow,
        ast.UAdd: operator.pos, ast.USub: operator.neg,
    }

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in operators:
            return operators[type(node.op)](visit(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("exponent is too large (maximum absolute exponent is 10)")
            result = operators[type(node.op)](left, right)
            if isinstance(result, (int, float)) and (abs(result) > 1e100):
                raise ValueError("result is too large")
            return result
        raise ValueError("only numeric literals and +, -, *, /, //, %, ** are allowed")

    return visit(tree)


def run_command(command_line):
    try:
        args = shlex.split(command_line)
    except ValueError as error:
        print("parse error: {}".format(error))
        return True
    if not args:
        return True

    COMMAND_HISTORY.append(command_line)
    name, argv = args[0].lower(), args[1:]

    if name in ("exit", "quit"):
        print("Goodbye!")
        return False
    if name == "help":
        if argv:
            print(HELP.get(argv[0], "No help available for '{}'. Try 'help'.".format(argv[0])))
        else:
            print("Available commands (read-only PyScript/web diagnostics):")
            for key in sorted(HELP):
                print("  " + HELP[key])
        return True
    if name == "about":
        print("This shell runs as Python inside the PyScript web page.")
        print("It provides read-only page, browser, resource-timing, and runtime diagnostics.")
        print("It does not execute operating-system commands, make network requests, or access host files.")
        print("Some page details may be unavailable because this page runs Python in a worker.")
    elif name == "debug":
        command_debug()
    elif name == "page":
        command_page()
    elif name == "browser":
        command_browser()
    elif name == "runtime":
        command_runtime()
    elif name == "resources":
        if len(argv) > 1:
            print("usage: resources [count]")
        else:
            try:
                count = int(argv[0]) if argv else 20
                if count < 1 or count > 200:
                    raise ValueError
                command_resources(count)
            except ValueError:
                print("resources: count must be an integer from 1 to 200")
    elif name == "timing":
        command_timing()
    elif name == "links":
        if len(argv) > 1:
            print("usage: links [count]")
        else:
            try:
                count = int(argv[0]) if argv else 30
                if count < 1 or count > 200:
                    raise ValueError
                command_links(count)
            except ValueError:
                print("links: count must be an integer from 1 to 200")
    elif name == "history":
        for index, entry in enumerate(COMMAND_HISTORY, 1):
            print("{:>4}  {}".format(index, entry))
    elif name == "date":
        print(datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
    elif name == "echo":
        print(" ".join(argv))
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
    else:
        print("{}: command not found. Type 'help' for available commands.".format(name))
    return True


async def main():
    """Run the terminal loop with synchronous or awaitable PyScript input."""
    while True:
        try:
            # PyScript/Pyodide versions differ: terminal input may be returned
            # directly as text or as an awaitable. Only await the latter.
            pending_command = input("web $ ")
            if hasattr(pending_command, "__await__"):
                command = await pending_command
            else:
                command = pending_command
            if not run_command(command):
                break
        except EOFError:
            print("Terminal input is unavailable. Reload the page and keep this tab in focus.")
            break
        except KeyboardInterrupt:
            print("\nUse 'exit' to leave the shell.")
        except Exception as error:
            # Keep a bad diagnostic command from terminating the interactive shell.
            print("shell error: {}".format(error))


await main()
