import os
import pandas as pd
from tkinter import filedialog


def export_to_excel(data, file_path=None):
    """Exporta datos a Excel y permite una ruta estable del proyecto.

    El diálogo se conserva solo como compatibilidad para código externo que
    llame esta función sin una ruta de proyecto.
    """
    df = pd.DataFrame(data)
    if file_path is None:
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx")
    if not file_path:
        return None
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    df.to_excel(file_path, index=False)
    print(f"Matriz exportada a: {file_path}")
    return str(file_path)
