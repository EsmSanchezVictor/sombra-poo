import sys, importlib.abc, importlib.util, os
sys.path.insert(0, os.getcwd())
class OptionalBlocked(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('pvlib','pythermalcomfort'):
            raise ModuleNotFoundError(f'Optional dependency disabled for fallback regression: {fullname}', name=fullname)
sys.meta_path.insert(0, OptionalBlocked())
_original_find_spec = importlib.util.find_spec
def optional_find_spec(name, package=None):
    if name.split('.')[0] in ('pvlib', 'pythermalcomfort'):
        return None
    return _original_find_spec(name, package)
importlib.util.find_spec = optional_find_spec
import pytest
raise SystemExit(pytest.main(['-q','-ra','-W','error::ResourceWarning','-W','error::pytest.PytestUnraisableExceptionWarning','-p','no:cacheprovider']))
