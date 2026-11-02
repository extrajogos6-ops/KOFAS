use std::path::{Path, PathBuf};

#[derive(Debug, PartialEq)]
pub struct LaunchSpec {
    pub executable: PathBuf,
    pub bootstrap: PathBuf,
    pub directory: PathBuf,
}

#[derive(Debug, PartialEq)]
pub enum StartAction {
    Focus,
    Wait,
    Spawn,
}

pub fn start_action(game_running: bool, bootstrap_running: bool) -> StartAction {
    if game_running {
        StartAction::Focus
    } else if bootstrap_running {
        StartAction::Wait
    } else {
        StartAction::Spawn
    }
}

pub fn process_matches(
    pid: u32,
    created: u64,
    current: Option<(u32, u64, &Path)>,
    expected: &Path,
) -> bool {
    current.is_some_and(|(current_pid, current_created, path)| {
        pid == current_pid && created == current_created && path == expected
    })
}

pub fn launch_spec(root: &Path) -> Result<LaunchSpec, String> {
    let spec = LaunchSpec {
        executable: root.join("python/pythonw.exe"),
        bootstrap: root.join("outputs/KOFAS-Local-Server/launch.pyw"),
        directory: root.to_path_buf(),
    };
    for path in [
        &spec.executable,
        &spec.bootstrap,
        &root.join("outputs/KOFAS-PC-Test/KOF ALLSTAR.exe"),
    ] {
        if !path.is_file() {
            return Err(format!(
                "Arquivo necessário não encontrado: {}",
                path.display()
            ));
        }
    }
    Ok(spec)
}

pub fn fixed_runtime(root: &Path) -> Result<Option<PathBuf>, String> {
    let runtime = root.join("runtime/webview2");
    if !runtime.exists() {
        return Ok(None);
    }
    if !runtime.join("msedgewebview2.exe").is_file() || !runtime.join("msedge.dll").is_file() {
        return Err(
            "O runtime/webview2 está incompleto. Extraia novamente o pacote inteiro.".to_string(),
        );
    }
    Ok(Some(runtime))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn bundled_runtime_follows_the_installation_and_rejects_partial_copies() {
        let root = installation();
        assert_eq!(fixed_runtime(&root).unwrap(), None);
        let runtime = root.join("runtime/webview2");
        fs::create_dir_all(&runtime).unwrap();
        assert!(fixed_runtime(&root).is_err());
        fs::write(runtime.join("msedgewebview2.exe"), b"fixture").unwrap();
        fs::write(runtime.join("msedge.dll"), b"fixture").unwrap();
        assert_eq!(fixed_runtime(&root).unwrap(), Some(runtime));
        fs::remove_dir_all(root).unwrap();
    }

    fn installation() -> PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!("kof launcher teste ç {unique}"));
        for file in [
            "python/pythonw.exe",
            "outputs/KOFAS-Local-Server/launch.pyw",
            "outputs/KOFAS-PC-Test/KOF ALLSTAR.exe",
        ] {
            let path = root.join(file);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(path, b"fixture").unwrap();
        }
        root
    }

    #[test]
    fn fixed_python_bootstrap_preserves_spaces_and_unicode() {
        let root = installation();
        let spec = launch_spec(&root).unwrap();
        assert_eq!(spec.executable, root.join("python/pythonw.exe"));
        assert_eq!(
            spec.bootstrap,
            root.join("outputs/KOFAS-Local-Server/launch.pyw")
        );
        assert_eq!(spec.directory, root);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn absent_python_does_not_produce_a_launch_command() {
        let root = installation();
        fs::remove_file(root.join("python/pythonw.exe")).unwrap();
        assert!(launch_spec(&root).is_err());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn absent_bootstrap_does_not_produce_a_launch_command() {
        let root = installation();
        fs::remove_file(root.join("outputs/KOFAS-Local-Server/launch.pyw")).unwrap();
        assert!(launch_spec(&root).is_err());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn absent_game_does_not_produce_a_launch_command() {
        let root = installation();
        fs::remove_file(root.join("outputs/KOFAS-PC-Test/KOF ALLSTAR.exe")).unwrap();
        assert!(launch_spec(&root).is_err());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn directories_cannot_impersonate_executables() {
        let root = installation();
        fs::remove_file(root.join("python/pythonw.exe")).unwrap();
        fs::create_dir(root.join("python/pythonw.exe")).unwrap();
        assert!(launch_spec(&root).is_err());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn play_focuses_an_existing_game_without_spawning() {
        assert_eq!(start_action(true, false), StartAction::Focus);
        assert_eq!(start_action(true, true), StartAction::Focus);
    }

    #[test]
    fn repeated_play_waits_for_the_existing_bootstrap() {
        assert_eq!(start_action(false, true), StartAction::Wait);
        assert_eq!(start_action(false, false), StartAction::Spawn);
    }

    #[test]
    fn reused_pid_and_other_installations_do_not_block_launch() {
        let expected = Path::new("C:/KOF/python/pythonw.exe");
        assert!(process_matches(
            42,
            100,
            Some((42, 100, expected)),
            expected
        ));
        assert!(!process_matches(
            42,
            100,
            Some((42, 200, expected)),
            expected
        ));
        assert!(!process_matches(
            42,
            100,
            Some((43, 100, expected)),
            expected
        ));
        assert!(!process_matches(
            42,
            100,
            Some((42, 100, Path::new("C:/Other/pythonw.exe"))),
            expected
        ));
        assert!(!process_matches(42, 100, None, expected));
    }
}
