"""Ranking de una sola escena bajo el contexto efectivo de Temperatura."""
from services.meteorology_controller import resolve_temperature_context
from core.scenario import ranking_arboles


def rank_app_trees(app, scene_name, *, extent=60.0, resolution=240):
    if scene_name not in ("Edición", "Modelo"):
        raise ValueError("Seleccione la escena Edición o Modelo.")
    variables = app.vars if scene_name == "Edición" else app.vars_modelo
    trees = list(variables.get("arboles") or [])
    if not trees:
        raise ValueError(f"No hay árboles en la escena {scene_name}.")
    ta, hour, fecha, lat, lon = app._leer_parametros_tmrt()
    config, _ = resolve_temperature_context(app, ta, hour, fecha, lat, lon)
    results = ranking_arboles(trees, config.calculator(), fecha, hour,
                             extent=extent, resolucion=resolution, scenario=config)
    return config, results
