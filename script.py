print("pyscript.net is UP: Hosted on 'https://xxcoolgamerx2022x.github.io/pyboring/' (all rights reserved)")
print("Type commands in the terminal below.")

while True:
    try:
        command = input("-$")
        print("received:", command)
    except EOFError:
        print("Terminal input is unavailable. Reload the page and keep this tab in focus.")
        break
