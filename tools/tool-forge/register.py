#!/usr/bin/env python3
"""
Forge Register — zapíše validní nástroj do manifest.json a provede git commit.
Spuštění: python3 register.py <cesta_k_tool_složce>
Vždy spouštěj AŽ PO úspěšném validate.py.
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).parent.parent.parent
MANIFEST     = TOOLKIT_ROOT / "manifest.json"
VALIDATE     = Path(__file__).parent / "validate.py"

def load_yaml(path: Path) -> dict:
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        # minimální fallback
        data = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip() or line.startswith(" "):
                continue
            k, _, v = line.partition(":")
            data[k.strip()] = v.strip().strip('"')
        return data

def run_validate(tool_dir: Path) -> bool:
    result = subprocess.run(
        [sys.executable, str(VALIDATE), str(tool_dir)],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return False
    return True

def register(tool_dir: Path):
    # Znovu validuj
    print("Spouštím validaci před registrací...")
    if not run_validate(tool_dir):
        print("✗ Registrace zrušena — nástroj neprošel validací.")
        sys.exit(1)

    meta = load_yaml(tool_dir / "tool.yaml")
    name = meta.get("name", tool_dir.name)

    # Relativní cesta k tool_dir
    try:
        rel = tool_dir.relative_to(TOOLKIT_ROOT)
    except ValueError:
        rel = Path("tools") / tool_dir.name

    meta["tool_dir"] = str(rel).replace("\\", "/")

    # Oprav call — nahraď absolutní cestu za {tool_dir} pokud ji agent zapsal absolutně
    if "call" in meta:
        abs_str = str(tool_dir).replace("\\", "/")
        meta["call"] = meta["call"].replace(abs_str, "{tool_dir}")

    # Načti manifest
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["tools"] = [t for t in manifest["tools"] if t.get("name") != name]
    manifest["tools"].append(meta)

    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"✓ Zapsáno do manifest.json [{name}]")

    # Git commit + push
    cmds = [
        ["git", "-C", str(TOOLKIT_ROOT), "add", "."],
        ["git", "-C", str(TOOLKIT_ROOT), "commit", "-m",
         f"forge: add {name} ({date.today()})"],
        ["git", "-C", str(TOOLKIT_ROOT), "push"],
    ]
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in r.stdout:
            print(f"⚠ {' '.join(cmd[2:])}: {r.stderr.strip() or r.stdout.strip()}")
        else:
            print(f"✓ {cmd[2]}: OK")

    print(f"\n✅ Nástroj '{name}' zaregistrován a pushnut na GitHub.")

def main():
    if len(sys.argv) < 2:
        print("Použití: python3 register.py <cesta_ke_složce_nástroje>")
        sys.exit(1)

    tool_dir = Path(sys.argv[1])
    if not tool_dir.is_absolute():
        tool_dir = (TOOLKIT_ROOT / tool_dir)
    tool_dir = tool_dir.resolve()

    if not tool_dir.exists():
        print(f"Složka neexistuje: {tool_dir}")
        sys.exit(1)

    register(tool_dir)

if __name__ == "__main__":
    main()
