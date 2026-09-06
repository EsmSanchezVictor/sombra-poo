from pathlib import Path


def test_scene3d_no_legacy_addactor2d_call():
    source = (Path(__file__).parents[1] / "ui" / "scene3d.py").read_text(encoding="utf-8")
    assert "renderer.AddActor2D(" not in source
    assert "renderer.AddViewProp(scalar_bar)" in source


def test_scalar_bar_can_be_added_as_view_prop_when_vtk_available():
    try:
        import vtk
    except Exception:
        return
    renderer = vtk.vtkRenderer()
    scalar_bar = vtk.vtkScalarBarActor()
    renderer.AddViewProp(scalar_bar)
    assert renderer.GetViewProps().GetNumberOfItems() >= 1
