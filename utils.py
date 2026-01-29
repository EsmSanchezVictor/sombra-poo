import pandas as pd
from tkinter import filedialog

def export_to_excel(data):
    """Exporta datos a un archivo Excel y devuelve la ruta seleccionada."""
    df = pd.DataFrame(data)
    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx")
    if file_path:
        df.to_excel(file_path, index=False)
        print(f"Matriz exportada a: {file_path}")
        return file_path
    return None
