# Tool Forge — Protokol pro tvorbu MCP nástrojů

Tento dokument definuje **podmínky a postup**, které musí splnit každý agent
při vytváření nového nástroje. Forge **nepoužívá žádné API** — vytváří nástroj
ten agent, který má repozitář aktuálně načtený.

---

## Spuštění

Uživatel zavolá forge příkazem:

```
forge: <popis cíle nástroje>
```

nebo přes MCP tool `tool-forge` s parametrem `goal`.

Agent (= ty, kdo čteš tento dokument) musí:
1. Přečíst `forge-conditions.yaml` — podmínky validity
2. Zeptat se uživatele na chybějící informace (viz sekce Vstupní dialog)
3. Vytvořit soubory dle šablon v `template/`
4. Spustit `python3 validate.py <cesta>` — musí projít BEZ chyb
5. Spustit `python3 register.py <cesta>` — zapíše do manifest.json + git commit

**Nikdy nevytvářej nástroj bez úspěšné validace.**

---

## Vstupní dialog (povinný)

Před generováním se zeptej na:

| Pole | Povinné | Příklad |
|------|---------|---------|
| **goal** | ✓ | "Stáhni všechny obrázky z URL" |
| **start** | doporučeno | "Dostanu URL, výstupní složku" |
| **runtime** | ✓ | `ps1` \| `py` \| `js` |
| **constraints** | ne | "Bez externích závislostí" |

---

## Podmínky validity (forge-conditions)

Viz `forge-conditions.yaml`. Shrnutí:

1. Složka `tools/<name>/` existuje
2. Soubor `tool.yaml` obsahuje všechna povinná pole
3. `description` ≤ 120 znaků, začíná slovesem
4. `call` obsahuje `{tool_dir}` placeholder
5. `name` je snake_case, unikátní v manifest.json
6. Implementační soubor `run.<ext>` existuje
7. Implementace přijímá parametry, tiskne výsledek, ukončuje se exit kódem
8. Všechny required inputs mají `type` a `description`

---

## Šablony

Kopíruj z `template/tool.yaml.template` a `template/run.<ext>.template`.
Nevyplněné placeholdery `{{...}}` způsobí selhání validace.

---

## Postup po validaci

```
python3 C:\MCPToolkit\tools\tool-forge\register.py tools/<name>
```

Registrace: přidá záznam do `manifest.json`, provede `git add . && git commit && git push`.
