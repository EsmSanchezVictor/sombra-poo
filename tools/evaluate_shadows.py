"""CLI de evaluación reproducible de máscaras con referencias anotadas."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.safe_io import atomic_write_json
from services.shadow_evaluation import evaluate_manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest');parser.add_argument('--report',required=True)
    parser.add_argument('--require-real',action='store_true',
                        help='Exigir fotos declaradas reales con autor y método de anotación; no certifica autenticidad')
    args=parser.parse_args()
    try:result=evaluate_manifest(args.manifest,require_real=args.require_real)
    except (ValueError,KeyError,OSError,TypeError) as exc:parser.exit(1,f'Error: {exc}\n')
    atomic_write_json(args.report,result)
    print(f'Evaluados {len(result["cases"])} casos. Fotos reales declaradas: {result["real_photo_cases"]}. Informe: {args.report}')


if __name__=='__main__':main()
