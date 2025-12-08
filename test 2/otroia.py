import cv2
import numpy as np
import tensorflow as tf
from tkinter import Tk, filedialog
import matplotlib.pyplot as plt

# Configuración
model_path = 'best_model.h5'  # Ruta a tu modelo entrenado
target_size = (512, 512)      # Debe coincidir con el tamaño de entrenamiento

def cargar_modelo():
    """Carga el modelo pre-entrenado"""
    return tf.keras.models.load_model('best_model.h5')

def procesar_imagen(model):
    """Procesa una imagen seleccionada por el usuario"""
    # Seleccionar imagen
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Seleccionar imagen a procesar")
    
    if not file_path:
        print("No se seleccionó ninguna imagen")
        return
    
    # Cargar y preprocesar imagen
    img = cv2.imread(file_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    original_shape = img.shape
    img_resized = cv2.resize(img, target_size)
    img_normalized = img_resized / 255.0
    
    # Hacer predicción
    mask = model.predict(np.expand_dims(img_normalized, axis=0))[0]
    mask_binaria = (mask.squeeze() > 0.5).astype(np.uint8)
    
    # Generar matriz de valores RGB promedio
    img_gris = np.mean(img_resized, axis=2)  # Promedio de canales RGB
    matriz_sombra = img_gris * mask_binaria   # Aplicar máscara
    
    # Escalar a 0-255 y convertir a entero
    matriz_sombra_escalada = (matriz_sombra * 255).astype(np.uint8)
    
    # Mostrar resultados
    plt.figure(figsize=(15, 5))
    
    plt.subplot(1, 3, 1)
    plt.imshow(img_resized)
    plt.title('Imagen Original')
    plt.axis('off')
    
    plt.subplot(1, 3, 2)
    plt.imshow(mask_binaria, cmap='gray')
    plt.title('Máscara de Sombra')
    plt.axis('off')
    
    plt.subplot(1, 3, 3)
    plt.imshow(matriz_sombra_escalada, cmap='gray', vmin=0, vmax=255)
    plt.title('Matriz de Intensidades')
    plt.axis('off')
    
    plt.tight_layout()
    plt.show()
    
    # Guardar resultados
    cv2.imwrite('matriz_sombra.png', matriz_sombra_escalada)
    np.savetxt('matriz_sombra.csv', matriz_sombra_escalada, delimiter=',', fmt='%d')
    
    print("Procesamiento completado!")
    print(f"Matriz guardada como: matriz_sombra.png y matriz_sombra.csv")

if __name__ == "__main__":
    model = cargar_modelo()
    procesar_imagen(model)