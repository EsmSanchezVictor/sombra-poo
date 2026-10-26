"""Puerto de interacción: el núcleo nunca crea diálogos ni importa Tk."""
import logging


class InteractionRequiredError(RuntimeError):
    pass


class HeadlessInteraction:
    @staticmethod
    def showerror(title, text):
        logging.getLogger('sombra.projects').error('%s: %s', title, text)

    @staticmethod
    def showwarning(title, text):
        logging.getLogger('sombra.projects').warning('%s: %s', title, text)

    @staticmethod
    def showinfo(title, text):
        logging.getLogger('sombra.projects').info('%s: %s', title, text)

    @staticmethod
    def _request(*args, **kwargs):
        raise InteractionRequiredError('Esta operación requiere un adaptador de interacción explícito.')

    askyesno = _request
    asksaveasfilename = _request
    askopenfilename = _request
    askdirectory = _request
    ask_text = _request
    ask_project_name = _request
    ask_project_location = _request
