use std::ffi::OsString;
use std::mem::{size_of, zeroed};
use std::os::windows::ffi::{OsStrExt, OsStringExt};
use std::path::{Path, PathBuf};
use windows_sys::Win32::Foundation::{
    CloseHandle, FILETIME, HANDLE, HWND, INVALID_HANDLE_VALUE, LPARAM, WAIT_OBJECT_0, WAIT_TIMEOUT,
};
use windows_sys::Win32::System::Diagnostics::ToolHelp::{
    CreateToolhelp32Snapshot, Process32FirstW, Process32NextW, PROCESSENTRY32W, TH32CS_SNAPPROCESS,
};
use windows_sys::Win32::System::Threading::{
    CreateProcessW, GetProcessTimes, OpenProcess, QueryFullProcessImageNameW, ResumeThread,
    TerminateProcess, WaitForSingleObject, CREATE_NO_WINDOW, CREATE_SUSPENDED, PROCESS_INFORMATION,
    PROCESS_QUERY_LIMITED_INFORMATION, PROCESS_SYNCHRONIZE, PROCESS_TERMINATE, STARTUPINFOW,
};
use windows_sys::Win32::UI::WindowsAndMessaging::{
    EnumWindows, GetWindowThreadProcessId, IsWindowVisible, PostMessageW, SetForegroundWindow,
    ShowWindow, SW_RESTORE, WM_CLOSE,
};

#[derive(Clone, Debug)]
pub struct Identity {
    pub pid: u32,
    pub created: u64,
    pub executable: PathBuf,
}

struct OwnedHandle(HANDLE);

impl Drop for OwnedHandle {
    fn drop(&mut self) {
        unsafe {
            CloseHandle(self.0);
        }
    }
}

struct PendingBootstrap {
    process: OwnedHandle,
    thread: OwnedHandle,
    resumed: bool,
}

impl Drop for PendingBootstrap {
    fn drop(&mut self) {
        if !self.resumed {
            unsafe {
                TerminateProcess(self.process.0, 1);
                WaitForSingleObject(self.process.0, 5000);
            }
        }
    }
}

pub fn spawn_registered(
    spec: &crate::core::LaunchSpec,
    publish: impl FnOnce(&Identity) -> Result<(), String>,
) -> Result<(), String> {
    let executable: Vec<u16> = spec
        .executable
        .as_os_str()
        .encode_wide()
        .chain(Some(0))
        .collect();
    let directory: Vec<u16> = spec
        .directory
        .as_os_str()
        .encode_wide()
        .chain(Some(0))
        .collect();
    let mut command = vec![34u16];
    command.extend(spec.executable.as_os_str().encode_wide());
    command.extend("\" -B \"".encode_utf16());
    command.extend(spec.bootstrap.as_os_str().encode_wide());
    command.extend([34, 0]);
    unsafe {
        let mut startup: STARTUPINFOW = zeroed();
        startup.cb = size_of::<STARTUPINFOW>() as u32;
        let mut info: PROCESS_INFORMATION = zeroed();
        if CreateProcessW(
            executable.as_ptr(),
            command.as_mut_ptr(),
            std::ptr::null(),
            std::ptr::null(),
            0,
            CREATE_NO_WINDOW | CREATE_SUSPENDED,
            std::ptr::null(),
            directory.as_ptr(),
            &startup,
            &mut info,
        ) == 0
        {
            return Err(format!(
                "Não foi possível iniciar o jogo: {}",
                std::io::Error::last_os_error()
            ));
        }
        let mut pending = PendingBootstrap {
            process: OwnedHandle(info.hProcess),
            thread: OwnedHandle(info.hThread),
            resumed: false,
        };
        let process = identity_from_handle(info.dwProcessId, pending.process.0)
            .ok_or("Não foi possível identificar a inicialização suspensa.")?;
        publish(&process)?;
        if ResumeThread(pending.thread.0) == u32::MAX {
            return Err(format!(
                "Não foi possível liberar a inicialização: {}",
                std::io::Error::last_os_error()
            ));
        }
        pending.resumed = true;
    }
    Ok(())
}

