"""Compatibilidad con el nombre histórico y el inicio con autenticación."""


def __getattr__(name):
    if name == "App":
        from ui.app_ui import SombraApp
        return SombraApp
    raise AttributeError(name)


def main():
    from main import main as start
    return start()


if __name__ == "__main__":
    main()
