#!/usr/bin/env python3
"""
Forge Validator — ověří že tool splňuje všechny forge-conditions.
Spuštění: python3 validate.py <cesta_k_tool_složce>
Exit 0 = valid, Exit 1 = invalid (s popisem chyb)
"""
import json
import re
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).parent.parent.parent
MANIFEST     = TOOLKIT_ROOT / "manifest.json"
CONDITIONS   = Path(__file__).parent / "forge-conditions.yaml"

VERB_HINT = {
    "cs": re.compile(r"^[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]", re.UNICODE),
    "en": re.compile(r"^[A-Z][a-z]"),
}
SNAKE_CASE  = re.compile(r"^[a-z][a-z0-9_-]*$")  # snake_case + kebab-case
UNFILLED    = re.compile(r"\{\{[^}]+\}\}")

errors   = []
warnings = []

def err(msg):  errors.append(f"  ✗ {msg}")
def warn(msg): warnings.append(f"  ⚠ {msg}")
def ok(msg):   print(f"  ✓ {msg}")

def load_yaml_simple(path: Path) -> dict:
    """Minimální YAML parser pro tool.yaml — bez závislosti na pyyaml."""
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        pass
    # fallback: parsuj jen top-level klíče
    data = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            data[k.strip()] = v.strip().strip('"')
    return data

def check_required_files(tool_dir: Path):
    if not (tool_dir / "tool.yaml").exists():
        err("Chybí tool.yaml")
        return False

    has_impl = any((tool_dir / f"run.{ext}").exists() for ext in ["ps1", "py", "js"])
    if not has_impl:
        err("Chybí implementace: run.ps1, run.py nebo run.js")
        return False

    ok("Povinné soubory přítomny")
    return True

def check_tool_yaml(tool_dir: Path) -> dict | None:
    path = tool_dir / "tool.yaml"
    try:
        meta = load_yaml_simple(path)
    except Exception as e:
        err(f"tool.yaml nelze parsovat: {e}")
        return None

    required = ["name", "description", "inputs", "outputs", "call", "tags", "tested"]
    missing  = [f for f in required if f not in meta or meta[f] is None]
    if missing:
        err(f"Chybí povinná pole v tool.yaml: {', '.join(missing)}")
    else:
        ok("Všechna povinná pole přítomna")

    # description
    desc = str(meta.get("description", ""))
    if len(desc) > 120:
        err(f"description je příliš dlouhý ({len(desc)} znaků, max 120)")
    if desc and not (VERB_HINT["cs"].match(desc) or VERB_HINT["en"].match(desc)):
        warn("description by měl začínat slovesem (velké písmeno)")
    if UNFILLED.search(desc):
        err("description obsahuje nevyplněné placeholdery {{...}}")

    # name
    name = str(meta.get("name", ""))
    if not SNAKE_CASE.match(name):
        err(f"name '{name}' není snake_case (pouze a-z, 0-9, _)")

    # call
    call = str(meta.get("call", ""))
    if "{tool_dir}" not in call:
        err("call musí obsahovat placeholder {tool_dir}")
    if UNFILLED.search(call):
        err("call obsahuje nevyplněné placeholdery {{...}}")

    # tags
    tags = meta.get("tags", [])
    if isinstance(tags, list):
        if len(tags) < 1: err("tags: alespoň 1 tag")
        if len(tags) > 5: warn("tags: více než 5 tagů (doporuč max 5)")
    else:
        err("tags musí být seznam")

    return meta

def check_unique_name(name: str):
    if not MANIFEST.exists():
        warn("manifest.json nenalezen — přeskakuji kontrolu unikátnosti")
        return
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    existing = [t["name"] for t in manifest.get("tools", [])]
    if name in existing:
        err(f"Nástroj '{name}' již existuje v manifest.json")
    else:
        ok(f"Název '{name}' je unikátní")

def check_implementation(tool_dir: Path):
    for ext in ["ps1", "py", "js"]:
        impl = tool_dir / f"run.{ext}"
        if impl.exists():
            content = impl.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                err(f"run.{ext} je prázdný")
                return
            if UNFILLED.search(content):
                err(f"run.{ext} obsahuje nevyplněné placeholdery {{{{...}}}}")
                return
            ok(f"Implementace run.{ext} OK ({len(content)} znaků)")
            return

def main():
    if len(sys.argv) < 2:
        print("Použití: python3 validate.py <cesta_ke_složce_nástroje>")
        sys.exit(1)

    tool_dir = Path(sys.argv[1])
    if not tool_dir.is_absolute():
        tool_dir = (TOOLKIT_ROOT / tool_dir)
    tool_dir = tool_dir.resolve()

    if not tool_dir.exists():
        print(f"Složka neexistuje: {tool_dir}")
        sys.exit(1)

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"\nValiduji: {tool_dir.name}")
    print("-" * 40)

    if not check_required_files(tool_dir):
        print("\n".join(errors))
        sys.exit(1)

    meta = check_tool_yaml(tool_dir)
    # uniqueness check je v register.py — při validaci přeskakujeme
    check_implementation(tool_dir)

    print()
    if warnings:
        print("Varování:")
        print("\n".join(warnings))

    if errors:
        print("\nCHYBY — nástroj není validní:")
        print("\n".join(errors))
        sys.exit(1)

    print("✅ Nástroj splňuje všechny forge conditions.")
    sys.exit(0)

if __name__ == "__main__":
    main()
