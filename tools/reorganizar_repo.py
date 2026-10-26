"""Reorganiza los archivos no-código del repositorio (sin tocar Python).

Por defecto SIMULA e imprime el plan. Para aplicar:

    python tools/reorganizar_repo.py --aplicar

- Dentro de un repositorio git usa `git mv` (conserva el historial); los archivos
  sin seguimiento (p. ej. ignorados) se mueven con el sistema de archivos.
- Es idempotente: lo ya movido se informa como "ya está" y no se repite.
- Nunca sobrescribe: si el destino existe, informa el conflicto y sigue.
- Actualiza enlaces solo en documentación vigente (README, docs/ y validacion/),
  nunca en las notas históricas ni en las entradas previas de CHANGELOG
  (se agrega una entrada nueva).
- No mueve código, datos de ejecución (data/settings.json, locations_*.csv,
  species_db.json), cuentas (users.db) ni requirements*.txt.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (origen, destino). Un origen terminado en "/" es una carpeta (se mueve archivo por archivo).
MOVES: list[tuple[str, str]] = [
    # --- evidencia de validación ---
    ("autocomprobacion_windows.json", "validacion/windows/2026-10-25_etapa4.3/autocomprobacion_windows.json"),
    ("escritorio_windows.json", "validacion/windows/2026-10-25_etapa4.3/escritorio_windows.json"),
    ("evidencia_4_3/", "validacion/qa_linux/etapa4.3/"),
    ("evidencia_4_2/", "validacion/qa_linux/etapa4.2/"),
    ("evidencia_actual/", "validacion/qa_linux/base_recibida/"),
    ("VALIDACION_ACTUAL.json", "validacion/estado_actual.json"),
    # --- campaña de campo y fotos reales ---
    ("data/plantilla_validacion_termica.csv", "validacion/campo/plantillas/plantilla_validacion_termica.csv"),
    ("data/plantilla_instrumentos_v16.csv", "validacion/campo/plantillas/plantilla_instrumentos_v16.csv"),
    ("data/plantilla_meteorologia_observada.csv", "validacion/campo/plantillas/plantilla_meteorologia_observada.csv"),
    ("data/validacion_fotos/manifest.plantilla.json", "validacion/fotos/manifest.plantilla.json"),
    # --- documentación ---
    ("INSTRUCCIONES_ACTUAL.md", "docs/releases/etapa4.3/INSTRUCCIONES.md"),
    ("preview_formas_copa_v35_4.png", "docs/imagenes/preview_formas_copa_v35_4.png"),
    ("smoke_anim3d_v35_2.png", "docs/imagenes/smoke_anim3d_v35_2.png"),
    ("cambios/", "docs/historico/cambios/"),
    # --- archivo histórico de etapas (raíz -> docs/historico) ---
    *[(f, f"docs/historico/etapas/{f}") for f in [
        "PRUEBAS_ETAPA1.txt", "PRUEBAS_ETAPA2.txt", "PRUEBAS_ETAPA2_FALLBACK.txt",
        "PRUEBAS_ETAPA3.txt", "PRUEBAS_ETAPA3_FALLBACK.txt", "PRUEBAS_ETAPA3_1.txt",
        "PRUEBAS_ETAPA3_1_FALLBACK.txt", "PRUEBAS_ETAPA3_2.txt", "PRUEBAS_ETAPA3_2_FALLBACK.txt",
        "REGRESION_ANTES_ETAPA3_1.txt", "REGRESION_ANTES_ETAPA3_2.txt", "REGRESION_DESPUES_ETAPA3_2.txt",
        "PROMPT_CONTINUIDAD_ETAPA1.txt", "PROMPT_CONTINUIDAD_ETAPA2.txt", "PROMPT_CONTINUIDAD_ETAPA3.txt",
        "PROMPT_CONTINUIDAD_ETAPA3_1.txt", "PROMPT_CONTINUIDAD_ETAPA3_2.txt",
        "VERIFICACION_FUENTES_ETAPA3.txt", "INSTALACION_QA_ETAPA3.txt", "DEPENDENCIAS_ETAPA3_2.txt",
    ]],
    *[(f, f"docs/historico/manifiestos/{f}") for f in [
        "MANIFIESTO_ETAPA2_SHA256.json", "MANIFIESTO_ETAPA3_SHA256.json",
        "MANIFIESTO_ETAPA3_1_SHA256.json", "MANIFIESTO_ETAPA3_2_SHA256.json",
        "MANIFIESTO_FUENTES_SHA256.json", "AUDITORIA_AUTOMATICA_v16.json", "AUDITORIA_AUTOMATICA_v16.txt",
    ]],
    # --- respaldos locales (ignorados por git) ---
    ("historial_git/", "respaldos/"),
]

# Reemplazos de texto en documentación vigente (de lo más largo a lo más corto).
LINK_REWRITES: list[tuple[str, str]] = [
    ("historial_git/Sombra_actual.bundle", "respaldos/Sombra_actual.bundle"),
    ("data/validacion_fotos/manifest.plantilla.json", "validacion/fotos/manifest.plantilla.json"),
    ("data/plantilla_", "validacion/campo/plantillas/plantilla_"),
    ("VALIDACION_ACTUAL.json", "validacion/estado_actual.json"),
    ("INSTRUCCIONES_ACTUAL.md", "docs/releases/etapa4.3/INSTRUCCIONES.md"),
    ("evidencia_4_3", "validacion/qa_linux/etapa4.3"),
    ("evidencia_4_2", "validacion/qa_linux/etapa4.2"),
    ("evidencia_actual", "validacion/qa_linux/base_recibida"),
    ("historial_git", "respaldos"),
]
CAMBIOS_RE = re.compile(r"(?<![\w/.-])cambios/")
DOC_GLOBS = ["README.md", "docs/*.md", "docs/releases/**/*.md", "validacion/**/*.md"]
# Documentos que citan rutas antiguas a propósito (tabla "antes -> ahora"): no se reescriben.
SKIP_REWRITE = {"docs/MAPA_DE_ARCHIVOS.md"}

CHANGELOG_MARK = "## Reorganización de archivos (sin cambio de versión)"
CHANGELOG_ENTRY = f"""{CHANGELOG_MARK}

