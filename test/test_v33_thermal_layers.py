from test.source_helpers import scene_source
from pathlib import Path


def test_vtk_thermal_layer_is_translucent_and_separated():
    source = scene_source()
    assert 'ground.GetProperty().SetOpacity(0.50)' in source
    assert 'ground.GetProperty().LightingOff()' in source
    assert 'base.GetProperty().SetColor(0.93, 0.93, 0.90)' in source
    assert 'vtkContourFilter' in source
    assert 'contours.GenerateValues(6, lo, hi)' in source


def test_physical_objects_are_visually_separated_from_temperature():
    source = scene_source()
    assert 'actor.GetProperty().SetOpacity(1.0)' in source
    assert 'actor.GetProperty().EdgeVisibilityOn()' in source
    assert 'actor.GetProperty().SetEdgeColor(0.16, 0.16, 0.16)' in source
    assert 'opacity = 0.96 if rho is None' in source
