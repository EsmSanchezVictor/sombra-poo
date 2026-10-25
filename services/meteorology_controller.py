"""Resolución meteorológica y configuración efectiva separadas de los widgets."""
from core.effective_scenario import EffectiveScenarioConfig


def resolve_solar_data(
    app, latitude, longitude, fecha, hora, *, manual_ghi=None,
    mode_override=None, use_pvlib_override=None,
):
    """Resuelve posición solar + radiación con procedencia explícita.

    Fuentes disponibles (v14):
    - clear_sky: cielo despejado modelado (pvlib si se solicita/está disponible,
      fallback analítico en caso contrario);
    - manual_measured: medición puntual ingresada por el usuario;
    - manual_scenario: escenario hipotético ingresado manualmente;
    - observed_series: serie meteorológica CSV importada.

    Los componentes faltantes DNI/DHI pueden derivarse, pero esa derivación
    queda registrada en ``quality``/``derived_components``.
    """
    instante = app._construir_instante(fecha, hora)
    tz = app._timezone_actual()
    app.solar_engine.set_timezone(tz)
    use_pvlib = (
        bool(use_pvlib_override) if use_pvlib_override is not None
        else bool(app.use_pvlib_engine.get())
    )
    app.solar_engine.set_use_pvlib(use_pvlib)

    mode = (
        str(mode_override) if mode_override is not None
        else (app.radiation_source_mode.get() if hasattr(app, "radiation_source_mode") else "clear_sky")
    )
    if mode.startswith("manual_") and manual_ghi is None:
        manual_ghi = app._optional_float_text(getattr(app, "manual_ghi", ""))
    manual_dni = app._optional_float_text(getattr(app, "manual_dni", "")) if mode.startswith("manual_") else None
    manual_dhi = app._optional_float_text(getattr(app, "manual_dhi", "")) if mode.startswith("manual_") else None
    max_gap = float(app.settings.get("meteorology_max_gap_minutes", 90.0))
    data = app.meteorology_service.resolve(
        mode=mode,
        solar_engine=app.solar_engine,
        lat=float(latitude), lon=float(longitude), dt=instante,
        manual_ghi=manual_ghi,
        manual_dni=manual_dni,
        manual_dhi=manual_dhi,
        max_gap_minutes=max_gap,
    )
    app.last_meteorology_data = data
    return data

def resolve_temperature_context(app, temp_ambient, hora, fecha, lat, lon):
    """Una política efectiva para punto, mapa, confort, sensibilidad e informe."""
    mode = app.modo_temperatura.get()
    advanced = mode == "advanced"
    solar = app._obtener_datos_solares(
        lat, lon, fecha, hora,
        mode_override=None if advanced else "clear_sky",
        use_pvlib_override=None if advanced else False,
    )
    rh = app.vars_modelo["humedad"].get() if advanced else app.simple_rh.get()
    config = EffectiveScenarioConfig.from_resolved(
        input_mode=mode, selected_model=app.tmrt_model_mode.get(),
        fecha=fecha, hour=hora, lat=lat, lon=lon, timezone=app._timezone_actual(),
        ta=temp_ambient, rh=rh, wind=app.vars_modelo["viento"].get(),
        k_factor=app.k_factor, solar=solar,
    )
    return config, solar
