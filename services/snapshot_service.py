import os
from typing import Any, Optional

import numpy as np
import pandas as pd
from PIL import Image

from core.project import Project


class SnapshotService:
    def save_snapshot(self, app: Any, project: Project, state: Optional[dict] = None) -> Optional[int]:
        if project is None:
            return None
        project.ensure_structure()
        state = state or {"next_n": 1}
        n = project.allocate_n(state)

        if getattr(app, "img_rgb", None) is not None:
            img = app.img_rgb
            if isinstance(img, Image.Image):
                image = img
            else:
                image = Image.fromarray(img)
            image.save(os.path.join(project.images_dir, f"elemento{n}.png"))

        if getattr(app, "curva_img_pil_original", None) is not None:
            app.curva_img_pil_original.save(os.path.join(project.curves_dir, f"Celemento{n}.png"))

        matrix = getattr(app, "tmrt_map", None)
        if matrix is None and getattr(app, "shape_selector", None) is not None:
            matrix = getattr(app.shape_selector, "area_seleccionada", None)
        if matrix is not None:
            pd.DataFrame(np.array(matrix)).to_excel(
                os.path.join(project.matrices_dir, f"MAelemento{n}.xlsx"),
                index=False,
            )

        mask = getattr(app, "mask", None)
        if mask is not None:
            pd.DataFrame(np.array(mask)).to_excel(
                os.path.join(project.masks_dir, f"Melemento{n}.xlsx"),
                index=False,
            )

        model_data = getattr(app, "last_T", None)
        if model_data is not None:
            pd.DataFrame(np.array(model_data)).to_excel(
                os.path.join(project.excels_dir, "modelo.xlsx"),
                index=False,
            )

        edit_data = getattr(app, "last_shadow", None)
        if edit_data is not None:
            pd.DataFrame(np.array(edit_data)).to_excel(
                os.path.join(project.excels_dir, "edicion.xlsx"),
                index=False,
            )

        return n