- Solo se reubican archivos que ningún módulo ni prueba lee: evidencia de validación (`validacion/`), notas y manifiestos de etapas anteriores (`docs/historico/`), instrucciones por entrega (`docs/releases/`) e imágenes (`docs/imagenes/`). Código, `data/` de ejecución, cuentas y `requirements*.txt` no se tocan.
- Mapa completo de rutas antiguas y nuevas: [docs/MAPA_DE_ARCHIVOS.md](docs/MAPA_DE_ARCHIVOS.md). Las menciones a rutas antiguas en las entradas de abajo son históricas y se conservan.
- Hecho con `tools/reorganizar_repo.py` (usa `git mv`, conserva el historial).

"""
GITIGNORE_LINES = [
    "# Respaldos locales (bundle de git, copias): fuera del repositorio",
    "respaldos/",
    "# Datos crudos pesados de campañas (fotos originales, registros del datalogger): conservar fuera de git",
    "validacion/campo/campanias/**/crudos/",
]


def sh(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def in_git() -> bool:
    try:
        return (ROOT / ".git").exists() and sh("git", "rev-parse", "--is-inside-work-tree").returncode == 0
    except FileNotFoundError:
        return False


def tracked(rel: str) -> bool:
    return sh("git", "ls-files", "--error-unmatch", "--", rel).returncode == 0


def expand(src: str, dst: str) -> list[tuple[str, str]]:
    if not src.endswith("/"):
        return [(src, dst)]
    base = ROOT / src
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            rel = p.relative_to(base).as_posix()
            out.append(((Path(src) / rel).as_posix(), (Path(dst) / rel).as_posix()))
    return out


def move_one(src: str, dst: str, apply: bool, git: bool) -> str:
    s, d = ROOT / src, ROOT / dst
    if not s.exists():
        return "ya está" if d.exists() else "no existe"
    if d.exists():
        return "CONFLICTO (destino existe)"
    if not apply:
        return "mover"
    d.parent.mkdir(parents=True, exist_ok=True)
    if git and tracked(src):
        r = sh("git", "mv", "--", src, dst)
        if r.returncode != 0:
            return "ERROR git mv: " + r.stderr.strip()
        return "movido (git)"
    shutil.move(str(s), str(d))
    return "movido"


def prune_empty(dirs: set[Path]) -> None:
    for d in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        if not d.is_dir():
            continue
        for sub in sorted([x for x in d.rglob("*") if x.is_dir()], key=lambda p: len(p.parts), reverse=True):
            if "__pycache__" in sub.parts:
                shutil.rmtree(sub, ignore_errors=True)
            elif not any(sub.iterdir()):
                sub.rmdir()
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


def rewrite_docs(apply: bool) -> int:
    changed = 0
    seen: set[Path] = set()
    for pattern in DOC_GLOBS:
        for p in ROOT.glob(pattern):
            if p in seen or not p.is_file() or "historico" in p.parts:
                continue
            seen.add(p)
            if p.relative_to(ROOT).as_posix() in SKIP_REWRITE:
                continue
            text = p.read_bytes().decode("utf-8")
            new = text
            for old, rep in LINK_REWRITES:
                new = new.replace(old, rep)
            new = CAMBIOS_RE.sub("docs/historico/cambios/", new)
            if new != text:
                changed += 1
                print(f"  enlaces actualizados: {p.relative_to(ROOT).as_posix()}")
                if apply:
                    p.write_bytes(new.encode("utf-8"))
    return changed


def add_changelog(apply: bool) -> None:
    p = ROOT / "CHANGELOG.md"
    if not p.is_file():
        return
    text = p.read_bytes().decode("utf-8")
    if CHANGELOG_MARK in text:
        print("  CHANGELOG: entrada ya presente")
        return
    crlf = "\r\n" in text
    work = text.replace("\r\n", "\n")
    head, sep, rest = work.partition("\n## ")
    if not sep:
        return
    print("  CHANGELOG: se agrega entrada de reorganización")
    if apply:
        new = head + "\n" + CHANGELOG_ENTRY + "## " + rest
        p.write_bytes((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))


def add_gitignore(apply: bool) -> None:
    p = ROOT / ".gitignore"
    if not p.is_file():
        return
    text = p.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    present = set(text.replace("\r\n", "\n").split("\n"))
    missing = [line for line in GITIGNORE_LINES if line not in present]
    if not missing:
        print("  .gitignore: sin cambios")
        return
    print(f"  .gitignore: se agregan {len(missing)} líneas")
    if apply:
        p.write_bytes((text.rstrip("\r\n") + nl + nl + nl.join(missing) + nl).encode("utf-8"))


def add_readme_link(apply: bool) -> None:
    p = ROOT / "README.md"
    if not p.is_file():
        return
    text = p.read_bytes().decode("utf-8")
    if "MAPA_DE_ARCHIVOS.md" in text:
        print("  README: enlace al mapa ya presente")
        return
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    for i, line in enumerate(lines):
        if "docs/ACEPTACION_WINDOWS.md" in line and line.lstrip().startswith("- "):
            lines.insert(i + 1, "- [Mapa de archivos y carpeta validacion/](docs/MAPA_DE_ARCHIVOS.md).")
            print("  README: se agrega enlace al mapa de archivos")
            if apply:
                p.write_bytes(nl.join(lines).encode("utf-8"))
            return
    print("  README: no se encontró dónde agregar el enlace al mapa (agréguelo a mano)")


LINK_MD = re.compile(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)")


def check_links() -> int:
    bad = 0
    seen: set[Path] = set()
    for pattern in DOC_GLOBS + ["CHANGELOG.md"]:
        for p in ROOT.glob(pattern):
            if p in seen or "historico" in p.parts or not p.is_file():
                continue
            seen.add(p)
            for m in LINK_MD.finditer(p.read_text(encoding="utf-8")):
                target = m.group(1).split("#")[0]
                if target and not (p.parent / target).exists():
                    print(f"  ENLACE ROTO en {p.relative_to(ROOT).as_posix()}: {target}")
                    bad += 1
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aplicar", action="store_true", help="ejecutar los cambios (por defecto solo simula)")
    ap.add_argument("--mantener-cambios", action="store_true", help="no mover la carpeta cambios/")
    ap.add_argument("--sin-git", action="store_true", help="no usar git mv aunque haya repositorio")
    args = ap.parse_args()

    git = in_git() and not args.sin_git
    print(f"Raíz: {ROOT}\nModo: {'APLICAR' if args.aplicar else 'SIMULACIÓN'} | git mv: {'sí' if git else 'no'}\n")
    counts: dict[str, int] = {}
    srcdirs: set[Path] = set()
    parents: set[Path] = set()
    for src, dst in MOVES:
        if args.mantener_cambios and src == "cambios/":
            continue
        if src.endswith("/"):
            srcdirs.add(ROOT / src)
        for s, d in expand(src, dst):
            res = move_one(s, d, args.aplicar, git)
            if (ROOT / s).parent != ROOT:
                parents.add((ROOT / s).parent)
            key = res.split(" (")[0].split(":")[0]
            counts[key] = counts.get(key, 0) + 1
            if not src.endswith("/") or res.startswith(("CONFLICTO", "ERROR")):
                print(f"  [{res:<13}] {s} -> {d}")
    if args.aplicar:
        prune_empty(srcdirs | parents)
    resumen = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "sin movimientos"
    print(f"\nResumen de archivos: {resumen}")
    print("\nDocumentación:")
    rewrite_docs(args.aplicar)
    add_changelog(args.aplicar)
    add_gitignore(args.aplicar)
    add_readme_link(args.aplicar)
    if args.aplicar:
        print("\nComprobación de enlaces en documentación vigente:")
        bad = check_links()
        print("  sin enlaces rotos" if not bad else f"  {bad} enlace(s) roto(s): revisar")
        print("\nListo. Revise con `git status`, ejecute la regresión y recién entonces haga el commit.")
        problems = bad or counts.get("CONFLICTO", 0) or any(k.startswith("ERROR") for k in counts)
        return 1 if problems else 0
    print("\nSimulación terminada: no se cambió nada. Agregue --aplicar para ejecutar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
