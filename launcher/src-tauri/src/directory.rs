use std::{
    fs::File,
    mem::zeroed,
    os::windows::{
        ffi::OsStrExt,
        io::{AsRawHandle, FromRawHandle},
    },
    path::Path,
};
use windows_sys::Win32::{
    Foundation::{INVALID_HANDLE_VALUE, WAIT_OBJECT_0},
    Storage::FileSystem::{
        CreateFileW, ReadDirectoryChangesW, FILE_FLAG_BACKUP_SEMANTICS, FILE_FLAG_OVERLAPPED,
        FILE_LIST_DIRECTORY, FILE_NOTIFY_CHANGE_FILE_NAME, FILE_NOTIFY_CHANGE_LAST_WRITE,
        FILE_NOTIFY_CHANGE_SIZE, FILE_SHARE_DELETE, FILE_SHARE_READ, FILE_SHARE_WRITE,
        OPEN_EXISTING,
    },
    System::{
        Threading::{CreateEventW, ResetEvent, WaitForSingleObject, INFINITE},
        IO::{CancelIoEx, GetOverlappedResult, OVERLAPPED},
    },
};

pub struct DirectoryWatcher {
    directory: File,
    event: File,
    overlapped: Box<OVERLAPPED>,
    buffer: Box<[u32; 4096]>,
    pending: bool,
}

impl DirectoryWatcher {
    pub fn open(path: &Path) -> Result<Self, String> {
        let path: Vec<u16> = path.as_os_str().encode_wide().chain(Some(0)).collect();
        unsafe {
            let directory = CreateFileW(
                path.as_ptr(),
                FILE_LIST_DIRECTORY,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                std::ptr::null(),
                OPEN_EXISTING,
                FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OVERLAPPED,
                std::ptr::null_mut(),
            );
            if directory == INVALID_HANDLE_VALUE {
                return Err(std::io::Error::last_os_error().to_string());
            }
            let directory = File::from_raw_handle(directory);
            let event = CreateEventW(std::ptr::null(), 1, 0, std::ptr::null());
            if event.is_null() {
                return Err(std::io::Error::last_os_error().to_string());
            }
            let event = File::from_raw_handle(event);
            let mut overlapped: Box<OVERLAPPED> = Box::new(zeroed());
            overlapped.hEvent = event.as_raw_handle();
            let mut watcher = Self {
                directory,
                event,
                overlapped,
                buffer: Box::new([0; 4096]),
                pending: false,
            };
            watcher.arm()?;
            Ok(watcher)
        }
    }

    fn arm(&mut self) -> Result<(), String> {
        unsafe {
            ResetEvent(self.event.as_raw_handle());
            if ReadDirectoryChangesW(
                self.directory.as_raw_handle(),
                self.buffer.as_mut_ptr().cast(),
                std::mem::size_of_val(self.buffer.as_ref()) as u32,
                0,
                FILE_NOTIFY_CHANGE_FILE_NAME
                    | FILE_NOTIFY_CHANGE_LAST_WRITE
                    | FILE_NOTIFY_CHANGE_SIZE,
                std::ptr::null_mut(),
                self.overlapped.as_mut(),
                None,
            ) == 0
            {
                return Err(std::io::Error::last_os_error().to_string());
            }
            self.pending = true;
            Ok(())
        }
    }

    pub fn next(&mut self) -> Result<bool, String> {
        unsafe {
            if WaitForSingleObject(self.event.as_raw_handle(), INFINITE) != WAIT_OBJECT_0 {
                return Err(std::io::Error::last_os_error().to_string());
            }
            let mut bytes = 0;
            if GetOverlappedResult(
                self.directory.as_raw_handle(),
                self.overlapped.as_ref(),
                &mut bytes,
                0,
            ) == 0
            {
                return Err(std::io::Error::last_os_error().to_string());
            }
            self.pending = false;
            let changed = contains_pid_notification(self.buffer.as_ref(), bytes as usize)?;
            self.arm()?;
            Ok(changed)
        }
    }
}

impl Drop for DirectoryWatcher {
    fn drop(&mut self) {
        if self.pending {
            unsafe {
                CancelIoEx(self.directory.as_raw_handle(), self.overlapped.as_ref());
                let mut bytes = 0;
                GetOverlappedResult(
                    self.directory.as_raw_handle(),
                    self.overlapped.as_ref(),
                    &mut bytes,
                    1,
                );
            }
        }
    }
}

fn contains_pid_notification(buffer: &[u32], bytes: usize) -> Result<bool, String> {
    if bytes == 0 {
        return Ok(true);
    }
    if bytes > std::mem::size_of_val(buffer) {
        return Err("Notificação de diretório inválida.".to_string());
    }
    let mut offset = 0;
    loop {
        if offset % 4 != 0 || offset + 12 > bytes {
            return Err("Notificação de diretório truncada.".to_string());
        }
        let row = &buffer[offset / 4..];
        let length = row[2] as usize;
        if length % 2 != 0 || offset + 12 + length > bytes {
            return Err("Nome de notificação inválido.".to_string());
        }
        let name =
            unsafe { std::slice::from_raw_parts(row.as_ptr().add(3).cast::<u16>(), length / 2) };
        let name = String::from_utf16_lossy(name);
        if name.eq_ignore_ascii_case("game.pid")
            || name.eq_ignore_ascii_case("launcher-session.json")
        {
            return Ok(true);
        }
        let next = row[0] as usize;
        if next == 0 {
            return Ok(false);
        }
        if next < 12 + length {
            return Err("Deslocamento de notificação inválido.".to_string());
        }
        offset = offset
            .checked_add(next)
            .ok_or("Notificação de diretório muito grande.")?;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        fs,
        sync::mpsc,
        time::{Duration, SystemTime, UNIX_EPOCH},
    };

    #[test]
    fn native_notification_observes_pid_publication_without_polling_logs() {
        let id = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!("kof-launcher-directory-{id}"));
        fs::create_dir_all(&root).unwrap();
        let (ready_tx, ready_rx) = mpsc::channel();
        let (event_tx, event_rx) = mpsc::channel();
        let watched = root.clone();
        let worker = std::thread::spawn(move || {
            let mut watcher = DirectoryWatcher::open(&watched).unwrap();
            ready_tx.send(()).unwrap();
            while !watcher.next().unwrap() {}
            event_tx.send(()).unwrap();
        });
        ready_rx.recv_timeout(Duration::from_secs(3)).unwrap();
        fs::write(root.join("mods-output.log"), "log").unwrap();
        assert!(event_rx.recv_timeout(Duration::from_millis(60)).is_err());
        fs::write(root.join("game.pid"), "1234").unwrap();
        event_rx.recv_timeout(Duration::from_secs(3)).unwrap();
        worker.join().unwrap();
        fs::remove_dir_all(root).unwrap();
    }
}