pub fn stop_game(expected: &Identity) -> Result<(), String> {
    unsafe extern "system" fn request_close(window: HWND, parameter: LPARAM) -> i32 {
        let expected = &*(parameter as *const Identity);
        let mut pid = 0;
        GetWindowThreadProcessId(window, &mut pid);
        if pid == expected.pid
            && IsWindowVisible(window) != 0
            && identity(pid).is_some_and(|actual| {
                actual.created == expected.created && actual.executable == expected.executable
            })
        {
            PostMessageW(window, WM_CLOSE, 0, 0);
        }
        1
    }
    unsafe {
        let raw = OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE | PROCESS_SYNCHRONIZE,
            0,
            expected.pid,
        );
        if raw.is_null() {
            return Err(format!(
                "Não foi possível fechar o jogo: {}",
                std::io::Error::last_os_error()
            ));
        }
        let handle = OwnedHandle(raw);
        let actual = identity_from_handle(expected.pid, handle.0).ok_or("O jogo já terminou.")?;
        if actual.created != expected.created || actual.executable != expected.executable {
            return Err("A identidade do processo mudou; nenhuma ação foi executada.".to_string());
        }
        EnumWindows(Some(request_close), expected as *const Identity as LPARAM);
        match WaitForSingleObject(handle.0, 1500) {
            WAIT_OBJECT_0 => return Ok(()),
            WAIT_TIMEOUT => {}
            _ => return Err(std::io::Error::last_os_error().to_string()),
        }
        if TerminateProcess(handle.0, 0) == 0 && WaitForSingleObject(handle.0, 0) != WAIT_OBJECT_0 {
            return Err(format!(
                "O jogo não pôde ser encerrado: {}",
                std::io::Error::last_os_error()
            ));
        }
        if WaitForSingleObject(handle.0, 5000) != WAIT_OBJECT_0 {
            return Err("O jogo ainda está encerrando.".to_string());
        }
    }
    Ok(())
}

pub fn normalized(path: &Path) -> PathBuf {
    let canonical = path.canonicalize().unwrap_or_else(|_| path.to_path_buf());
    dunce::simplified(&canonical).to_path_buf()
}

fn identity_from_handle(pid: u32, handle: HANDLE) -> Option<Identity> {
    unsafe {
        let mut buffer = vec![0u16; 32768];
        let mut length = buffer.len() as u32;
        let mut created: FILETIME = zeroed();
        let mut exited: FILETIME = zeroed();
        let mut kernel: FILETIME = zeroed();
        let mut user: FILETIME = zeroed();
        let valid = QueryFullProcessImageNameW(handle, 0, buffer.as_mut_ptr(), &mut length) != 0
            && GetProcessTimes(handle, &mut created, &mut exited, &mut kernel, &mut user) != 0
            && exited.dwLowDateTime == 0
            && exited.dwHighDateTime == 0;
        if !valid {
            return None;
        }
        let executable = normalized(&PathBuf::from(OsString::from_wide(
            &buffer[..length as usize],
        )));
        Some(Identity {
            pid,
            created: ((created.dwHighDateTime as u64) << 32) | created.dwLowDateTime as u64,
            executable,
        })
    }
}

pub fn identity(pid: u32) -> Option<Identity> {
    unsafe {
        let raw = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid);
        if raw.is_null() {
            return None;
        }
        let handle = OwnedHandle(raw);
        identity_from_handle(pid, handle.0)
    }
}

pub fn wait_exit(expected: &Identity, timeout_ms: u32) -> Result<bool, String> {
    unsafe {
        let raw = OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_SYNCHRONIZE,
            0,
            expected.pid,
        );
        if raw.is_null() {
            let error = std::io::Error::last_os_error();
            return if error.raw_os_error() == Some(87) {
                Ok(true)
            } else {
                Err(error.to_string())
            };
        }
        let handle = OwnedHandle(raw);
        let Some(actual) = identity_from_handle(expected.pid, handle.0) else {
            return Ok(true);
        };
        if actual.created != expected.created || actual.executable != expected.executable {
            return Ok(true);
        }
        match WaitForSingleObject(handle.0, timeout_ms) {
            WAIT_OBJECT_0 => Ok(true),
            WAIT_TIMEOUT => Ok(false),
            _ => Err(std::io::Error::last_os_error().to_string()),
        }
    }
}

pub fn find_game(expected: &Path) -> Option<Identity> {
    let expected = normalized(expected);
    unsafe {
        let snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if snapshot == INVALID_HANDLE_VALUE {
            return None;
        }
        let mut row: PROCESSENTRY32W = zeroed();
        row.dwSize = size_of::<PROCESSENTRY32W>() as u32;
        let mut valid = Process32FirstW(snapshot, &mut row);
        let mut found = None;
        while valid != 0 {
            let length = row
                .szExeFile
                .iter()
                .position(|value| *value == 0)
                .unwrap_or(row.szExeFile.len());
            if OsString::from_wide(&row.szExeFile[..length])
                .to_string_lossy()
                .eq_ignore_ascii_case("KOF ALLSTAR.exe")
            {
                if let Some(candidate) = identity(row.th32ProcessID) {
                    if candidate.executable == expected {
                        found = Some(candidate);
                        break;
                    }
                }
            }
            valid = Process32NextW(snapshot, &mut row);
        }
        CloseHandle(snapshot);
        found
    }
}

