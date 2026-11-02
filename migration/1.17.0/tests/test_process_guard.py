"""Process-identity checks only: no game, Frida, UI or desktop actions."""
import ctypes
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / 'tools' / 'run_experimental.py'
spec = importlib.util.spec_from_file_location('experimental_runtime_guard', SOURCE)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class ProcessGuardTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.game = self.root / 'game'
        self.marker = self.root / 'active-probe.json'
        self.marker.write_text(json.dumps({'pid': 18832}), encoding='utf-8')
        for name, value in [('DIAGNOSTICS', self.root), ('GAME', self.game)]:
            patcher = patch.object(runtime, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.exit_codes = [259]
        self.image = self.game / 'KOF ALLSTAR.exe'
        self.kernel = Mock()
        self.kernel.OpenProcess.return_value = 123
        self.kernel.GetExitCodeProcess.side_effect = self.get_exit_code
        self.kernel.QueryFullProcessImageNameW.side_effect = self.get_image
        patcher = patch.object(runtime.ctypes, 'WinDLL', return_value=self.kernel, create=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def get_exit_code(self, handle, output):
        value = self.exit_codes.pop(0) if len(self.exit_codes) > 1 else self.exit_codes[0]
        ctypes.cast(output, ctypes.POINTER(ctypes.c_uint32))[0] = value
        return 1

    def get_image(self, handle, flags, buffer, count):
        buffer.value = str(self.image)
        return 1

    def test_exited_process_with_open_handle_is_not_a_running_game(self):
        self.exit_codes = [3489660927]
        self.kernel.QueryFullProcessImageNameW.return_value = 0
        self.kernel.QueryFullProcessImageNameW.side_effect = None
        self.assertFalse(runtime.running_experimental_game())
        self.kernel.QueryFullProcessImageNameW.assert_not_called()
        self.kernel.CloseHandle.assert_called_once_with(123)

    def test_live_matching_process_blocks_a_second_game(self):
        self.assertTrue(runtime.running_experimental_game())
        self.kernel.CloseHandle.assert_called_once_with(123)

    def test_reused_pid_of_another_executable_is_not_this_game(self):
        self.image = self.root / 'other.exe'
        self.assertFalse(runtime.running_experimental_game())
        self.kernel.CloseHandle.assert_called_once_with(123)

    def test_process_exiting_between_checks_is_not_a_running_game(self):
        self.exit_codes = [259, 0]
        self.kernel.QueryFullProcessImageNameW.side_effect = None
        self.kernel.QueryFullProcessImageNameW.return_value = 0
        self.assertFalse(runtime.running_experimental_game())
        self.kernel.CloseHandle.assert_called_once_with(123)

    def test_unknown_identity_of_live_process_remains_blocked(self):
        self.kernel.QueryFullProcessImageNameW.side_effect = None
        self.kernel.QueryFullProcessImageNameW.return_value = 0
        with self.assertRaisesRegex(RuntimeError, 'identidade'):
            runtime.running_experimental_game()
        self.kernel.CloseHandle.assert_called_once_with(123)

    def test_unverifiable_exit_state_remains_blocked(self):
        self.kernel.GetExitCodeProcess.side_effect = None
        self.kernel.GetExitCodeProcess.return_value = 0
        with self.assertRaises(RuntimeError):
            runtime.running_experimental_game()
        self.kernel.CloseHandle.assert_called_once_with(123)

    def test_absent_pid_is_not_a_running_game(self):
        self.kernel.OpenProcess.return_value = 0
        self.assertFalse(runtime.running_experimental_game())
        self.kernel.CloseHandle.assert_not_called()

    def test_missing_marker_does_not_query_windows(self):
        self.marker.unlink()
        self.assertFalse(runtime.running_experimental_game())
        self.kernel.OpenProcess.assert_not_called()


if __name__ == '__main__':
    unittest.main()
