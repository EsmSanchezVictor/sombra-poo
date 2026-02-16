import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

radio = 1.0
n_puntos = 80

theta = np.linspace(0, np.pi, n_puntos)
phi = np.linspace(0, 2*np.pi, n_puntos)
psi = np.linspace(0, 2*np.pi, n_puntos)

x4d = radio * np.sin(theta[:, None, None]) * np.cos(phi[:, None]) * np.cos(psi[None, :, None])
y4d = radio * np.sin(theta[:, None, None]) * np.cos(phi[:, None]) * np.sin(psi[None, :, None])
z4d = radio * np.sin(theta[:, None, None]) * np.sin(phi[:, None])
w4d = radio * np.cos(theta[:, None, None])

x3d = x4d[:, :, 0]
y3d = y4d[:, :, 0]
z3d = z4d[:, :, 0]

#Crear ventana de Tk
ventana = tk.Tk()
ventana.title("Gráfica 3D")

#Crear figura y eje 3D
fig = plt.Figure(figsize=(8, 8))
ax = fig.add_subplot(111, projection='3d')

#Agregar figura a la ventana de Tk
canvas = FigureCanvasTkAgg(fig, master=ventana)
canvas.draw()
canvas.get_tk_widget().pack()

def update(frame):
    ax.clear()
    ax.set_axis_off()

    # Rotar la gráfica
    ax.view_init(azim=frame)

    colors = np.sin(z3d + frame / 10.0)
    ax.scatter(x3d.ravel(), y3d.ravel(), z3d.ravel(), c=colors.ravel(), cmap='viridis')

ani = animation.FuncAnimation(fig, update, frames=200, interval=50)

ventana.mainloop()