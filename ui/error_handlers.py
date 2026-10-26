"""Presentación de errores de callbacks Tk."""
def install_tk_error_handler(root, logger):
    def report(exception_type, exception, traceback):
        from tkinter import messagebox
        from core.local_time import LocalTimeError
        logger.error('Error de callback de la interfaz',exc_info=(exception_type,exception,traceback))
        if isinstance(exception, LocalTimeError):
            messagebox.showerror('Fecha y hora del escenario', str(exception))
        else:
            messagebox.showerror('Error de la aplicación','Se produjo un error. El detalle quedó en el registro de diagnóstico local.')
    root.report_callback_exception = report
