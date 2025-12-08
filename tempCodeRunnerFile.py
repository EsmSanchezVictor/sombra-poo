import tkinter as tk
from database_manager import DatabaseManager
from main_app import MainApp

def main():
    root = tk.Tk()
    db_manager = DatabaseManager()
    # Crear usuario administrador inicial si no existe
    if not db_manager.get_user("admin"):
        db_manager.add_user("admin", "admin", 1, "Administrador", "", "", "", "", "", "", "")
    MainApp(root, db_manager)
    root.mainloop()

if __name__ == "__main__":
    main()