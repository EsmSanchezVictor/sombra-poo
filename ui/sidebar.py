"""Componentes de interfaz de Proyecto Sombra."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from ui.layout import PANEL_CONTENT_RATIO, PANEL_HORIZONTAL_SCALE, calcular_geometria_contenido_panel, calcular_ancho_sidebar_abierto

class SidebarMixin:
    """Responsabilidad extraída conservando los métodos y sus callbacks."""

    def _ancho_viewport_actual(self):
        """Ancho usable para dimensionar el lateral en el estado actual."""
        try:
            ancho = int(self.root.winfo_width())
        except (TypeError, ValueError, tk.TclError):
            ancho = 1
        if ancho <= 200:
            try:
                ancho = int(self.root.winfo_screenwidth())
            except (TypeError, ValueError, tk.TclError):
                ancho = 1366
        return max(ancho, 1)

    def _reservar_ancho_sidebar(self, ancho):
        """Reserva físicamente la columna 0 para que frame1 no se comprima.

        ``place`` no participa en el cálculo de tamaño de ``grid``. Por eso
        configurar solo ``frame1.config(width=...)`` no garantizaba que la
        columna 0 recibiera ese ancho. El ``minsize`` de la columna sí lo
        garantiza y evita que el panel quede recortado contra frame2/frame4.
        """
        ancho = max(int(ancho), 1)
        self.frame1.configure(width=ancho)
        self.root.grid_columnconfigure(0, weight=0, minsize=ancho)
        return ancho

    def _recalcular_ancho_sidebar_abierto(self):
        self.panel_width = calcular_ancho_sidebar_abierto(self._ancho_viewport_actual())
        return self.panel_width

    def _crear_panel_desplazable(self, contenedor):
        """Crea el viewport común de TODOS los paneles laterales.

        v24 (sobre la geometría segura de v22):
        - reducción HORIZONTAL real: el sidebar completo es ~30 % más angosto
          y los widgets con ancho explícito se reducen al 70 %;
        - el contenido ocupa el 96 % del Canvas, con márgenes de ~2 % por lado,
          para no desperdiciar espacio lateral;
        - la barra vertical vive en una columna propia (fuera del Canvas),
          por lo que jamás se superpone con botones, entradas o etiquetas;
        - el texto largo se envuelve automáticamente al ancho real;
        - la rueda del mouse se vincula localmente a widgets no editables,
          evitando un ``bind_all`` global que podía interferir con otros
          controles de la aplicación.
        """
        contenedor.grid_rowconfigure(0, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_columnconfigure(1, weight=0)

        canvas = tk.Canvas(
            contenedor,
            bg=self.palette["panel"],
            highlightthickness=0,
            bd=0,
            yscrollincrement=18,
        )
        scrollbar = tk.Scrollbar(
            contenedor,
            orient="vertical",
            command=canvas.yview,
            width=10,
            takefocus=False,
        )
        contenido = tk.Frame(canvas, bg=self.palette["panel"], bd=0)

        # La scrollbar se reserva en column=1. El Canvas solamente usa
        # column=0, así que su viewport ya excluye físicamente la barra.
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        ventana_id = canvas.create_window((0, 0), window=contenido, anchor="nw")

        def _actualizar_scrollregion():
            bbox = canvas.bbox("all")
            if bbox is not None:
                canvas.configure(scrollregion=bbox)

        def _ajustar_textos(widget, ancho):
            # Label/Checkbutton/Radiobutton/Button admiten wraplength.
            # Esto cubre también textos de botones largos que antes podían
            # quedar cortados al reducir el ancho del contenido.
            wrap = max(80, int(ancho) - 10)
            for hijo in widget.winfo_children():
                if isinstance(hijo, (tk.Label, tk.Checkbutton, tk.Radiobutton, tk.Button)):
                    try:
                        hijo.config(wraplength=wrap)
                    except tk.TclError:
                        pass
                _ajustar_textos(hijo, ancho)

        def _escalar_horizontal(valor, factor=PANEL_HORIZONTAL_SCALE):
            """Reduce sólo espaciados/ancho horizontales; no toca altura."""
            if valor in (None, "", 0, "0"):
                return valor
            if isinstance(valor, (tuple, list)):
                return tuple(max(0, int(round(float(v) * factor))) for v in valor)
            texto = str(valor).strip()
            if " " in texto:
                partes = [p for p in texto.split() if p]
                try:
                    return tuple(max(0, int(round(float(v) * factor))) for v in partes)
                except ValueError:
                    return valor
            try:
                return max(0, int(round(float(valor) * factor)))
            except (TypeError, ValueError):
                return valor

        def _compactar_widget_horizontal(widget):
            """v24: compacta exclusivamente el ANCHO una sola vez.

            No se modifican font, height, pady ni ipady. Los controles con
            sticky=ew quedan más angostos porque el propio sidebar es ~30 %
            menor; los controles con width/length explícitos también se
            reducen al 70 %. Así la reducción es visible y no vertical.
            """
            if getattr(widget, "_panel_horizontal_v24", False):
                return
            widget._panel_horizontal_v24 = True

            # Sólo padding horizontal administrado por grid/pack.
            try:
                manager = widget.winfo_manager()
                if manager == "grid":
                    info = widget.grid_info()
                    cambios = {}
                    for clave in ("padx", "ipadx"):
                        if clave in info:
                            cambios[clave] = _escalar_horizontal(info[clave])
                    if cambios:
                        widget.grid_configure(**cambios)
                elif manager == "pack":
                    info = widget.pack_info()
                    cambios = {}
                    for clave in ("padx", "ipadx"):
                        if clave in info:
                            cambios[clave] = _escalar_horizontal(info[clave])
                    if cambios:
                        widget.pack_configure(**cambios)
            except (tk.TclError, ValueError, TypeError):
                pass

            # Sólo ancho explícito. La altura se conserva intacta.
            try:
                valor = float(widget.cget("width"))
                if valor > 1:
                    widget.configure(width=max(1, int(round(valor * PANEL_HORIZONTAL_SCALE))))
            except (tk.TclError, ValueError, TypeError):
                pass

            # En Scale, length es la dimensión horizontal principal.
            if isinstance(widget, tk.Scale):
                try:
                    valor = float(widget.cget("length"))
                    if valor > 5:
                        widget.configure(length=max(5, int(round(valor * PANEL_HORIZONTAL_SCALE))))
                except (tk.TclError, ValueError, TypeError):
                    pass

        def _compactar_arbol_horizontal(widget):
            for hijo in widget.winfo_children():
                _compactar_widget_horizontal(hijo)
                _compactar_arbol_horizontal(hijo)

        # La rueda se aplica solo a elementos que no tienen un comportamiento
        # de rueda propio. Entradas, escalas y Combobox quedan intactos; la
        # scrollbar sigue estando siempre visible para esos casos.
        _wheel_bound = set()

        def _on_mousewheel(event):
            delta = getattr(event, "delta", 0)
            if delta:
                canvas.yview_scroll(int(-1 * (delta / 120)), "units")
            elif getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")
            return "break"

        def _vincular_rueda(widget):
            for hijo in widget.winfo_children():
                # No interceptar la rueda de controles editables/interactivos.
                if not isinstance(hijo, (tk.Entry, tk.Scale, ttk.Combobox, tk.Listbox, tk.Text)):
                    key = str(hijo)
                    if key not in _wheel_bound:
                        hijo.bind("<MouseWheel>", _on_mousewheel, add="+")
                        hijo.bind("<Button-4>", _on_mousewheel, add="+")
                        hijo.bind("<Button-5>", _on_mousewheel, add="+")
                        _wheel_bound.add(key)
                _vincular_rueda(hijo)

        canvas.bind("<MouseWheel>", _on_mousewheel, add="+")
        canvas.bind("<Button-4>", _on_mousewheel, add="+")
        canvas.bind("<Button-5>", _on_mousewheel, add="+")
        contenido.bind("<MouseWheel>", _on_mousewheel, add="+")
        contenido.bind("<Button-4>", _on_mousewheel, add="+")
        contenido.bind("<Button-5>", _on_mousewheel, add="+")

        _vertical_sync_job = None

        def _sincronizar_alto_y_scroll():
            nonlocal _vertical_sync_job
            _vertical_sync_job = None
            alto = max(canvas.winfo_height(), contenido.winfo_reqheight())
            try:
                actual = float(canvas.itemcget(ventana_id, "height") or 0)
            except (TypeError, ValueError, tk.TclError):
                actual = 0
            if abs(actual - alto) > 1:
                canvas.itemconfig(ventana_id, height=alto)
            _actualizar_scrollregion()

        def _on_contenido_configure(_event):
            nonlocal _vertical_sync_job
            _compactar_arbol_horizontal(contenido)
            _vincular_rueda(contenido)
            # El wrap de textos puede aumentar el alto pedido DESPUÉS del
            # resize horizontal. Sin esta segunda sincronización, el Canvas
            # podía conservar el alto previo y recortar las últimas filas.
            if _vertical_sync_job is None:
                _vertical_sync_job = canvas.after_idle(_sincronizar_alto_y_scroll)

        contenido.bind("<Configure>", _on_contenido_configure, add="+")

        def _on_canvas_resize(event):
            # v24: contenido al 96 % del Canvas (~2 % de margen por lado).
            # La reducción horizontal no se logra con márgenes grandes, sino
            # con el sidebar y anchos explícitos más compactos.
            x, ancho = calcular_geometria_contenido_panel(
                event.width, PANEL_CONTENT_RATIO
            )
            canvas.coords(ventana_id, x, 0)
            canvas.itemconfig(ventana_id, width=ancho)

            # Si el contenido entra verticalmente, completar el alto visible;
            # si no, respetar su alto pedido para que la barra pueda recorrerlo.
            alto = max(event.height, contenido.winfo_reqheight())
            canvas.itemconfig(ventana_id, height=alto)
            _ajustar_textos(contenido, ancho)
            canvas.after_idle(_actualizar_scrollregion)

        canvas.bind("<Configure>", _on_canvas_resize, add="+")

        # Guardar referencias facilita depuración y mantiene viva la relación
        # explícita panel -> canvas -> scrollbar.
        if not hasattr(self, "panel_canvases"):
            self.panel_canvases = []
        if not hasattr(self, "panel_scrollbars"):
            self.panel_scrollbars = []
        self.panel_canvases.append(canvas)
        self.panel_scrollbars.append(scrollbar)

        return contenido

    def toggle_panel(self, index):
        """Abre, cierra, o cambia de panel lateral.

        BUG CORREGIDO ("conflicto al tocar los íconos"): antes, para
        cambiar de un panel a otro, se cerraba el viejo y se programaba
        abrir el nuevo con `frame1.after(250, ...)` — un tiempo fijo
        inventado que NO espera a que la animación de cierre realmente
        termine. animate_panel_close reduce el ancho de a 10px cada
        10ms, así que con un panel de, por ejemplo, 260px de ancho, el
        cierre tarda 260ms — MÁS que los 250ms de espera. Resultado: el
        open_panel del panel nuevo arrancaba mientras el close_panel
        del viejo todavía estaba corriendo, y las dos animaciones
        terminaban escribiendo `frame1.config(width=...)` una encima de
        la otra — de ahí el conflicto visual.

        Ahora close_panel() recibe un callback `on_complete` y recién
        llama a open_panel() cuando el cierre TERMINÓ de verdad — sin
        adivinar tiempos. Además, cualquier clic nuevo invalida
        cualquier animación vieja todavía en curso (ver
        self._panel_anim_token), así que ya no hace falta bloquear el
        clic con `if self.is_animating: return` — un clic de más ya no
        puede corromper nada, como mucho reinicia la animación.
        """
        if not self.require_project("acceder a los paneles"):
            return
        self._panel_anim_token += 1  # invalida cualquier animación en curso

        if self.active_panel is not None and self.active_panel != index:
            self.close_panel(self.active_panel, on_complete=lambda: self.open_panel(index))
        elif self.active_panel == index:
            self.close_panel(self.active_panel)
            self.active_panel = None
        else:
            self.open_panel(index)

    def open_panel(self, index):
        """Abre (despliega) el panel lateral 'index' (0-3).

        GEOMETRÍA v22: los paneles internos usan .place(), por lo que no
        participan del cálculo de tamaño de grid. Configurar solamente
        ``frame1.width`` no alcanzaba: en una prueba 1400x900 frame1
        pedía 260 px pero la columna 0 recibía 218 px, y el borde derecho
        del panel quedaba recortado al comenzar frame2/frame4. Ahora la
        apertura reserva el ancho completo mediante ``minsize`` en la
        columna 0 antes de animar. close_panel devuelve esa reserva al
        ancho de la barra de íconos al terminar.
        """
        if not self.require_project("acceder a los paneles"):
            return
        token = self._panel_anim_token
        self.active_panel = index
        self.is_animating = True
        # BUG CORREGIDO ("los íconos no manejan bien el cambio de
        # paneles"): antes la barra de íconos se pasaba a horizontal
        # DESPUÉS de arrancar la animación y frame1 se agrandaba a
        # iconos+panel — pero grid ignora ese config(width) y el panel,
        # que crece al ancho que le pide su contenido (~400px), quedaba
        # superpuesto sobre el área de escena. Ahora: íconos
        # horizontales primero, frame1 = ancho del panel, y la
        # animación fuerza el ancho exacto del panel (place width).
        self.switch_buttons_to_horizontal()
        self._recalcular_ancho_sidebar_abierto()
        self._reservar_ancho_sidebar(self.panel_width)
        self.animate_panel_open(index, 0, token)
        if index == 1:
            self.show_panel2_frames()
        elif index == 2:
            self.show_diseno_frames()
        elif index == 3:
            self.show_modelo_frames()
        self.switch_buttons_to_horizontal()
        self.highlight_button(index)

    def animate_panel_open(self, index, current_width, token=None):
        """Animación de apertura: el ANCHO del panel crece de a 10px
        por frame hasta llegar a self.panel_width. Para tocar la
        velocidad, ajustar el paso (+10) o el delay (after(10, ...)).

        SINCRONIZACIÓN: si `token` ya no coincide con
        self._panel_anim_token, quiere decir que otra acción (otro
        clic) interrumpió esta animación mientras estaba en curso —
        esta corrida "vieja" se corta acá mismo en vez de seguir
        peleando por frame1/el panel con la animación nueva.

        ALTURA (bug corregido en la vuelta anterior): antes era
        relheight=1 (= 100% del alto de frame1) posicionado en
        y=button_height — eso hace que el panel mida MÁS que el espacio
        libre debajo de la barra de íconos, y el sobrante quedaba por
        debajo del borde inferior real de la ventana, invisible. Con
        height=-button_height, place() resta esa franja del alto total.

        ANCHO: place() lleva width= explícito en cada paso, así el
        panel mide EXACTAMENTE self.panel_width (antes, sin width,
        place usaba el ancho pedido por el contenido y el panel quedaba
        superpuesto al área de escena). button_height se toma con
        winfo_reqheight() para no depender de si los íconos ya se
        redibujaron en horizontal.

        Cada paso se encola vía _panel_anim_step (comando Tcl
        persistente — ver __init__) en vez de re-registrar callables
        con widget.after(), que colisionaba por reuso de id().
        """
        self._panel_anim_step("open", index, current_width, token)

    def _panel_anim_step(self, op, index, width, token):
        """Un único handler Tcl persistente para los pasos de las
        animaciones de panel (op = "open" | "close"). Se registró UNA
        vez en __init__ (_anim_cmd); cada paso se encola con
        tk.call("after", 10, _anim_cmd, ...) sobre ese nombre estable.

        Recibe los argumentos como strings (los pasa Tcl) — acá se
        convierten. Primero se valida el token: si la animación que
        encoló este paso ya no es la actual, el paso se descarta sin
        re-encolar (así las corridas viejas se abortan solas)."""
        index = int(index)
        width = int(width)
        token = int(token)
        if token != self._panel_anim_token:
            return
        button_height = max(self.buttons[0].winfo_reqheight(), 30)
        outer = self.panel_outer_frames[index]
        if op == "open":
            if width < self.panel_width:
                outer.config(width=width)
                outer.place(
                    x=0, y=button_height, relheight=1, height=-button_height,
                    width=width,
                )
                self.root.tk.call("after", 10, self._anim_cmd, "open", index, width + 10, token)
            else:
                outer.config(width=self.panel_width)
                outer.place(
                    x=0, y=button_height, relheight=1, height=-button_height,
                    width=self.panel_width,
                )
                self.is_animating = False
        else:
            if width > 0:
                outer.config(width=width)
                outer.place(
                    x=0, y=button_height, relheight=1, height=-button_height,
                    width=width,
                )
                self.root.tk.call("after", 10, self._anim_cmd, "close", index, width - 10, token)
            else:
                outer.place_forget()
                if self._open_after_close.get(index) == token:
                    del self._open_after_close[index]
                    callback = self._close_callbacks.pop(index, None)
                    if callback is not None:
                        callback()
                    else:
                        self.open_panel(index)
                else:
                    icon_width = max(self.sidebar_closed_width, self.icon_frame.winfo_reqwidth(), 40)
                    self._reservar_ancho_sidebar(icon_width)
                    self.is_animating = False

    def close_panel(self, index, on_complete=None):
        """Cierra el panel 'index'. Si se pasa on_complete, se llama
        recién cuando la animación de cierre TERMINÓ de verdad — así
        se encadena una apertura sin adivinar tiempos (ver toggle_panel).

        BUG CORREGIDO: cuando el cierre va encadenado a una apertura
        (on_complete != None) ya no se vuelve a vertical la barra de
        íconos — antes la volteaba y al toque open_panel la volvía
        horizontal, y el panel saltaba de lugar durante el cambio."""
        token = self._panel_anim_token
        self.is_animating = True
        self.animate_panel_close(index, self.panel_width, token, on_complete)
        self.reset_button(index)
        if on_complete is None:
            self.switch_buttons_to_vertical()

    def animate_panel_close(self, index, current_width, token=None, on_complete=None):
        """Igual que animate_panel_open pero decreciendo el ancho.
        Mismo chequeo de token (ver animate_panel_open) y mismo fix de
        altura (height=-button_height) — antes tenía, además, un
        rely=0.1 mezclado con y=button_height que no tenía relación con
        cómo se abría el panel; se sacó para que abrir/cerrar usen
        exactamente la misma geometría.

        Si viene on_complete (se está encadenando una apertura), NO se
        achica frame1 acá — el open_panel que sigue va a fijar el ancho
        que corresponda; achicarlo acá de paso sería trabajo perdido y,
        peor, un parpadeo visual (achica y al toque vuelve a agrandar).

        Igual que animate_panel_open: width explícito en place() y
        button_height con winfo_reqheight() (ver docstring de open).
        Los pasos se encolan vía _panel_anim_step (comando Tcl
        persistente). Si viene on_complete, se guarda el token en
        self._open_after_close (y el callback en _close_callbacks) y
        _panel_anim_step recién encadena la apertura cuando el cierre
        terminó de verdad.
        """
        if on_complete is not None:
            self._open_after_close[index] = token
            self._close_callbacks[index] = on_complete
        self._panel_anim_step("close", index, current_width, token)

    def hide_all_frames(self):
        """Oculta todos los paneles desplegables. Actúa sobre los
        frames FÍSICOS (panel_outer_frames) — son los que están
        realmente posicionados con .place(); los de contenido
        (panel_frames) viven dentro de un Canvas y no necesitan
        esconderse por separado."""
        for frame in self.panel_outer_frames:
            frame.place_forget()

    def _toggle_frames(self, frames_to_show, frames_to_hide):
        for frame in frames_to_hide:
            frame.grid_remove()
        for frame in frames_to_show:
            frame.grid()

    def show_panel2_frames(self):
        self._toggle_frames(
            [self.frame2, self.frame3, self.frame4, self.frame5, self.frame15],
            [self.frame7, self.frame8, self.frame9, self.frame10, self.frame11, self.frame12, self.frame13, self.frame14],
        )

    def show_diseno_frames(self):
        # v30: un único host ocupa las cuatro celdas centrales. Esto evita
        # tres cuartos vacíos alrededor del gráfico 2D/3D y permite que el
        # Notebook de Edición use todo el viewport disponible.
        self._toggle_frames(
            [self.frame7],
            [self.frame2, self.frame3, self.frame4, self.frame5,
             self.frame8, self.frame9, self.frame10,
             self.frame11, self.frame12, self.frame13, self.frame14, self.frame15],
        )

    def show_modelo_frames(self):
        # v30: mismo criterio para Modelo. frame11 tiene rowspan=2 y
        # columnspan=2, por lo que ocupa el bloque frame2..frame5 completo.
        self._toggle_frames(
            [self.frame11],
            [self.frame2, self.frame3, self.frame4, self.frame5,
             self.frame7, self.frame8, self.frame9, self.frame10,
             self.frame12, self.frame13, self.frame14, self.frame15],
        )

    def highlight_button(self, index):
        for i, button in enumerate(self.buttons):
            button.config(bg="gray80" if i == index else self.frame1.cget("bg"))

    def reset_button(self, index):
        self.buttons[index].config(bg=self.frame1.cget("bg"))

    def switch_buttons_to_horizontal(self):
        for i, button in enumerate(self.buttons):
            button.grid_forget()
            button.grid(row=0, column=i,padx=12, sticky="ew")

    def switch_buttons_to_vertical(self):
        for i, button in enumerate(self.buttons):
            button.grid_forget()
            button.grid(row=i, column=0, sticky="ew")
