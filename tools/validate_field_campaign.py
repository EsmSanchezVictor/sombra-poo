"""Evaluar CSV de campaña sin abrir Tk ni aplicar ajustes a la aplicación."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.safe_io import atomic_write_json
from services.field_validation import evaluate_campaign,json_report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv');parser.add_argument('--report',required=True)
    parser.add_argument('--diagnostic',action='store_true',help='Permitir holdout interno; no es validación independiente')
    args=parser.parse_args()
    try:result=evaluate_campaign(args.csv,strict_campaigns=not args.diagnostic)
    except (ValueError,OSError,KeyError) as exc:parser.exit(1,f'Error: {exc}\n')
    atomic_write_json(args.report,json_report(result))
    print(f'Informe: {args.report}. No se aplicó ninguna calibración.')


if __name__=='__main__':main()