pub fn focus(pid: u32) {
    unsafe extern "system" fn visit(window: HWND, parameter: LPARAM) -> i32 {
        let mut owner = 0;
        GetWindowThreadProcessId(window, &mut owner);
        if owner == parameter as u32 && IsWindowVisible(window) != 0 {
            ShowWindow(window, SW_RESTORE);
            SetForegroundWindow(window);
            return 0;
        }
        1
    }
    unsafe {
        EnumWindows(Some(visit), pid as LPARAM);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::LaunchSpec;
    use std::fs;
    use std::os::windows::process::CommandExt;
    use std::process::{Child, Command};
    use std::time::{Duration, SystemTime, UNIX_EPOCH};

    struct Fixture {
        root: PathBuf,
        child: Option<Child>,
    }

    impl Fixture {
        fn new() -> Self {
            let id = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos();
            let root = std::env::temp_dir().join(format!("kof-launcher-process-{id}"));
            fs::create_dir_all(&root).unwrap();
            fs::write(root.join("start.py"), "from pathlib import Path\nimport time\nPath('executed').write_text('yes')\ntime.sleep(30)\n").unwrap();
            Self { root, child: None }
        }

        fn spec(&self) -> LaunchSpec {
            let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .unwrap()
                .parent()
                .unwrap()
                .to_path_buf();
            LaunchSpec {
                executable: root.join("python/python.exe"),
                bootstrap: self.root.join("start.py"),
                directory: self.root.clone(),
            }
        }
    }

    impl Drop for Fixture {
        fn drop(&mut self) {
            if let Some(child) = &mut self.child {
                let _ = child.kill();
                let _ = child.wait();
            }
            assert!(self.root.is_absolute() && self.root.starts_with(std::env::temp_dir()));
            let _ = fs::remove_dir_all(&self.root);
        }
    }

    #[test]
    fn current_process_identity_has_the_actual_executable_and_creation_time() {
        let current = identity(std::process::id()).unwrap();
        assert_eq!(current.pid, std::process::id());
        assert_eq!(
            current.executable,
            normalized(&std::env::current_exe().unwrap())
        );
        assert!(current.created > 0);
    }

    #[test]
    fn absent_process_has_no_identity() {
        assert!(identity(u32::MAX).is_none());
    }

    #[test]
    fn native_exit_wait_blocks_until_the_verified_process_ends() {
        let mut fixture = Fixture::new();
        let spec = fixture.spec();
        fixture.child = Some(
            Command::new(&spec.executable)
                .arg("-B")
                .arg(&spec.bootstrap)
                .current_dir(&spec.directory)
                .creation_flags(0x08000000)
                .spawn()
                .unwrap(),
        );
        let expected = identity(fixture.child.as_ref().unwrap().id()).unwrap();
        assert!(!wait_exit(&expected, 20).unwrap());
        fixture.child.as_mut().unwrap().kill().unwrap();
        assert!(wait_exit(&expected, 5000).unwrap());
        let mut stale = expected;
        stale.created += 1;
        assert!(wait_exit(&stale, 0).unwrap());
    }

    #[test]
    fn python_native_extensions_receive_regular_windows_paths() {
        let file = std::env::current_exe().unwrap().canonicalize().unwrap();
        let portable = normalized(&file);
        assert!(portable.is_file());
        assert!(!portable.as_os_str().to_string_lossy().starts_with(r"\\?\"));
    }

    #[test]
    fn failed_marker_publication_never_executes_or_leaves_a_bootstrap_alive() {
        let fixture = Fixture::new();
        let marker = fixture.root.join("session.json");
        fs::write(&marker, b"old marker").unwrap();
        let mut permissions = fs::metadata(&marker).unwrap().permissions();
        permissions.set_readonly(true);
        fs::set_permissions(&marker, permissions).unwrap();
        for _ in 0..2 {
            let pending = fixture.root.join("session.pending");
            fs::write(&pending, b"new marker").unwrap();
            let mut pid = None;
            let result = spawn_registered(&fixture.spec(), |process| {
                pid = Some(process.pid);
                fs::rename(&pending, &marker).map_err(|error| error.to_string())
            });
            assert!(result.is_err());
            assert!(identity(pid.expect("process must be created suspended")).is_none());
            assert!(!fixture.root.join("executed").exists());
        }
        let mut permissions = fs::metadata(&marker).unwrap().permissions();
        permissions.set_readonly(false);
        fs::set_permissions(marker, permissions).unwrap();
    }

    #[test]
    fn stop_rejects_a_reused_identity_then_closes_the_expected_process() {
        let mut fixture = Fixture::new();
        let spec = fixture.spec();
        fixture.child = Some(
            Command::new(&spec.executable)
                .arg("-B")
                .arg(&spec.bootstrap)
                .current_dir(&spec.directory)
                .creation_flags(0x08000000)
                .spawn()
                .unwrap(),
        );
        let pid = fixture.child.as_ref().unwrap().id();
        for _ in 0..100 {
            if fixture.root.join("executed").exists() {
                break;
            }
            std::thread::sleep(Duration::from_millis(20));
        }
        assert!(fixture.root.join("executed").exists());
        let expected = identity(pid).unwrap();
        let mut wrong = expected.clone();
        wrong.created += 1;
        assert!(stop_game(&wrong).is_err());
        assert!(identity(pid).is_some());
        wrong = expected.clone();
        wrong.executable = fixture.root.join("other.exe");
        assert!(stop_game(&wrong).is_err());
        assert!(identity(pid).is_some());
        stop_game(&expected).unwrap();
        assert!(identity(pid).is_none());
    }
}
