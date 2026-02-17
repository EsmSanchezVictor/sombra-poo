import os
import json
import numpy as np
import cv2
import shutil
from datetime import datetime
from core.file_versioning import safe_path
#from PIL import Image

class DatasetSaver:
    def __init__(self, app):
        self.app = app
        self.mask_data = {}
        self.dataset_dir = "DataSetSombra"  # Nueva carpeta principal
        os.makedirs(self.dataset_dir, exist_ok=True)  # Crear carpeta si no existe
        self.load_existing_data()
        
    def load_existing_data(self):
        """Carga los datos existentes del archivo mascaras.json si existe"""
        try:
            with open('mascaras.json', 'r') as f:
                self.mask_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Si el archivo no existe o está vacío, empezamos con una estructura básica
            self.mask_data = {
                "_via_settings": {
                    "ui": {
                        "annotation_editor_height": 25,
                        "annotation_editor_fontsize": 0.8,
                        "leftsidebar_width": 18,
                        "image_grid": {
                            "img_height": 80,
                            "rshape_fill": "none",
                            "rshape_fill_opacity": 0.3,
                            "rshape_stroke": "yellow",
                            "rshape_stroke_width": 2,
                            "show_region_shape": True,
                            "show_image_policy": "all"
                        },
                        "image": {
                            "region_label": "__via_region_id__",
                            "region_color": "__via_default_region_color__",
                            "region_label_font": "10px Sans",
                            "on_image_annotation_editor_placement": "NEAR_REGION"
                        }
                    },
                    "core": {
                        "buffer_size": "18",
                        "filepath": {},
                        "default_filepath": ""
                    },
                    "project": {
                        "name": f"via_project_{datetime.now().strftime('%d%b%Y_%Hh%Mm')}"
                    }
                },
                "_via_img_metadata": {},
                "_via_attributes": {
                    "region": {},
                    "file": {}
                },
                "_via_data_format_version": "2.0.10",
                "_via_image_id_list": []
            }

    def save_dataset(self, img_filename=None, mask_filename=None, save_image=True):
        """Guarda la imagen y la máscara en los directorios correspondientes"""
        project = getattr(self.app, "project_manager", None)
        current_project = project.current_project if project else None
        if not current_project:
            return
        if not self.app.img_rgb.size or not self.app.shape_selector.area_seleccionada.size:
            print("Error: No hay imagen o área seleccionada para guardar")
            return
            
        try:
            current_project.ensure_structure()
            image_root = os.path.join(current_project.root_path, "imagenes")
            os.makedirs(image_root, exist_ok=True)
            if img_filename is None or mask_filename is None:
                n = current_project.allocate_n()
            
            # Generar nombre de archivo único basado en timestamp
            img_filename = img_filename or f"elemento{n}.jpg"
            mask_filename = mask_filename or f"Melemento{n}.png"
            
            # Guardar imagen original o reutilizar imagen actual validada
            img_path = safe_path(image_root, img_filename)
            img_path = str(img_path)
            if save_image:
                cv2.imwrite(img_path, cv2.cvtColor(self.app.img_rgb, cv2.COLOR_RGB2BGR))
            else:
                src_path = getattr(self.app, "current_image_path", None)
                if not src_path or not os.path.exists(src_path):
                    raise FileNotFoundError(f"Imagen actual inexistente: {src_path}")
                if os.path.abspath(src_path) != os.path.abspath(img_path):
                    shutil.copy2(src_path, img_path)
            if not os.path.exists(img_path):
                raise FileNotFoundError(f"No existe imagen para dataset: {img_path}")

            img_filename = os.path.basename(img_path)
            self.app.current_image_path = img_path
            self.app.current_image_basename = img_filename
            self.app.current_image_stem = os.path.splitext(img_filename)[0]
            print(f"[dataset] Imagen registrada: {img_path}")


            # Registrar último recurso guardado para snapshots
            self.app.last_image_path = img_path
                        
            # Crear y guardar máscara
            saved_mask = self.save_mask(img_filename, mask_filename)
            mask_filename = os.path.basename(str(saved_mask))
            self.app.last_mask_path = str(saved_mask)
            
            # Actualizar archivo JSON
            self.update_mask_json(img_filename, mask_filename)
            
            print(f"Datos guardados correctamente: {img_filename}")
        except Exception as e:
            print(f"Error al guardar dataset: {str(e)}")
            self.app.project_manager.save_project()

    def update_mask_json(self, img_filename, mask_filename):
        """Actualiza el archivo JSON con los nuevos datos de la máscara"""
        try:
            current_project = self.app.project_manager.current_project
            image_path = getattr(self.app, "current_image_path", None) or os.path.join(current_project.root_path, "imagenes", img_filename)
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"No se puede actualizar JSON sin imagen existente: {image_path}")
            img_filename = os.path.basename(image_path)            
            # Obtener tamaño de la imagen
            img_size = os.path.getsize(image_path)
            
            
            # Generar estructura de datos para la máscara
            mask_entry = {
                "filename": img_filename,
                "size": img_size,
                "regions": [],
                "file_attributes": {}
            }
            
            # Agregar información de la región según el tipo de selección
            region = {
                "shape_attributes": {},
                "region_attributes": {}
            }
            
            if self.app.selection_type.get() == "Rectángulo":
                x1, y1 = int(self.app.shape_selector.start_point[0]), int(self.app.shape_selector.start_point[1])
                x2, y2 = int(self.app.shape_selector.end_point[0]), int(self.app.shape_selector.end_point[1])
                
                # Convertir a formato de polígono (4 puntos)
                all_points_x = [x1, x2, x2, x1]
                all_points_y = [y1, y1, y2, y2]
                
                region["shape_attributes"] = {
                    "name": "polygon",
                    "all_points_x": all_points_x,
                    "all_points_y": all_points_y
                }
                
            elif self.app.selection_type.get() == "Círculo":
                center_x, center_y = int(self.app.shape_selector.start_point[0]), int(self.app.shape_selector.start_point[1])
                radius = int(np.sqrt((self.app.shape_selector.end_point[0] - self.app.shape_selector.start_point[0])**2 + (self.app.shape_selector.end_point[1] - self.app.shape_selector.start_point[1])**2))
                
                # Aproximar círculo como polígono de 36 puntos
                points = []
                for i in range(36):
                    angle = 2 * np.pi * i / 36
                    x = center_x + radius * np.cos(angle)
                    y = center_y + radius * np.sin(angle)
                    points.append((int(x), int(y)))
                
                all_points_x = [p[0] for p in points]
                all_points_y = [p[1] for p in points]
                
                region["shape_attributes"] = {
                    "name": "polygon",
                    "all_points_x": all_points_x,
                    "all_points_y": all_points_y
                }
                
            elif self.app.selection_type.get() == "Polígono":
                all_points_x = [int(p[0]) for p in self.app.shape_selector.polygon_points_aux]
                all_points_y = [int(p[1]) for p in self.app.shape_selector.polygon_points_aux]
                
                region["shape_attributes"] = {
                    "name": "polygon",
                    "all_points_x": all_points_x,
                    "all_points_y": all_points_y
                }
            
            mask_entry["regions"].append(region)
            
            # Agregar entrada al JSON
            file_id = f"{img_filename}{img_size}"
            self.mask_data["_via_img_metadata"][file_id] = mask_entry
            if file_id not in self.mask_data["_via_image_id_list"]:
                self.mask_data["_via_image_id_list"].append(file_id)
            
            # Guardar JSON
            with open('mascaras.json', 'w') as f:
                json.dump(self.mask_data, f, indent=2)
                
        except Exception as e:
            print(f"Error al actualizar JSON: {str(e)}")
            raise
    def save_mask(self, img_filename, mask_filename):
        """Crea y guarda la máscara como imagen PNG binaria"""
        try:
            current_project = self.app.project_manager.current_project
            # Verificar que hay una imagen cargada
            if not hasattr(self.app, 'img_rgb') or self.app.img_rgb is None:
                raise ValueError("No hay imagen cargada para crear la máscara")

            # Crear máscara binaria del mismo tamaño que la imagen (inicialmente todo negro)
            mask = np.zeros(self.app.img_rgb.shape[:2], dtype=np.uint8)
            
            # Obtener el tipo de selección actual
            selection_type = self.app.selection_type.get()

            if selection_type == "Rectángulo":
                # Verificar que hay puntos de inicio y fin
                if not hasattr(self.app.shape_selector, 'start_point') or not hasattr(self.app.shape_selector, 'end_point'):
                    raise ValueError("No se han definido los puntos del rectángulo")
                    
                # Convertir coordenadas a enteros
                x1, y1 = int(self.app.shape_selector.start_point[0]), int(self.app.shape_selector.start_point[1])
                x2, y2 = int(self.app.shape_selector.end_point[0]), int(self.app.shape_selector.end_point[1])
                
                # Asegurar que las coordenadas estén dentro de los límites de la imagen
                height, width = self.app.img_rgb.shape[:2]
                x1, x2 = np.clip([x1, x2], 0, width-1)
                y1, y2 = np.clip([y1, y2], 0, height-1)
                
                # Dibujar rectángulo blanco sobre fondo negro
                cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
                
            elif selection_type == "Círculo":
                # Verificar que hay puntos de inicio y fin
                if not hasattr(self.app.shape_selector, 'start_point') or not hasattr(self.app.shape_selector, 'end_point'):
                    raise ValueError("No se han definido los puntos del círculo")
                    
                # Convertir centro a enteros
                center_x, center_y = int(self.app.shape_selector.start_point[0]), int(self.app.shape_selector.start_point[1])
                
                # Calcular radio
                radius = int(np.sqrt((self.app.shape_selector.end_point[0] - center_x)**2 + 
                                (self.app.shape_selector.end_point[1] - center_y)**2))
                
                # Asegurar que el círculo esté dentro de los límites de la imagen
                height, width = self.app.img_rgb.shape[:2]
                radius = min(radius, min(center_x, width-center_x, center_y, height-center_y))
                
                # Dibujar círculo blanco sobre fondo negro
                cv2.circle(mask, (center_x, center_y), radius, 255, -1)
                
            elif selection_type == "Polígono":
                # Verificar que hay puntos definidos                                    
                if not hasattr(self.app.shape_selector, 'polygon_points') or len(self.app.shape_selector.polygon_points_aux) < 3:
                    raise ValueError("Se necesitan al menos 3 puntos para formar un polígono")
                    
                # Convertir puntos a formato numpy array (int32)
                pts = np.array([[int(x), int(y)] for x, y in self.app.shape_selector.polygon_points_aux], dtype=np.int32)
                
                # Reformar a formato que OpenCV espera: (1, N, 2)
                pts = pts.reshape((-1, 1, 2))
                
                # Dibujar polígono blanco relleno sobre fondo negro
                cv2.fillPoly(mask, [pts], color=255)
                
            else:
                raise ValueError(f"Tipo de selección no soportado: {selection_type}")

            # Crear directorio si no existe
            os.makedirs(os.path.join(current_project.root_path, "mascaras"), exist_ok=True)
            
            # Guardar máscara como imagen PNG binaria (blanco=selección, negro=fondo)
            mask_path = safe_path(os.path.join(current_project.root_path, "mascaras"), mask_filename)
            if not cv2.imwrite(str(mask_path), mask):
                raise RuntimeError(f"No se pudo guardar la máscara en {mask_path}")

            return mask_path
            
        except Exception as e:
            print(f"Error crítico al guardar máscara: {str(e)}")
            # Mostrar mensaje de error en la interfaz si es posible
            if hasattr(self.app, 'show_error_message'):
                self.app.show_error_message(f"Error al guardar máscara: {str(e)}")
            raise