use std::{ffi::c_void, os::windows::ffi::OsStrExt, path::Path};
use windows_sys::Win32::{
    Foundation::LocalFree,
    Security::{
        Authorization::{
            ConvertStringSidToSidW, GetNamedSecurityInfoW, SetEntriesInAclW, SetNamedSecurityInfoW,
            EXPLICIT_ACCESS_W, GRANT_ACCESS, SE_FILE_OBJECT, TRUSTEE_IS_SID,
            TRUSTEE_IS_WELL_KNOWN_GROUP,
        },
        DACL_SECURITY_INFORMATION, SUB_CONTAINERS_AND_OBJECTS_INHERIT,
    },
    Storage::FileSystem::{FILE_GENERIC_EXECUTE, FILE_GENERIC_READ},
};

struct LocalMemory(*mut c_void);

impl Drop for LocalMemory {
    fn drop(&mut self) {
        unsafe {
            LocalFree(self.0);
        }
    }
}

pub fn grant_webview_read_access(path: &Path) -> Result<(), String> {
    let path: Vec<u16> = path.as_os_str().encode_wide().chain(Some(0)).collect();
    unsafe {
        let mut old_acl = std::ptr::null_mut();
        let mut descriptor = std::ptr::null_mut();
        let result = GetNamedSecurityInfoW(
            path.as_ptr(),
            SE_FILE_OBJECT,
            DACL_SECURITY_INFORMATION,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            &mut old_acl,
            std::ptr::null_mut(),
            &mut descriptor,
        );
        let _descriptor = LocalMemory(descriptor);
        if result != 0 {
            return Err(std::io::Error::from_raw_os_error(result as i32).to_string());
        }
        if old_acl.is_null() {
            return Ok(());
        }
        let mut entries = Vec::new();
        let mut sids = Vec::new();
        for text in ["S-1-15-2-1", "S-1-15-2-2"] {
            let text: Vec<u16> = text.encode_utf16().chain(Some(0)).collect();
            let mut sid = std::ptr::null_mut();
            if ConvertStringSidToSidW(text.as_ptr(), &mut sid) == 0 {
                return Err(std::io::Error::last_os_error().to_string());
            }
            sids.push(LocalMemory(sid));
            let mut entry: EXPLICIT_ACCESS_W = std::mem::zeroed();
            entry.grfAccessPermissions = FILE_GENERIC_READ | FILE_GENERIC_EXECUTE;
            entry.grfAccessMode = GRANT_ACCESS;
            entry.grfInheritance = SUB_CONTAINERS_AND_OBJECTS_INHERIT;
            entry.Trustee.TrusteeForm = TRUSTEE_IS_SID;
            entry.Trustee.TrusteeType = TRUSTEE_IS_WELL_KNOWN_GROUP;
            entry.Trustee.ptstrName = sid.cast();
            entries.push(entry);
        }
        let mut new_acl = std::ptr::null_mut();
        let result = SetEntriesInAclW(
            entries.len() as u32,
            entries.as_ptr(),
            old_acl,
            &mut new_acl,
        );
        let _new_acl = LocalMemory(new_acl.cast());
        if result != 0 {
            return Err(std::io::Error::from_raw_os_error(result as i32).to_string());
        }
        let result = SetNamedSecurityInfoW(
            path.as_ptr(),
            SE_FILE_OBJECT,
            DACL_SECURITY_INFORMATION,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            new_acl,
            std::ptr::null(),
        );
        if result != 0 {
            return Err(std::io::Error::from_raw_os_error(result as i32).to_string());
        }
    }
    Ok(())
}

#[cfg(test)]
fn read_acl(path: &Path) -> Result<String, String> {
    use windows_sys::Win32::Security::Authorization::ConvertSidToStringSidW;
    use windows_sys::Win32::Security::{GetAce, ACCESS_ALLOWED_ACE};
    let path: Vec<u16> = path.as_os_str().encode_wide().chain(Some(0)).collect();
    unsafe {
        let mut acl = std::ptr::null_mut();
        let mut descriptor = std::ptr::null_mut();
        let result = GetNamedSecurityInfoW(
            path.as_ptr(),
            SE_FILE_OBJECT,
            DACL_SECURITY_INFORMATION,
            std::ptr::null_mut(),
            std::ptr::null_mut(),
            &mut acl,
            std::ptr::null_mut(),
            &mut descriptor,
        );
        let _descriptor = LocalMemory(descriptor);
        if result != 0 {
            return Err(result.to_string());
        }
        let mut output = String::new();
        for index in 0..(*acl).AceCount as u32 {
            let mut ace = std::ptr::null_mut();
            assert_ne!(GetAce(acl, index, &mut ace), 0);
            let ace = &*(ace as *const ACCESS_ALLOWED_ACE);
            if ace.Header.AceType != 0 {
                continue;
            }
            let mut text = std::ptr::null_mut();
            assert_ne!(
                ConvertSidToStringSidW(
                    std::ptr::addr_of!(ace.SidStart).cast_mut().cast(),
                    &mut text
                ),
                0
            );
            let _text = LocalMemory(text.cast());
            let mut length = 0;
            while *text.add(length) != 0 {
                length += 1;
            }
            output.push_str(&format!(
                "{}:{}:{}\n",
                String::from_utf16_lossy(std::slice::from_raw_parts(text, length)),
                ace.Mask,
                ace.Header.AceFlags
            ));
        }
        Ok(output)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        fs,
        time::{SystemTime, UNIX_EPOCH},
    };

    #[test]
    fn webview_read_permissions_are_idempotent_and_preserve_user_write_access() {
        let id = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!("kof-launcher-acl-{id}"));
        fs::create_dir_all(&root).unwrap();
        grant_webview_read_access(&root).unwrap();
        let first = read_acl(&root).unwrap();
        grant_webview_read_access(&root).unwrap();
        assert_eq!(first, read_acl(&root).unwrap());
        assert!(first.contains("S-1-15-2-1"));
        assert!(first.contains("S-1-15-2-2"));
        fs::write(root.join("owned.txt"), "user still writes").unwrap();
        fs::remove_file(root.join("owned.txt")).unwrap();
        fs::remove_dir(root).unwrap();
    }
}
