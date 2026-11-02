"""Windows service lifecycle tests using disposable CLI children; no game or UI."""
import importlib.util
import ctypes
from pathlib import Path
import subprocess
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'tools' / 'service_job.py'


@unittest.skipUnless(sys.platform == 'win32', 'Windows Job Objects')
class ServiceJobTest(unittest.TestCase):
    def load_job(self):
        spec = importlib.util.spec_from_file_location('experimental_service_job', SOURCE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ServiceJob()

    def child(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                                 creationflags=0x08000000)
        self.addCleanup(self.stop_child, child)
        return child

    @staticmethod
    def stop_child(child):
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)

    def test_closing_job_terminates_assigned_cli_child(self):
        job = self.load_job()
        self.addCleanup(job.close)
        child = self.child()
        job.add(child)
        job.close()
        child.wait(timeout=5)
        self.assertIsNotNone(child.returncode)

    def test_closing_job_preserves_unassigned_cli_child(self):
        job = self.load_job()
        self.addCleanup(job.close)
        assigned = self.child()
        unrelated = self.child()
        job.add(assigned)
        job.close()
        assigned.wait(timeout=5)
        self.assertIsNone(unrelated.poll())

    def test_close_is_safe_twice(self):
        job = self.load_job()
        job.close()
        job.close()

    def test_abrupt_supervisor_exit_also_terminates_assigned_child(self):
        code = (
            'import os,subprocess,sys; '
            f'sys.path.insert(0, {str(SOURCE.parent)!r}); '
            'from service_job import ServiceJob; job=ServiceJob(); '
            'child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"],'
            'stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=0x08000000); '
            'job.add(child); print(child.pid,flush=True); os._exit(0)'
        )
        parent = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, creationflags=0x08000000)
        output, error = parent.communicate(timeout=5)
        self.assertEqual(parent.returncode, 0, error)
        child_pid = int(output.strip())
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x100000, False, child_pid)
        if handle:
            try:
                self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0)
            finally:
                kernel.CloseHandle(handle)


if __name__ == '__main__':
    unittest.main()
