import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.animation import FuncAnimation

class Sphere4DProjection:
    def __init__(self, num_points=10000):
        self.num_points = num_points
        self.generate_4d_points()
        
    def generate_4d_points(self):
        theta = np.random.uniform(0, 2*np.pi, self.num_points)
        phi = np.arccos(1 - 2*np.random.uniform(0, 1, self.num_points))
        psi = np.random.uniform(0, 2*np.pi, self.num_points)
        omega = np.random.uniform(0, 2*np.pi, self.num_points)
        
        r = 1.0
        x = r * np.sin(phi) * np.cos(theta)
        y = r * np.sin(phi) * np.sin(theta)
        z = r * np.cos(phi)
        w = r * np.sin(psi) * np.cos(omega)
        
        self.points_4d = np.column_stack([x, y, z, w])
    
    def project_to_3d(self, w_slice):
        mask = np.abs(self.points_4d[:, 3] - w_slice) < 0.1
        return self.points_4d[mask, :3]
    
    def animate_projection(self):
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        def update(frame):
            ax.clear()
            w_slice = frame / 50.0
            points = self.project_to_3d(w_slice)
            
            # Mapeo de colores alternativo usando coordenadas
            colors = np.linalg.norm(points, axis=1)
            
            ax.scatter(points[:, 0], points[:, 1], points[:, 2],
                      c=colors, cmap='viridis', alpha=0.7)
            
            ax.set_title(f'4D Sphere Projection (w = {w_slice:.2f})')
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)
            ax.set_zlim(-1, 1)

        animation = FuncAnimation(fig, update, frames=100, interval=50)
        plt.show()

def main():
    projection = Sphere4DProjection()
    projection.animate_projection()

if __name__ == "__main__":
    main()