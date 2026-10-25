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
from core.safe_io import atomic_write_json
import os
import shutil
import filecmp
from core.safe_paths import validate_analysis_id, contained_path, safe_component


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
        paths = (
            self.config_dir, self.images_dir, self.meteorology_dir,
            self.validation_inputs_dir, self.scene_dir, self.analysis_dir,
            self.analysis_elements_dir, self.dataset_dir, self.project_results_dir,
            self.validation_results_dir, self.reports_dir, self.backups_dir,
        )
        for path in paths:
            contained_path(self.root, path)
        for path in (self.analysis_db, self.edit_excel, self.model_excel, self.structure_manifest,
                     self.inventory_manifest, self.via_annotations, self.validation_report,
                     self.audit_json, self.audit_txt, self.full_report, self.last_element_report):
            contained_path(self.root, path)
        for path in paths:
            os.makedirs(path, exist_ok=True)
        if not os.path.isfile(self.structure_manifest):
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
        atomic_write_json(self.structure_manifest, payload, indent=2, ensure_ascii=False)

    def write_inventory(self) -> None:
        from core.project_integrity import IntegrityTracker
        atomic_write_json(self.inventory_manifest, IntegrityTracker().inventory(self.root))

    def element_dir(self, analysis_id: str) -> str:
        path = contained_path(self.analysis_elements_dir, validate_analysis_id(analysis_id), allow_absolute=False)
        children = [contained_path(self.root, os.path.join(path, child)) for child in ("areas", "sombra", "termico")]
        for child in children:
            os.makedirs(child, exist_ok=True)
        return path

    def element_paths(self, analysis_id: str) -> dict[str, str]:
        base = self.element_dir(analysis_id)
        paths = {
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
        return {key: contained_path(self.root, value) for key, value in paths.items()}

    def rel(self, path: str | None) -> str | None:
        if not path:
            return None
        try:
            return os.path.relpath(contained_path(self.root, os.path.abspath(path)), self.root)
        except (ValueError, OSError):
            return None

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
        destination_dir = contained_path(self.root, os.path.abspath(destination_dir))
        if not os.path.isfile(source):
            raise FileNotFoundError(source)
        os.makedirs(destination_dir, exist_ok=True)
        try:
            if os.path.commonpath([source, destination_dir]) == destination_dir:
                return contained_path(destination_dir, source)
        except ValueError:
            pass

        basename = safe_component(os.path.basename(source))
        candidate = contained_path(destination_dir, basename, allow_absolute=False)
        if os.path.exists(candidate):
            try:
                if filecmp.cmp(source, candidate, shallow=False):
                    return candidate
            except OSError:
                pass
            stem, ext = os.path.splitext(basename)
            version = 2
            while True:
                candidate = contained_path(destination_dir, safe_component(f"{stem}_v{version}{ext}"), allow_absolute=False)
                if not os.path.exists(candidate):
                    break
                try:
                    if filecmp.cmp(source, candidate, shallow=False):
                        return candidate
                except OSError:
                    pass
                version += 1
        from core.safe_io import atomic_output
        with atomic_output(candidate) as temporary:
            shutil.copy2(source, temporary)
        return candidate

    # ------------------------------ migración de carpetas previas
    def _move_tree_contents(self, old_rel: str, new_dir: str) -> None:
        old = contained_path(self.root, old_rel, allow_absolute=False)
        new_dir = contained_path(self.root, new_dir)
        if not os.path.isdir(old) or os.path.abspath(old) == os.path.abspath(new_dir):
            return
        os.makedirs(new_dir, exist_ok=True)
        for name in os.listdir(old):
            src = contained_path(self.root, os.path.join(old, name))
            dst = contained_path(self.root, os.path.join(new_dir, name))
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
        src = contained_path(self.root, src)
        dst = contained_path(self.root, dst)
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            s = contained_path(self.root, os.path.join(src, name))
            d = contained_path(self.root, os.path.join(dst, name))
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
        src = contained_path(self.root, src)
        target_dir = contained_path(self.legacy_dir, rel_parent, allow_absolute=False)
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, os.path.basename(src))
        if not os.path.exists(target):
            shutil.move(src, target)

    def archive_legacy_folder(self, rel: str) -> None:
        """Mueve una carpeta antigua restante bajo _legacy_v18/."""
        src = contained_path(self.root, rel, allow_absolute=False)
        if not os.path.exists(src):
            return
        dst = contained_path(self.legacy_dir, rel, allow_absolute=False)
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
        old_db = contained_path(self.root, "datos/analisis.sqlite3", allow_absolute=False)
        if os.path.exists(old_db) and not os.path.exists(self.analysis_db):
            os.makedirs(self.analysis_dir, exist_ok=True)
            shutil.move(old_db, self.analysis_db)
        self._move_tree_contents("imagenes", self.images_dir)
        self._move_tree_contents("meteorologia", self.meteorology_dir)
        old_via = contained_path(self.root, "mascaras.json", allow_absolute=False)
        if os.path.exists(old_via) and not os.path.exists(self.via_annotations):
            os.makedirs(self.dataset_dir, exist_ok=True)
            shutil.move(old_via, self.via_annotations)
        old_dataset = contained_path(self.root, "DataSetSombra", allow_absolute=False)
        if os.path.isdir(old_dataset):
            self._move_tree_contents("DataSetSombra", self.dataset_dir)

        # Resultados globales conocidos.
        old_analysis = contained_path(self.root, "resultados/analisis", allow_absolute=False)
        if os.path.isdir(old_analysis):
            for name in list(os.listdir(old_analysis)):
                src = contained_path(self.root, os.path.join(old_analysis, name))
                if not os.path.isfile(src):
                    continue
                low = name.lower()
                if low.startswith("informe_") and low.endswith(".pdf"):
                    dst = os.path.join(self.reports_dir, name)
                elif "validacion" in low or "auditoria" in low:
                    dst = os.path.join(self.validation_results_dir, name)
                else:
                    dst = os.path.join(self.project_results_dir, name)
                dst = contained_path(self.root, dst)
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
