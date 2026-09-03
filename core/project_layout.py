"""Esquema único de carpetas de un proyecto (v19).

La aplicación deja de dispersar artefactos entre ``imagenes/``, ``mascaras/``,
``curvas/``, ``Planos/``, ``modelos/`` y varias ramas de ``resultados``.
Todo recurso persistente tiene un destino predecible y portable relativo a la
raíz del proyecto.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
import shutil
import filecmp


LAYOUT_VERSION = 2


@dataclass(frozen=True)
class ProjectLayout:
    root: str

    def __post_init__(self):
        object.__setattr__(self, "root", os.path.abspath(self.root))

    # ------------------------------ directorios principales
    @property
    def config_dir(self): return os.path.join(self.root, "config")
    @property
    def inputs_dir(self): return os.path.join(self.root, "entradas")
    @property
    def images_dir(self): return os.path.join(self.inputs_dir, "imagenes")
    @property
    def meteorology_dir(self): return os.path.join(self.inputs_dir, "meteorologia")
    @property
    def validation_inputs_dir(self): return os.path.join(self.inputs_dir, "validacion")
    @property
    def scene_dir(self): return os.path.join(self.root, "escena")
    @property
    def analysis_dir(self): return os.path.join(self.root, "analisis")
    @property
    def analysis_elements_dir(self): return os.path.join(self.analysis_dir, "elementos")
    @property
    def dataset_dir(self): return os.path.join(self.analysis_dir, "dataset")
    @property
    def results_dir(self): return os.path.join(self.root, "resultados")
    @property
    def project_results_dir(self): return os.path.join(self.results_dir, "proyecto")
    @property
    def validation_results_dir(self): return os.path.join(self.results_dir, "validacion")
    @property
    def reports_dir(self): return os.path.join(self.results_dir, "informes")
    @property
    def backups_dir(self): return os.path.join(self.root, "respaldos")
    @property
    def legacy_dir(self): return os.path.join(self.root, "_legacy_v18")

    # ------------------------------ archivos estables
    @property
    def analysis_db(self): return os.path.join(self.analysis_dir, "analisis.sqlite3")
    @property
    def edit_excel(self): return os.path.join(self.scene_dir, "edicion.xlsx")
    @property
    def model_excel(self): return os.path.join(self.scene_dir, "modelo.xlsx")
    @property
    def via_annotations(self): return os.path.join(self.dataset_dir, "mascaras_via.json")
    @property
    def structure_manifest(self): return os.path.join(self.config_dir, "estructura.json")
    @property
    def inventory_manifest(self): return os.path.join(self.config_dir, "inventario.json")
    @property
    def validation_report(self): return os.path.join(self.validation_results_dir, "validacion_modelos_termicos.xlsx")
    @property
    def audit_json(self): return os.path.join(self.validation_results_dir, "auditoria_cientifica.json")
    @property
    def audit_txt(self): return os.path.join(self.validation_results_dir, "auditoria_cientifica.txt")
    @property
    def full_report(self): return os.path.join(self.reports_dir, "informe_proyecto.pdf")
    @property
    def last_element_report(self): return os.path.join(self.reports_dir, "ultimo_elemento.pdf")
    @property
    def comparison_chart(self): return os.path.join(self.project_results_dir, "comparativo_elementos.png")
    @property
    def scatter_chart(self): return os.path.join(self.project_results_dir, "dispersion_sombra_tmrt.png")
    @property
    def sensitivity_chart(self): return os.path.join(self.project_results_dir, "sensibilidad_sombra.png")
    @property
    def elements_excel(self): return os.path.join(self.project_results_dir, "elementos_proyecto.xlsx")

    def ensure(self) -> None:
        for path in (
            self.config_dir, self.images_dir, self.meteorology_dir,
            self.validation_inputs_dir, self.scene_dir, self.analysis_dir,
            self.analysis_elements_dir, self.dataset_dir, self.project_results_dir,
            self.validation_results_dir, self.reports_dir, self.backups_dir,
        ):
            os.makedirs(path, exist_ok=True)
        self.write_structure_manifest()

    def write_structure_manifest(self) -> None:
        payload = {
            "layout_version": LAYOUT_VERSION,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "folders": {
                "entradas_imagenes": "entradas/imagenes",
                "entradas_meteorologia": "entradas/meteorologia",
                "entradas_validacion": "entradas/validacion",
                "escena": "escena",
                "analisis_db": "analisis/analisis.sqlite3",
                "analisis_elementos": "analisis/elementos/<analysis_id>",
                "dataset": "analisis/dataset",
                "resultados_proyecto": "resultados/proyecto",
                "resultados_validacion": "resultados/validacion",
                "informes": "resultados/informes",
                "respaldos": "respaldos",
            },
            "stable_files": {
                "edicion": "escena/edicion.xlsx",
                "modelo": "escena/modelo.xlsx",
                "informe": "resultados/informes/informe_proyecto.pdf",
                "validacion": "resultados/validacion/validacion_modelos_termicos.xlsx",
                "auditoria_json": "resultados/validacion/auditoria_cientifica.json",
                "inventario": "config/inventario.json",
            },
        }
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.structure_manifest, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

    def write_inventory(self) -> None:
        """Escribe un índice liviano de los archivos vivos del proyecto.

        No es la fuente primaria de datos (esa función la cumplen .sombra y
        SQLite); sirve para auditoría, diagnóstico y para verificar rápidamente
        qué artefactos persistentes existen. Se excluyen respaldos y legacy.
        """
        files = []
        excluded = {os.path.abspath(self.backups_dir), os.path.abspath(self.legacy_dir)}
        for folder, dirs, names in os.walk(self.root):
            dirs[:] = [
                d for d in dirs
                if os.path.abspath(os.path.join(folder, d)) not in excluded
            ]
            for name in names:
                full = os.path.join(folder, name)
                if os.path.abspath(full) == os.path.abspath(self.inventory_manifest):
                    continue
                try:
                    stat = os.stat(full)
                except OSError:
                    continue
                files.append({
                    "path": os.path.relpath(full, self.root).replace("\\", "/"),
                    "size_bytes": int(stat.st_size),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                })
        payload = {
            "layout_version": LAYOUT_VERSION,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "file_count": len(files),
            "files": sorted(files, key=lambda item: item["path"]),
        }
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.inventory_manifest, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

    def element_dir(self, analysis_id: str) -> str:
        path = os.path.join(self.analysis_elements_dir, str(analysis_id))
        for child in ("areas", "sombra", "termico"):
            os.makedirs(os.path.join(path, child), exist_ok=True)
        return path

    def element_paths(self, analysis_id: str) -> dict[str, str]:
        base = self.element_dir(analysis_id)
        return {
            "matrix": os.path.join(base, "areas", "matriz_calculo.xlsx"),
            "reference": os.path.join(base, "areas", "matriz_referencia.xlsx"),
            "calc_data": os.path.join(base, "areas", "calculo.npz"),
            "reference_data": os.path.join(base, "areas", "referencia.npz"),
            "dataset_mask": os.path.join(base, "areas", "mascara_seleccion.png"),
            "photo_analysis_data": os.path.join(base, "sombra", "analisis_fotografico.npz"),
            "histogram": os.path.join(base, "sombra", "histograma.png"),
            "shadow_classification": os.path.join(base, "sombra", "clasificacion_sombra.png"),
            "tmrt_data": os.path.join(base, "termico", "datos_tmrt.npz"),
            "curve": os.path.join(base, "termico", "curva_tmrt.png"),
            "temperature_summary": os.path.join(base, "termico", "resumen_tmrt.png"),
        }

    def rel(self, path: str | None) -> str | None:
        if not path:
            return None
        try:
            return os.path.relpath(os.path.abspath(path), self.root)
        except Exception:
            return path

    def import_input_file(self, source_path: str, destination_dir: str) -> str:
        """Importa un archivo de entrada sin sobrescribir ni duplicar idénticos.

        - Si ``source_path`` ya está dentro del destino, se reutiliza.
        - Si existe un archivo homónimo con exactamente el mismo contenido,
          se reutiliza ese archivo.
        - Si el homónimo es distinto, se crea ``_v2``, ``_v3``... únicamente
          para preservar dos *entradas* realmente diferentes.

        El versionado queda limitado a fuentes importadas; los resultados del
        proyecto tienen nombres estables y se actualizan en el mismo archivo.
        """
        source = os.path.abspath(source_path)
        destination_dir = os.path.abspath(destination_dir)
        if not os.path.isfile(source):
            raise FileNotFoundError(source)
        os.makedirs(destination_dir, exist_ok=True)
        try:
            if os.path.commonpath([source, destination_dir]) == destination_dir:
                return source
        except ValueError:
            pass

        basename = os.path.basename(source)
        candidate = os.path.join(destination_dir, basename)
        if os.path.exists(candidate):
            try:
                if filecmp.cmp(source, candidate, shallow=False):
                    return candidate
            except OSError:
                pass
            stem, ext = os.path.splitext(basename)
            version = 2
            while True:
                candidate = os.path.join(destination_dir, f"{stem}_v{version}{ext}")
                if not os.path.exists(candidate):
                    break
                try:
                    if filecmp.cmp(source, candidate, shallow=False):
                        return candidate
                except OSError:
                    pass
                version += 1
        shutil.copy2(source, candidate)
        return candidate

    # ------------------------------ migración de carpetas previas
    def _move_tree_contents(self, old_rel: str, new_dir: str) -> None:
        old = os.path.join(self.root, old_rel)
        if not os.path.isdir(old) or os.path.abspath(old) == os.path.abspath(new_dir):
            return
        os.makedirs(new_dir, exist_ok=True)
        for name in os.listdir(old):
            src = os.path.join(old, name)
            dst = os.path.join(new_dir, name)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    self._merge_dirs(src, dst)
                else:
                    shutil.move(src, dst)
            else:
                if not os.path.exists(dst):
                    shutil.move(src, dst)
                else:
                    # No se pisa información: el duplicado viejo queda para
                    # revisión en _legacy_v18.
                    self._stash_legacy(src, old_rel)
        try:
            if not os.listdir(old):
                os.rmdir(old)
        except OSError:
            pass

    def _merge_dirs(self, src: str, dst: str) -> None:
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            s = os.path.join(src, name); d = os.path.join(dst, name)
            if os.path.isdir(s):
                self._merge_dirs(s, d)
            elif not os.path.exists(d):
                shutil.move(s, d)
            else:
                self._stash_legacy(s, os.path.relpath(src, self.root))
        try:
            if not os.listdir(src): os.rmdir(src)
        except OSError:
            pass

    def _stash_legacy(self, src: str, rel_parent: str) -> None:
        target_dir = os.path.join(self.legacy_dir, rel_parent)
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, os.path.basename(src))
        if not os.path.exists(target):
            shutil.move(src, target)

    def archive_legacy_folder(self, rel: str) -> None:
        """Mueve una carpeta antigua restante bajo _legacy_v18/."""
        src = os.path.join(self.root, rel)
        if not os.path.exists(src):
            return
        dst = os.path.join(self.legacy_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            self._merge_dirs(src, dst)
        else:
            shutil.move(src, dst)

    def migrate_basic_legacy(self) -> dict[str, str]:
        """Mueve entradas/base y devuelve equivalencias de prefijos.

        Los artefactos por análisis se migran desde AnalysisRecordStore, que
        conoce el ``analysis_id`` de cada registro.
        """
        self.ensure()
        old_db = os.path.join(self.root, "datos", "analisis.sqlite3")
        if os.path.exists(old_db) and not os.path.exists(self.analysis_db):
            os.makedirs(self.analysis_dir, exist_ok=True)
            shutil.move(old_db, self.analysis_db)
        self._move_tree_contents("imagenes", self.images_dir)
        self._move_tree_contents("meteorologia", self.meteorology_dir)
        old_via = os.path.join(self.root, "mascaras.json")
        if os.path.exists(old_via) and not os.path.exists(self.via_annotations):
            os.makedirs(self.dataset_dir, exist_ok=True)
            shutil.move(old_via, self.via_annotations)
        old_dataset = os.path.join(self.root, "DataSetSombra")
        if os.path.isdir(old_dataset):
            self._move_tree_contents("DataSetSombra", self.dataset_dir)

        # Resultados globales conocidos.
        old_analysis = os.path.join(self.root, "resultados", "analisis")
        if os.path.isdir(old_analysis):
            for name in list(os.listdir(old_analysis)):
                src = os.path.join(old_analysis, name)
                if not os.path.isfile(src):
                    continue
                low = name.lower()
                if low.startswith("informe_") and low.endswith(".pdf"):
                    dst = os.path.join(self.reports_dir, name)
                elif "validacion" in low or "auditoria" in low:
                    dst = os.path.join(self.validation_results_dir, name)
                else:
                    dst = os.path.join(self.project_results_dir, name)
                if not os.path.exists(dst):
                    shutil.move(src, dst)
            try:
                if not os.listdir(old_analysis): os.rmdir(old_analysis)
            except OSError:
                pass

        return {
            "imagenes/": "entradas/imagenes/",
            "meteorologia/": "entradas/meteorologia/",
            "datos/analisis.sqlite3": "analisis/analisis.sqlite3",
        }
