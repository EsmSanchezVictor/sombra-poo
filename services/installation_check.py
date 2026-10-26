"""Autocomprobación aislada del núcleo instalado; no abre Tk ni proyectos reales."""
from datetime import datetime
from importlib import import_module, metadata
from pathlib import Path
import math
import platform
import tempfile
import time


def run_installation_check(*, require_full=False):
    from core.app_version import APP_RELEASE
    from core.model_registry import methodology_manifest
    def resource_path(relative):
        return Path(__file__).resolve().parents[1] / relative
    checks = []

    def check(name, operation):
        start = time.perf_counter()
        try:
            detail = operation()
            checks.append(dict(name=name, status="passed", detail=detail,
                               seconds=round(time.perf_counter()-start, 3)))
        except Exception as exc:
            checks.append(dict(name=name, status="failed", error=f"{type(exc).__name__}: {exc}"))

    for module, distribution in (("numpy", "numpy"), ("pandas", "pandas"), ("cv2", "opencv-python"),
                                 ("openpyxl", "openpyxl"), ("matplotlib", "matplotlib"),
                                 ("PIL", "pillow"), ("fpdf", "fpdf2"), ("tzdata", "tzdata")):
        def dependency(module=module, distribution=distribution):
            loaded = import_module(module)
            if module == "cv2":
                return loaded.__version__  # Perfil QA headless también válido.
            return metadata.version(distribution)
        check(f"dependency:{module}", dependency)
    for module in ("pvlib", "pythermalcomfort", "vtkmodules.vtkCommonCore"):
        try:
            imported = import_module(module)
        except ImportError as exc:
            checks.append(dict(name=f"optional:{module}", status="failed" if require_full else "optional_absent",
                               error=str(exc)))
        else:
            checks.append(dict(name=f"optional:{module}", status="passed"))

    def resources():
        from PIL import Image
        for name in ("fiebre", "sombra", "config", "vista-3d"):
            with Image.open(resource_path(f"test/imagen/{name} (3).png")) as image:
                image.verify()
        if not resource_path("data/locations_latam.csv").is_file():
            raise ValueError("Falta el catálogo de ubicaciones.")
        return "Cuatro iconos y ubicaciones disponibles independientemente del directorio de inicio."
    check("resources", resources)

    def science():
        from services.solar_engine import SolarEngine
        from core.local_time import local_instant, LocalTimeError
        from shadow_temp import Temperatura
        from core.thermal_comfort import utci
        solar = SolarEngine().get_solar_data(-31.4, -64.2, datetime(2024, 1, 15, 13))
        closure = solar['dni']*max(0, math.sin(math.radians(solar['elevation']))) + solar['dhi']
        if not math.isclose(closure, solar['ghi'], rel_tol=1e-9):
            raise ValueError("No cierra la radiación horizontal.")
        calc = Temperatura(-31.4, -64.2)
        result = calc.calculate_tmrt(30, 50, date_value=datetime(2024,1,15).date(), time_value=13,
                                     radiation_override=500, solar_altitude_override=45)
        if not result['Tmrt_sombra'] <= result['Tmrt_sol']:
            raise ValueError("Tmrt en sombra supera el valor al sol.")
        for fecha, hour in ((datetime(2024,3,10).date(),2.5),(datetime(2024,11,3).date(),1.5)):
            try:
                local_instant(fecha,hour,"America/New_York")
            except LocalTimeError:
                pass
            else:
                raise ValueError("No se rechazó un conflicto horario.")
        comfort = utci(30, 45, 4, 60)
        if require_full and (comfort is None or not math.isfinite(float(comfort))):
            raise ValueError("UTCI no produce un resultado finito dentro de dominio.")
        return dict(tmrt_sol=result['Tmrt_sol'], tmrt_shade=result['Tmrt_sombra'], utci=comfort)
    check("science", science)

    with tempfile.TemporaryDirectory(prefix="sombra-install-check-") as directory:
        def persistence():
            from core.project import Project
            from core.excel_scene import save_scene_excel, load_scene_excel
            from core.project_manager import ProjectManager
            from services.analysis_record_store import AnalysisRecordStore
            from services.project_copy import copy_project
            from types import SimpleNamespace
            root = Path(directory)
            project = Project(str(root / "Plaza de prueba")); project.ensure_structure()
            AnalysisRecordStore(project.root_path).upsert({'analysis_id':'check','n':1})
            scene = dict(hora=13,dia=15,_year=2024,lat=-31.4,lon=-64.2,T_amb_base=300.,T_min=290.,
                         T_max=308.,I_sol_base=700.,humedad=60.,viento='moderado',arboles=[],estructuras=[])
            save_scene_excel(project.layout.edit_excel,[],[],scene)
            load_scene_excel(project.layout.edit_excel)
            project.storage.commit(project.state_path,{'version':1,'next_n':2,'name':'Plaza de prueba'})
            saved,recovered,issues = project.storage.load(project.state_path)
            if saved['next_n'] != 2 or issues or recovered:
                raise ValueError("El estado guardado no se recupera íntegramente.")
            archive = root/'respaldo.3es';project.storage.export(archive)
            manager = ProjectManager(SimpleNamespace(settings={}),None)
            manager.projects_root = str(root/'importados')
            restored = manager.import_archive(str(archive))
            if not Path(restored).is_file():
                raise ValueError("El respaldo no puede importarse.")
            copied = copy_project(project, root/'Copia de prueba')
            if not Path(copied).is_file():
                raise ValueError("No se puede copiar el proyecto.")
            return "JSON/Excel/SQLite, reapertura, exportación/importación .3es y copia en carpetas temporales."
        check("persistence", persistence)
    return dict(schema_version=1, app_release=APP_RELEASE, methodology=methodology_manifest(),
                platform=platform.platform(), python=platform.python_version(), require_full=require_full,
                status="passed" if all(c['status'] != 'failed' for c in checks) else "failed",
                visual_tk_vtk_tested=False, field_validation=False, checks=checks)
