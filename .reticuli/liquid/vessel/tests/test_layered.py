"""The layered self-host: a component supplies *free code* to a dependent (not
just pinned data). `realize --recursive` rehydrates the component first and
threads its code up as a `from` produce step, so the dependent is a basin over
*both* implementations — the component's and its own — yet still lands on one
root. This is exactly the kernel-core -> whole shape the repo itself uses."""
import os
import shutil

from reticuli import kernel, pack, registry

LIB = "def val():\n    return 42\n"
APP = "from lib import val\n\n\ndef answer():\n    return val()\n"
LIB_CHECK = ("import sys\nsys.path.insert(0, '.')\nfrom lib import val\n"
             "assert val() == 42\n"
             "open('LIB_OK', 'w').write('lib-ok\\n')\n")
APP_CHECK = ("import sys\nsys.path.insert(0, '.')\nfrom app import answer\n"
             "assert answer() == 42\n"
             "open('APP_OK', 'w').write('app-ok\\n')\n")

# one producer, byte-different from the warm build but behaviour-identical; it
# regrows lib.py (for the component) and app.py (for the dependent)
PRODUCER = (
    'case "$RETICULI_OUTPUT" in '
    "lib.py) printf 'def val(): return 42  # regrown\\n' > lib.py ;; "
    "app.py) printf 'from lib import val\\ndef answer(): return val()  # regrown\\n' > app.py ;; "
    "esac"
)


def _write(d, files):
    os.makedirs(d, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(d, name), "w") as f:
            f.write(content)


def _build(tmp_path):
    lib = str(tmp_path / "libcode")
    _write(lib, {"lib.py": LIB, "lib_check.py": LIB_CHECK})
    rl = pack.pack(lib, "libcode", ["lib.py"], ["lib_check.py"], "python3 lib_check.py", "LIB_OK")

    app = str(tmp_path / "app")
    _write(app, {"lib.py": LIB, "app.py": APP, "app_check.py": APP_CHECK})
    shutil.copytree(lib, os.path.join(app, ".reticuli", "liquid", "libcode"))  # host the component
    comp = {"name": "libcode", "record": os.path.join(app, ".reticuli", "liquid", "libcode"),
            "outputs": ["lib.py"]}
    ra = pack.pack(app, "app", ["lib.py", "app.py"], ["app_check.py"],
                   "python3 app_check.py", "APP_OK", component=comp)
    return app, rl["root"], ra["root"]


def test_component_supplies_free_code_and_the_chain_reproduces(tmp_path):
    app, root_lib, root_app = _build(tmp_path)
    assert kernel.load_recipe(app)  # sanity

    into = str(tmp_path / "M3")
    out = registry.rehydrate(app, PRODUCER, into)

    # the component regrew, kernel-first, to its own claim
    assert any(c["component"] == "libcode" and c["root"] == root_lib
               for c in out["rehydrated_components"])
    # the whole chain lands on the dependent's one root...
    assert out["root"] == root_app == kernel.verify(app)["root"]
    # ...even though BOTH implementations are byte-different from the warm build
    assert kernel._hf(os.path.join(into, "app.py")) != kernel._hf(os.path.join(app, "app.py"))
    assert kernel._hf(os.path.join(into, "lib.py")) != kernel._hf(os.path.join(app, "lib.py"))
    # lib.py in the dependent is the code the component supplied (a free `from` step)
    assert kernel._hf(os.path.join(into, "lib.py")) == \
        kernel._hf(os.path.join(into, ".reticuli", "deps", "libcode", "lib.py"))


def test_editing_the_component_output_is_free_at_the_top(tmp_path):
    """lib.py is `from` the component (free), so the dependent's root does not
    move when the component's code changes — only its check would."""
    app, _root_lib, root_app = _build(tmp_path)
    with open(os.path.join(app, "lib.py"), "a") as f:
        f.write("# an edit to the supplied code (free)\n")
    # re-pack the dependent: the component link is unchanged, lib.py is free
    comp = {"name": "libcode", "record": os.path.join(app, ".reticuli", "liquid", "libcode"),
            "outputs": ["lib.py"]}
    again = pack.pack(app, "app", ["lib.py", "app.py"], ["app_check.py"],
                      "python3 app_check.py", "APP_OK", component=comp)
    assert again["root"] == root_app
