"""Migración compatible, transaccional y sin respaldos en texto plano."""
from database_manager import DatabaseManager
import argparse


def migrar(db_name=None, *, legacy_path=None):
    db = DatabaseManager(db_name, legacy_path=legacy_path)
    db.close()
    print("Migración completada. Usuarios e historial preservados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-db", help="Base antigua fuera de la carpeta de instalación.")
    args = parser.parse_args()
    migrar(legacy_path=args.legacy_db)
