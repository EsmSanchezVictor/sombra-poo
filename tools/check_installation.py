"""Autocomprobación sin GUI ni cambios en cuentas o proyectos reales."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.installation_check import run_installation_check
from core.safe_io import atomic_write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',required=True)
    parser.add_argument('--require-full',action='store_true')
    args=parser.parse_args()
    result=run_installation_check(require_full=args.require_full)
    atomic_write_json(args.report,result)
    print(f'{result["status"]}: {args.report}')
    return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
