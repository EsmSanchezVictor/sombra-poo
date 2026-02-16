import os
import json
import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

# Configuración
data_dir = 'test 2/dataset/'
target_size = (512, 512)
json_path = 'test 2/mascaras.json'

# 1. Generar máscaras corregido
def crear_mascaras(json_path, output_dir):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    
    for item in data["_via_img_metadata"].values():
        if not item['regions']:
            continue

        # Cargar imagen original para obtener dimensiones
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
            
            # Escalado correcto con dimensiones originales
            scaled_points = np.array([[
                int(px * target_size[1] / w),
                int(py * target_size[0] / h)
            ] for px, py in zip(x, y)], dtype=np.int32)
            
            cv2.fillPoly(mask, [scaled_points], 255)
        
        # Mantener la extensión original del archivo
        mask_name = os.path.splitext(item['filename'])[0] + '_mask.png'
        cv2.imwrite(os.path.join(output_dir, mask_name), mask)

crear_mascaras(json_path, 'mascaras_generadas')

# 2. Carga de datos mejorada
def cargar_datos(img_dir, mask_dir):
    images, masks = [], []
    
    for img_name in os.listdir(img_dir):
        base_name = os.path.splitext(img_name)[0]
        mask_path = os.path.join(mask_dir, f"{base_name}_mask.png")
        
        if not os.path.exists(mask_path):
            continue
            
        # Cargar imagen
        img = cv2.imread(os.path.join(img_dir, img_name))
        img = cv2.resize(img, target_size)
        img = img / 255.0
        
        # Cargar máscara
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        mask = cv2.resize(mask, target_size)
        mask = (mask > 127).astype(np.float32)[..., np.newaxis]
        
        images.append(img)
        masks.append(mask)
    
    return np.array(images), np.array(masks)

images, masks = cargar_datos(data_dir, 'mascaras_generadas')

# 3. Modelo U-Net mejorado
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

model = build_unet((*target_size, 3))
model.summary()

# 4. Entrenamiento con callbacks
checkpoint = tf.keras.callbacks.ModelCheckpoint(
    'best_model.h5',
    save_best_only=True,
    monitor='val_loss',
    mode='min'
)

early_stop = tf.keras.callbacks.EarlyStopping(
    patience=10,
    restore_best_weights=True
)

x_train, x_val, y_train, y_val = train_test_split(
    images, masks, test_size=0.2, random_state=42)

history = model.fit(
    x_train, y_train,
    validation_data=(x_val, y_val),
    batch_size=8,
    epochs=3,
    callbacks=[checkpoint, early_stop]
) 

# 5. Predicción mejorada
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

predecir_y_visualizar("test 2/5499597.jpg")

# 6. Exportación TFLite optimizada
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

with open('modelo_optimizado.tflite', 'wb') as f:
    f.write(tflite_model)

print("\n✅ Modelo listo para producción!")