import os
import json
import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.model_selection import train_test_split
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog

# Configuración global
data_dir = 'test 2/dataset/'
target_size = (512, 512)
json_path = 'test 2/mascaras.json'
model_path = 'best_model.h5'
mask_dir = 'mascaras_generadas'

# 1. Función para generar máscaras
def crear_mascaras(json_path, output_dir):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    
    for item in data["_via_img_metadata"].values():
        if not item['regions']:
            continue

        img_path = os.path.join(data_dir, item['filename'])
        original_img = cv2.imread(img_path)
        if original_img is None:
            print(f"Error cargando: {img_path}")
            continue
            
        h, w = original_img.shape[:2]
        mask = np.zeros(target_size, dtype=np.uint8)
        
        for region in item['regions']:
            x = region['shape_attributes']['all_points_x']
            y = region['shape_attributes']['all_points_y']
            
            scaled_points = np.array([[
                int(px * target_size[1] / w),
                int(py * target_size[0] / h)
            ] for px, py in zip(x, y)], dtype=np.int32)
            
            cv2.fillPoly(mask, [scaled_points], 255)
        
        mask_name = os.path.splitext(item['filename'])[0] + '_mask.png'
        cv2.imwrite(os.path.join(output_dir, mask_name), mask)

# 2. Función para cargar datos
def cargar_datos(img_dir, mask_dir):
    images, masks = [], []
    
    for img_name in os.listdir(img_dir):
        base_name = os.path.splitext(img_name)[0]
        mask_path = os.path.join(mask_dir, f"{base_name}_mask.png")
        
        if not os.path.exists(mask_path):
            continue
            
        img = cv2.imread(os.path.join(img_dir, img_name))
        img = cv2.resize(img, target_size)
        img = img / 255.0
        
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        mask = cv2.resize(mask, target_size)
        mask = (mask > 127).astype(np.float32)[..., np.newaxis]
        
        images.append(img)
        masks.append(mask)
    
    return np.array(images), np.array(masks)

# 3. Arquitectura del modelo U-Net
def build_unet(input_shape):
    inputs = layers.Input(input_shape)
    
    # Encoder
    c1 = layers.Conv2D(32, (3,3), activation='relu', padding='same')(inputs)
    c1 = layers.Conv2D(32, (3,3), activation='relu', padding='same')(c1)
    p1 = layers.MaxPooling2D((2,2))(c1)
    
    c2 = layers.Conv2D(64, (3,3), activation='relu', padding='same')(p1)
    c2 = layers.Conv2D(64, (3,3), activation='relu', padding='same')(c2)
    p2 = layers.MaxPooling2D((2,2))(c2)
    
    # Centro
    c3 = layers.Conv2D(128, (3,3), activation='relu', padding='same')(p2)
    c3 = layers.Conv2D(128, (3,3), activation='relu', padding='same')(c3)
    
    # Decoder
    u1 = layers.UpSampling2D((2,2))(c3)
    u1 = layers.concatenate([u1, c2])
    c4 = layers.Conv2D(64, (3,3), activation='relu', padding='same')(u1)
    c4 = layers.Conv2D(64, (3,3), activation='relu', padding='same')(c4)
    
    u2 = layers.UpSampling2D((2,2))(c4)
    u2 = layers.concatenate([u2, c1])
    c5 = layers.Conv2D(32, (3,3), activation='relu', padding='same')(u2)
    c5 = layers.Conv2D(32, (3,3), activation='relu', padding='same')(c5)
    
    outputs = layers.Conv2D(1, (1,1), activation='sigmoid')(c5)
    
    model = models.Model(inputs=[inputs], outputs=[outputs])
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-4),
                 loss='binary_crossentropy',
                 metrics=['accuracy'])
    return model

# 4. Función de predicción y visualización
def predecir_y_visualizar(ruta_imagen):
    original = cv2.imread(ruta_imagen)
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

# Flujo principal del programa
if __name__ == "__main__":
    # Verificar si el modelo ya existe
    if os.path.exists(model_path):
        print("\nModelo pre-entrenado encontrado. Cargando...")
        model = tf.keras.models.load_model(model_path)
    else:
        print("\nEntrenando nuevo modelo...")
        crear_mascaras(json_path, mask_dir)
        images, masks = cargar_datos(data_dir, mask_dir)
        
        model = build_unet((*target_size, 3))
        
        # Callbacks
        checkpoint = tf.keras.callbacks.ModelCheckpoint(
            model_path,
            save_best_only=True,
            monitor='val_loss',
            mode='min'
        )
        
        early_stop = tf.keras.callbacks.EarlyStopping(
            patience=10,
            restore_best_weights=True
        )
        
        # Dividir datos
        x_train, x_val, y_train, y_val = train_test_split(
            images, masks, test_size=0.2, random_state=42)
        
        # Entrenamiento
        print("\nIniciando entrenamiento...")
        history = model.fit(
            x_train, y_train,
            validation_data=(x_val, y_val),
            batch_size=8,
            epochs=5,
            callbacks=[checkpoint, early_stop]
        )
        print("\nEntrenamiento completado!")

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

    # Opcional: Exportar a TFLite
    # converter = tf.lite.TFLiteConverter.from_keras_model(model)
    # converter.optimizations = [tf.lite.Optimize.DEFAULT]
    # tflite_model = converter.convert()
    # with open('modelo_optimizado.tflite', 'wb') as f:
    #     f.write(tflite_model)

    plt.show()