import os
import json
from core.safe_io import atomic_write_json
import numpy as np
import cv2
import shutil
from datetime import datetime
from core.file_versioning import safe_path
#from PIL import Image

class DatasetSaver:
    def __init__(self, app):
        self.app = app
        self.mask_data = self._empty_via_data()
        self._loaded_project_root = None

    @staticmethod
    def _empty_via_data():
        return {
            "_via_settings": {"ui": {}, "core": {"filepath": {}, "default_filepath": ""},
                              "project": {"name": "sombra_project"}},
            "_via_img_metadata": {},
            "_via_attributes": {"region": {}, "file": {}},
            "_via_data_format_version": "2.0.10",
            "_via_image_id_list": [],
        }

    def load_existing_data(self):
        """Carga anotaciones VIA desde analisis/dataset del proyecto activo."""
        project = getattr(getattr(self.app, "project_manager", None), "current_project", None)
        if project is None:
            self.mask_data = self._empty_via_data(); return
        root = os.path.abspath(project.root_path)
        if self._loaded_project_root == root:
            return
        path = project.layout.via_annotations
        try:
            with open(path, "r", encoding="utf-8") as fh:
                self.mask_data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            self.mask_data = self._empty_via_data()
        self._loaded_project_root = root

    def save_dataset(self, img_filename=None, mask_filename=None, save_image=False):
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
            self.load_existing_data()
            image_root = current_project.layout.images_dir
            os.makedirs(image_root, exist_ok=True)
            if img_filename is None or mask_filename is None:
                n = current_project.allocate_n()
            
            # Generar nombre de archivo único basado en timestamp
            img_filename = img_filename or f"elemento{n}.jpg"
            mask_filename = mask_filename or f"Melemento{n}.png"
            
            # La imagen original se importa una sola vez a entradas/imagenes.
            # Guardar Dataset actualiza anotaciones/máscaras; nunca duplica una
            # fotografía que ya pertenece al proyecto.
            src_path = getattr(self.app, "current_image_path", None)
            src_abs = os.path.abspath(src_path) if src_path and os.path.exists(src_path) else None
            image_root_abs = os.path.abspath(image_root)
            already_in_project = bool(
                src_abs and os.path.commonpath([src_abs, image_root_abs]) == image_root_abs
            )
            if already_in_project:
                img_path = src_abs
            elif src_abs:
                # Entrada externa: importación deduplicada por contenido.
                img_path = current_project.layout.import_input_file(src_abs, image_root)
            elif save_image:
                img_path = str(safe_path(image_root, img_filename))
                cv2.imwrite(img_path, cv2.cvtColor(self.app.img_rgb, cv2.COLOR_RGB2BGR))
            else:
                raise FileNotFoundError(f"Imagen actual inexistente: {src_path}")
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
            try:
                self.app.project_manager.autosave_project()
            except Exception:
                pass
            raise

    def update_mask_json(self, img_filename, mask_filename):
        """Actualiza el archivo JSON con los nuevos datos de la máscara"""
        try:
            current_project = self.app.project_manager.current_project
            image_path = getattr(self.app, "current_image_path", None) or os.path.join(current_project.layout.images_dir, img_filename)
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
            
            # Guardar JSON dentro del proyecto.
            os.makedirs(current_project.layout.dataset_dir, exist_ok=True)
            atomic_write_json(current_project.layout.via_annotations, self.mask_data, indent=2, ensure_ascii=False)
                
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

            # v19: la máscara del dataset pertenece al análisis activo.
            analysis_id = getattr(self.app, "current_analysis_id", None)
            if analysis_id:
                mask_path = current_project.layout.element_paths(analysis_id)["dataset_mask"]
            else:
                mask_path = os.path.join(current_project.layout.dataset_dir, mask_filename)
            os.makedirs(os.path.dirname(mask_path), exist_ok=True)
            if not cv2.imwrite(str(mask_path), mask):
                raise RuntimeError(f"No se pudo guardar la máscara en {mask_path}")

            return mask_path
            
        except Exception as e:
            print(f"Error crítico al guardar máscara: {str(e)}")
            # Mostrar mensaje de error en la interfaz si es posible
            if hasattr(self.app, 'show_error_message'):
                self.app.show_error_message(f"Error al guardar máscara: {str(e)}")
            raise