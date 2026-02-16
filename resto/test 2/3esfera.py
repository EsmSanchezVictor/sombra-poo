import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation

#Parámetros de la esfera en 4D
radio = 1.0

#Número de puntos en la esfera
n_puntos = 100

#Ángulos en 4D
theta = np.linspace(0, np.pi, n_puntos)
phi = np.linspace(0, 2*np.pi, n_puntos)
psi = np.linspace(0, 2*np.pi, n_puntos)

#Generar coordenadas en 4D
x4d = radio * np.sin(theta[:, None, None]) * np.cos(phi[:, None]) * np.cos(psi[None, :, None])
y4d = radio * np.sin(theta[:, None, None]) * np.cos(phi[:, None]) * np.sin(psi[None, :, None])
z4d = radio * np.sin(theta[:, None, None]) * np.sin(phi[:, None])
w4d = radio * np.cos(theta[:, None, None])

#Proyección en 3D
x3d = x4d[:, :, 0]
y3d = y4d[:, :, 0]
z3d = z4d[:, :, 0]

#Crear figura y eje 3D
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

#Función de actualización para la animación
def update(frame):
    ax.clear()
    ax.set_xlim(-radio, radio)
    ax.set_ylim(-radio, radio)
    ax.set_zlim(-radio, radio)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    
    # Cambiar el color de los puntos según su posición
    colors = np.sin(z3d + frame / 10.0)
    ax.scatter(x3d.ravel(), y3d.ravel(), z3d.ravel(), c=colors.ravel(), cmap='viridis')

#Crear la animación
ani = animation.FuncAnimation(fig, update, frames=200, interval=50)

plt.show()