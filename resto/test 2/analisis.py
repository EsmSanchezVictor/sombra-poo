import os
import cv2
import numpy as np
import tensorflow as tf
from tkinter import Tk, filedialog
import matplotlib.pyplot as plt

# Configuración global
target_size = (512, 512)
model_path = 'best_model.h5'

# Cargar el modelo pre-entrenado
print("\nCargando modelo pre-entrenado...")
model = tf.keras.models.load_model(model_path)

# Función de predicción y visualización
def predecir_y_visualizar(ruta_imagen):
    original = cv2.imread(ruta_imagen)
    if original is None:
        print(f"No se pudo cargar la imagen: {ruta_imagen}")
        return
    
    resized = cv2.resize(original, target_size)
    pred = model.predict(np.expand_dims(resized/255.0, axis=0))[0]
    
    plt.figure(figsize=(15,8))
    
    plt.subplot(1,3,1)
    plt.title('Imagen Original')
    plt.imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
    plt.axis('off')
    
    plt.subplot(1,3,2)
    plt.title('Máscara Predicha')
    plt.imshow(pred.squeeze(), cmap='jet')
    plt.axis('off')
    
    plt.subplot(1,3,3)
    plt.title('Superposición')
    plt.imshow(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
    plt.imshow(pred.squeeze(), alpha=0.5, cmap='jet')
    plt.axis('off')
    
    plt.tight_layout()
    plt.show()

# Selección de imagen mediante diálogo
root = Tk()
root.withdraw()
file_path = filedialog.askopenfilename(
    title="Seleccione una imagen para analizar",
    filetypes=[("Imágenes", "*.jpg *.jpeg *.png")]
)
root.destroy()

if file_path:
    print("\nProcesando imagen...")
    predecir_y_visualizar(file_path)
    print("\nVisualización completada!")
else:
    print("\nNo se seleccionó ninguna imagen.")