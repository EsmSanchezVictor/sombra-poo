import tkinter as tk
from ui.app_ui import SombraApp

App = SombraApp

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()