"""Extract package names an LLM tells the user to install or import."""
import re
import sys

# Import names that differ from their PyPI distribution names.
PY_IMPORT_ALIASES = {
    "cv2": "opencv-python", "yaml": "pyyaml", "sklearn": "scikit-learn",
    "PIL": "pillow", "bs4": "beautifulsoup4", "dotenv": "python-dotenv",
    "jwt": "pyjwt", "dateutil": "python-dateutil", "Crypto": "pycryptodome",
    "serial": "pyserial", "usb": "pyusb", "magic": "python-magic",
    "attr": "attrs", "google": None, "docx": "python-docx", "pptx": "python-pptx",
    "jose": "python-jose", "multipart": "python-multipart", "socketio": "python-socketio",
    "OpenSSL": "pyopenssl", "smbus2": "smbus2", "smbus": "smbus", "RPi": "rpi-gpio",
    "fitz": "pymupdf", "skimage": "scikit-image", "Evtx": "python-evtx",
    "evtx": "evtx", "stix2": "stix2", "pyshark": "pyshark", "board": "adafruit-blinka",
    "busio": "adafruit-blinka", "digitalio": "adafruit-blinka", "pymodbus": "pymodbus",
    "lief": "lief", "pefile": "pefile", "yara": "yara-python", "astropy": "astropy",
    "Levenshtein": "levenshtein", "zmq": "pyzmq", "git": "gitpython",
    "kiutils": "kiutils", "pyvisa": "pyvisa", "can": "python-can", "dns": "dnspython",
    "mitreattack": "mitreattack-python", "lorawan": "lorawan", "pydantic_settings": "pydantic-settings",
}
PY_STDLIB = set(sys.stdlib_module_names) | {"__future__"}

NODE_BUILTINS = {
    "fs", "path", "http", "https", "crypto", "os", "url", "util", "stream", "events",
    "child_process", "buffer", "net", "tls", "dns", "zlib", "readline", "assert",
    "querystring", "worker_threads", "cluster", "process", "timers", "vm", "perf_hooks",
    "string_decoder", "dgram", "module", "v8", "tty", "async_hooks", "inspector", "test",
}

CODE_BLOCK = re.compile(r"```[^\n]*\n(.*?)```", re.S)
INLINE_CODE = re.compile(r"`([^`\n]+)`")
PIP_LINE = re.compile(r"\bpip3?[ \t]+install[ \t]+([^\n`#&|;]+)")
NPM_LINE = re.compile(r"\b(?:npm[ \t]+(?:install|i|add)|yarn[ \t]+add|pnpm[ \t]+add)[ \t]+([^\n`#&|;]+)")
PY_IMPORT = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w]*)[\w.]*\s+import|import\s+([A-Za-z_][\w]*))", re.M)
JS_IMPORT = re.compile(r"""(?:require\(\s*|from\s+|import\s+)['"]([^'"]+)['"]""")


def _clean_pip_token(tok):
    tok = tok.strip().strip("'\"")
    if not tok or tok.startswith("-") or "/" in tok or tok.startswith("."):
        return None
    tok = re.split(r"[\[<>=!~;@ ]", tok)[0]
    return tok if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", tok) else None


def _clean_npm_token(tok):
    tok = tok.strip().strip("'\"")
    if not tok or tok.startswith("-"):
        return None
    if tok.startswith("@"):
        m = re.match(r"(@[\w.-]+/[\w.-]+)", tok)
        return m.group(1).lower() if m else None
    name = tok.split("@")[0]
    return name.lower() if re.fullmatch(r"[a-z0-9][\w.-]*", name, re.I) else None


def _js_root(spec):
    """Package root of a module specifier: 'lodash/fp' -> 'lodash', '@a/b/c' -> '@a/b'."""
    if spec.startswith((".", "/", "node:")):
        return None
    parts = spec.split("/")
    root = "/".join(parts[:2]) if spec.startswith("@") else parts[0]
    if root in NODE_BUILTINS:
        return None
    return root.lower()


# Options whose next token is a value (file, URL, path), not a package.
OPTS_WITH_VALUE = {
    "-r", "--requirement", "-c", "--constraint", "-e", "--editable", "-i", "--index-url",
    "--extra-index-url", "-f", "--find-links", "-t", "--target", "--prefix", "--root",
    "--registry", "--prefix", "-w", "--workspace",
}


def _args(line):
    """Split an install command's arguments, dropping option values."""
    toks, skip = [], False
    for tok in line.split():
        if skip:
            skip = False
        elif tok in OPTS_WITH_VALUE:
            skip = True
        else:
            toks.append(tok)
    return toks


def extract(text, lang):
    """Return {'install': set, 'import': set} of package names in registry form."""
    install, imported = set(), set()
    # Only trust install commands written as code, not prose like "pip install X or Y".
    commands = "\n".join(CODE_BLOCK.findall(text) + INLINE_CODE.findall(text))
    if lang == "python":
        for line in PIP_LINE.findall(commands):
            install.update(filter(None, map(_clean_pip_token, _args(line))))
        code = "\n".join(CODE_BLOCK.findall(text)) or text
        for a, b in PY_IMPORT.findall(code):
            mod = a or b
            if mod in PY_STDLIB:
                continue
            name = PY_IMPORT_ALIASES.get(mod, mod)
            if name:
                imported.add(name)
    else:
        for line in NPM_LINE.findall(commands):
            install.update(filter(None, map(_clean_npm_token, _args(line))))
        code = "\n".join(CODE_BLOCK.findall(text)) or text
        imported.update(filter(None, map(_js_root, JS_IMPORT.findall(code))))
    return {"install": install, "import": imported}
