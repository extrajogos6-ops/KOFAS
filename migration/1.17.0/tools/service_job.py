"""Keep only this launcher's newly created services in a Windows Job Object.

KILL_ON_JOB_CLOSE also handles console closure or abrupt supervisor exit, when
Python finally blocks cannot run. Unrelated/existing processes are never added.
See https://learn.microsoft.com/windows/win32/procthread/job-objects
"""
import ctypes


class BasicLimits(ctypes.Structure):
    _fields_ = [
        ('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
        ('flags', ctypes.c_uint32), ('minimum_working_set', ctypes.c_size_t),
        ('maximum_working_set', ctypes.c_size_t), ('active_processes', ctypes.c_uint32),
        ('affinity', ctypes.c_size_t), ('priority', ctypes.c_uint32),
        ('scheduling', ctypes.c_uint32),
    ]


class IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in (
        'read_operations', 'write_operations', 'other_operations',
        'read_bytes', 'write_bytes', 'other_bytes')]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ('basic', BasicLimits), ('io', IoCounters),
        ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
        ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t),
    ]


class ServiceJob:
    def __init__(self):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        self.kernel.CreateJobObjectW.restype = ctypes.c_void_p
        self.kernel.SetInformationJobObject.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
        self.kernel.SetInformationJobObject.restype = ctypes.c_int
        self.kernel.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.kernel.AssignProcessToJobObject.restype = ctypes.c_int
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        self.kernel.CloseHandle.restype = ctypes.c_int
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(
                self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def add(self, process):
        if not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            error = ctypes.WinError(ctypes.get_last_error())
            # This process was just created by the caller, but not added to the job.
            process.terminate()
            process.wait(timeout=10)
            raise error

    def close(self):
        if self.handle:
            if not self.kernel.CloseHandle(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self.handle = None
