from pathlib import Path
import contextlib, runpy, traceback
root=Path(__file__).resolve().parents[2]
try:
    with (Path(__file__).parent/'bootstrap-output.log').open('a',encoding='utf-8',buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            runpy.run_path(str(root/'tools/run_experimental.py'),run_name='__main__')
except Exception:
    (Path(__file__).parent/'launcher-error.log').write_text(traceback.format_exc(),encoding='utf-8')
