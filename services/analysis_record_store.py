"""Persistencia SQLite de los análisis asociados al carrusel del Panel 2.

Cada miniatura del carrusel representa UN registro de análisis estable.  El
JSON del proyecto conserva una copia compatible de ``snapshots``, pero esta
base es la fuente primaria para recuperar foto, artefactos, máscaras y
métricas sin recalcular el análisis al seleccionar una miniatura.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
import sqlite3
import uuid
import re
from typing import Iterable


SCHEMA_VERSION = 1


class AnalysisRecordStore:
    """Base SQLite local, portable junto con la carpeta del proyecto."""

    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)
        data_dir = os.path.join(self.project_root, "datos")
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "analisis.sqlite3")
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = DELETE")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS analysis_records (
                    analysis_id TEXT PRIMARY KEY,
                    n INTEGER NOT NULL,
                    label TEXT,
                    timestamp TEXT,
                    updated_at TEXT NOT NULL,
                    complete INTEGER NOT NULL DEFAULT 1,
                    image TEXT,
                    curve TEXT,
                    matrix TEXT,
                    reference TEXT,
                    calc_data TEXT,
                    reference_data TEXT,
                    tmrt_data TEXT,
                    photo_analysis_data TEXT,
                    histogram TEXT,
                    shadow_classification TEXT,
                    area_calculo_text TEXT,
                    area_referencia_text TEXT,
                    area_calculo_px INTEGER,
                    area_referencia_px INTEGER,
                    promedio_gris REAL,
                    cobertura_sombra REAL,
                    atenuacion_sombra REAL,
                    transmitancia_efectiva REAL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_analysis_records_n
                    ON analysis_records(n);
                CREATE INDEX IF NOT EXISTS idx_analysis_records_complete
                    ON analysis_records(complete);
                CREATE INDEX IF NOT EXISTS idx_analysis_records_image
                    ON analysis_records(image);
                """
            )
            conn.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    @staticmethod
    def new_analysis_id() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _legacy_id(entry: dict) -> str:
        """ID determinista para snapshots anteriores a v17.

        No usa la ruta absoluta del proyecto, de modo que el ID no cambia al
        mover/exportar la carpeta.
        """
        seed = "|".join(
            str(entry.get(k) or "")
            for k in ("n", "timestamp", "label", "image", "curve")
        )
        return uuid.uuid5(uuid.NAMESPACE_URL, "sombra-analysis:" + seed).hex

    @staticmethod
    def _json_safe(value):
        try:
            import numpy as np
            if isinstance(value, np.generic):
                return value.item()
            if isinstance(value, np.ndarray):
                return value.tolist()
        except Exception:
            pass
        if isinstance(value, dict):
            return {str(k): AnalysisRecordStore._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [AnalysisRecordStore._json_safe(v) for v in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def upsert(self, entry: dict, *, complete: bool | None = None) -> dict:
        entry = dict(entry or {})
        analysis_id = entry.get("analysis_id") or self.new_analysis_id()
        entry["analysis_id"] = analysis_id
        if complete is None:
            complete = bool(entry.get("complete", not entry.get("provisional", False)))
        entry["complete"] = bool(complete)
        entry.pop("provisional", None)
        now = datetime.now().isoformat(timespec="seconds")
        entry.setdefault("timestamp", now)
        if not isinstance(entry.get("n"), int):
            entry["n"] = self.next_n()

        payload = json.dumps(self._json_safe(entry), ensure_ascii=False, separators=(",", ":"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO analysis_records(
                    analysis_id, n, label, timestamp, updated_at, complete,
                    image, curve, matrix, reference, calc_data, reference_data,
                    tmrt_data, photo_analysis_data, histogram,
                    shadow_classification, area_calculo_text,
                    area_referencia_text, area_calculo_px, area_referencia_px,
                    promedio_gris, cobertura_sombra, atenuacion_sombra,
                    transmitancia_efectiva, payload_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(analysis_id) DO UPDATE SET
                    n=excluded.n,
                    label=excluded.label,
                    timestamp=excluded.timestamp,
                    updated_at=excluded.updated_at,
                    complete=excluded.complete,
                    image=excluded.image,
                    curve=excluded.curve,
                    matrix=excluded.matrix,
                    reference=excluded.reference,
                    calc_data=excluded.calc_data,
                    reference_data=excluded.reference_data,
                    tmrt_data=excluded.tmrt_data,
                    photo_analysis_data=excluded.photo_analysis_data,
                    histogram=excluded.histogram,
                    shadow_classification=excluded.shadow_classification,
                    area_calculo_text=excluded.area_calculo_text,
                    area_referencia_text=excluded.area_referencia_text,
                    area_calculo_px=excluded.area_calculo_px,
                    area_referencia_px=excluded.area_referencia_px,
                    promedio_gris=excluded.promedio_gris,
                    cobertura_sombra=excluded.cobertura_sombra,
                    atenuacion_sombra=excluded.atenuacion_sombra,
                    transmitancia_efectiva=excluded.transmitancia_efectiva,
                    payload_json=excluded.payload_json
                """,
                (
                    analysis_id, int(entry["n"]), entry.get("label"),
                    entry.get("timestamp"), now, 1 if complete else 0,
                    entry.get("image"), entry.get("curve"), entry.get("matrix"),
                    entry.get("reference"), entry.get("calc_data"),
                    entry.get("reference_data"), entry.get("tmrt_data"),
                    entry.get("photo_analysis_data"), entry.get("histogram"),
                    entry.get("shadow_classification"), entry.get("area_calculo_text"),
                    entry.get("area_referencia_text"), entry.get("area_calculo_px"),
                    entry.get("area_referencia_px"), entry.get("promedio_gris"),
                    entry.get("cobertura_sombra"), entry.get("atenuacion_sombra"),
                    entry.get("transmitancia_efectiva"), payload,
                ),
            )
        return entry

    def next_n(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(n), 0) AS max_n FROM analysis_records").fetchone()
        return int(row["max_n"] or 0) + 1

    def get(self, analysis_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM analysis_records WHERE analysis_id=?",
                (analysis_id,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])

    def list_entries(self, *, complete_only: bool = True) -> list[dict]:
        sql = "SELECT payload_json FROM analysis_records"
        args = ()
        if complete_only:
            sql += " WHERE complete=1"
        sql += " ORDER BY n ASC, timestamp ASC, analysis_id ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def migrate_legacy_snapshots(self, snapshots: Iterable[dict] | None) -> int:
        """Importa el historial JSON viejo una sola vez de forma idempotente.

        Las entradas ``provisional`` se conservan fuera del carrusel nuevo,
        porque por definición no contienen todos los artefactos exigidos para
        una restauración completa.  Los snapshots formales sí se migran.
        """
        migrated = 0
        seen_fingerprints = set()
        for raw in list(snapshots or []):
            if not isinstance(raw, dict) or raw.get("provisional"):
                continue
            entry = dict(raw)

            # Limpieza muy conservadora del bug v16: al seleccionar un
            # registro se recalculaba y, si luego se guardaba, podía aparecer
            # otro snapshot con nombre sintético "elementoN" pero exactamente
            # las mismas ROIs y métricas. Solo se colapsa ese patrón inequívoco.
            fingerprint = json.dumps(self._json_safe({
                "poly_calculo": entry.get("poly_calculo"),
                "poly_referencia": entry.get("poly_referencia"),
                "cobertura": entry.get("cobertura_sombra", entry.get("porcentaje_sombra")),
                "atenuacion": entry.get("atenuacion_sombra"),
                "tau": entry.get("transmitancia_efectiva"),
                "tmrt_sombra": entry.get("tmrt_sombra"),
                "delta_tmrt": entry.get("delta_tmrt"),
            }), sort_keys=True, ensure_ascii=False)
            synthetic = bool(re.fullmatch(r"elemento\d+", str(entry.get("label") or ""), re.IGNORECASE))
            if synthetic and fingerprint in seen_fingerprints:
                continue
            seen_fingerprints.add(fingerprint)

            entry.setdefault("analysis_id", self._legacy_id(entry))
            entry["complete"] = True
            self.upsert(entry, complete=True)
            migrated += 1
        return migrated

    def count(self, *, complete_only: bool = True) -> int:
        sql = "SELECT COUNT(*) AS n FROM analysis_records"
        if complete_only:
            sql += " WHERE complete=1"
        with self._connect() as conn:
            row = conn.execute(sql).fetchone()
        return int(row["n"])
