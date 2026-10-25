"""Resuelve entradas efectivas de Edición/Modelo sin escribir controles de Tk."""
from datetime import timedelta
import math
from core.effective_scenario import scenario_date, effective_model, value, SCENARIO_SCHEMA
from core.local_time import local_instant, instant_metadata
from core.climate_profile import (temperatura_diurna_ciclo, viento_categoria_a_ms,
                                  velocidad_viento, factor_ghi_nubosidad, descomponer_radiacion)
from services.solar_engine import SolarEngine


def prepare_surface_scenario(variables):
    app = variables.get('_app_instance')
    model_panel = app is not None and variables is getattr(app, 'vars_modelo', None)
    mode_var = getattr(app, 'modo_modelo' if model_panel else 'modo_edicion', None)
    mode = value(mode_var) if mode_var is not None else value(variables.get('_modo_modelo', 'advanced'))
    selected = value(getattr(app, 'surface_model_mode', variables.get('_surface_model_mode', 'standard')))
    model = effective_model(mode, selected, surface=True)
    fecha = scenario_date(variables)
    hour = float(value(variables['hora']))
    lat, lon = float(value(variables['lat'])), float(value(variables['lon']))
    if not all(math.isfinite(x) for x in (hour, lat, lon)) or not 0 <= hour <= 24 or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('Hora o coordenadas del escenario inválidas')
    if hour == 24:
        fecha += timedelta(days=1)
        hour = 0.0
    timezone = value(variables.get('timezone', 'America/Argentina/Buenos_Aires'))
    engine = SolarEngine(tz=str(timezone))
    instant = local_instant(fecha, hour, str(timezone))
    solar = engine.get_solar_data(lat, lon, instant)
    rh = float(value(variables.get('humedad', 50)))
    wind = viento_categoria_a_ms(value(variables.get('viento', 'moderado')))
    if mode == 'simple':
        ta = float(value(variables['T_amb_base']))
    else:
        ta = temperatura_diurna_ciclo(hour, value(variables['T_min']), value(variables['T_max']))
    variables['_radiation_override_ghi'] = None
    variables['_radiation_override_dni'] = None
    variables['_radiation_override_dhi'] = None
    variables['_cloud_fraction_override'] = None
    source_mode = 'legacy_configured'
    label, quality, detail = 'Radiación simplificada del escenario', 'legacy_configured', 'legacy'
    weather_sources = {key: 'user_input' for key in ('ta_c', 'rh_pct', 'wind_m_s')}
    if mode == 'advanced' and app is not None and hasattr(app, '_obtener_datos_solares'):
        source_mode = value(app.radiation_source_mode)
        ghi_manual = float(value(variables['I_sol_base'])) if source_mode.startswith('manual_') else None
        solar = app._obtener_datos_solares(lat, lon, fecha, hour, manual_ghi=ghi_manual)
        if source_mode == 'clear_sky':
            cloud = value(variables.get('nubosidad', 'Despejado'))
            factor = factor_ghi_nubosidad(cloud)
            if factor != 1:
                solar = dict(solar)
                rad = descomponer_radiacion(solar['ghi'] * factor, solar['elevation'], cloud)
                solar.update(ghi=rad['ghi'], dni=rad['dni_normal'], dhi=rad['dhi'])
                solar['source_label'] += f' · {cloud}'
                solar['quality'] += ' + escenario_nubosidad'
        if source_mode == 'observed_series':
            for key in weather_sources:
                if solar.get(key) is not None:
                    weather_sources[key] = 'observed_series'
            ta = float(solar['ta_c']) + 273.15 if solar.get('ta_c') is not None else ta
            rh = float(solar['rh_pct']) if solar.get('rh_pct') is not None else rh
            wind = viento_categoria_a_ms(solar['wind_m_s']) if solar.get('wind_m_s') is not None else wind
            variables['_cloud_fraction_override'] = solar.get('cloud_fraction')
        for component in ('ghi', 'dni', 'dhi'):
            variables[f'_radiation_override_{component}'] = float(solar[component])
        label, quality, detail = solar['source_label'], solar['quality'], solar.get('source_detail', '')
        ghi = float(solar['ghi'])
    else:
        # Preserve the fast model and standalone scene API.
        ghi = float(value(variables['I_sol_base'])) * max(0, math.sin(math.radians(solar['elevation'])))
    if not math.isfinite(ta) or ta <= 0 or not math.isfinite(rh) or not 0 <= rh <= 100:
        raise ValueError('Temperatura Kelvin o humedad del escenario inválida')
    variables['_effective_wind_ref_10m'] = wind
    variables['_effective_rh_pct'] = rh
    variables['_air_temp_override_k'] = ta
    variables['_radiation_source_label'] = label
    variables['_radiation_quality'] = quality
    config = dict(schema_version=SCENARIO_SCHEMA, context='surface', input_mode=mode, surface_model=model,
                  date_iso=fecha.isoformat(), hour_local=hour, latitude=lat, longitude=lon,
                  timezone=timezone, air_temp_k=ta, rh_pct=rh, wind_ref_10m_m_s=wind,
                  wind_2m_m_s=velocidad_viento(2, wind), wind_profile='neutral_log_z0_0.03m',
                  convection_wind='reference_10m_legacy_approximation', ghi=ghi,
                  dni=variables['_radiation_override_dni'], dhi=variables['_radiation_override_dhi'],
                  solar_elevation=solar['elevation'], solar_azimuth=solar['azimuth'],
                  source_mode=source_mode, source_label=label, quality=quality, source_detail=detail,
                  weather_sources=weather_sources, derived_components=solar.get('derived_components', []),
                  warnings=solar.get('warnings', []), **instant_metadata(instant))
    variables['_effective_scenario'] = config
    return config
