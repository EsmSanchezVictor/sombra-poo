import tkinter as tk
from tkinter import ttk
import pandas as pd

class ExcelPreview:
    def __init__(self, parent_frame):
        self.frame = tk.Frame(parent_frame)
        self.notebook = ttk.Notebook(self.frame)
        
        # Pestaña para Árboles
        self.tree_frame = ttk.Frame(self.notebook)
        self.tree_table = ttk.Treeview(self.tree_frame)
        self._setup_table(self.tree_frame, self.tree_table, 
                        ["X", "Y", "Altura (m)", "Densidad Copa", "Radio Copa (m)"],
                        [80, 80, 100, 120, 120])
        
        # Pestaña para Estructuras
        self.struct_frame = ttk.Frame(self.notebook)
        self.struct_table = ttk.Treeview(self.struct_frame)
        self._setup_table(self.struct_frame, self.struct_table,
                        ["Tipo", "X1", "Y1", "X2", "Y2", "Altura (m)", "Opacidad", "Material"],
                        [100, 60, 60, 60, 60, 100, 80, 120])
        
        self.notebook.add(self.tree_frame, text="Árboles")
        self.notebook.add(self.struct_frame, text="Estructuras")
        self.notebook.pack(expand=True, fill='both')
        
    def _setup_table(self, parent, table, columns, widths):
        table = ttk.Treeview(parent, columns=columns, show='headings', selectmode='browse')
        vsb = ttk.Scrollbar(parent, orient="vertical", command=table.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=table.xview)
        
        table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        for col, width in zip(columns, widths):
            table.heading(col, text=col)
            table.column(col, width=width, anchor='center')
        
        table.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        
        self.table = table
        return table

    def update_preview(self, df_arboles, df_estructuras):
        # Actualizar tabla de árboles
        self._clear_table(self.tree_table)
        for _, row in df_arboles.iterrows():
            self.tree_table.insert('', 'end', values=(
                round(row['X'], 2),
                round(row['Y'], 2),
                row['Altura (m)'],
                row['Densidad_copa (0-1)'],
                row['Radio_copa (m)']
            ))
        
        # Actualizar tabla de estructuras
        self._clear_table(self.struct_table)
        for _, row in df_estructuras.iterrows():
            self.struct_table.insert('', 'end', values=(
                row['Tipo'],
                round(row['X_inicial'], 2),
                round(row['Y_inicial'], 2),
                round(row['X_final'], 2),
                round(row['Y_final'], 2),
                row['Altura (m)'],
                row['Opacidad (0-1)'],
                row['Material']
            ))

    def _clear_table(self, table):
        for item in table.get_children():
            table.delete(item)

    def get_frame(self):
        return self.frame