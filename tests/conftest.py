import importlib.machinery
import importlib.util
import os
import sys

# The script under test, `muse-record`, has no .py suffix (it is meant to be
# run directly), so load it as a module explicitly.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_loader = importlib.machinery.SourceFileLoader("muse_record", os.path.join(_ROOT, "muse-record"))
_spec = importlib.util.spec_from_loader("muse_record", _loader)
muse_record = importlib.util.module_from_spec(_spec)
_loader.exec_module(muse_record)
sys.modules["muse_record"] = muse_record
