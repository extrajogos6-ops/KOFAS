#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod core;
mod directory;
mod keybindings;
mod process;
mod runtime;

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs;
use std::path::PathBuf;
use std::sync::{
    atomic::{AtomicBool, AtomicU64, Ordering},
    Arc, Mutex,
};
use std::time::{SystemTime, UNIX_EPOCH};
use tauri::{Emitter, Manager, State};

struct Installation {
    root: PathBuf,
    gate: Mutex<()>,
    stopping: AtomicBool,
    watched: Mutex<HashSet<(u32, u64)>>,
    revision: AtomicU64,
}

#[derive(Serialize, Deserialize)]
struct BootMarker {
    pid: u32,
    created: u64,
    started: u64,
}

#[derive(Clone, Serialize)]
struct Status {
    phase: &'static str,
    detail: Option<String>,
    revision: u64,
}

impl Installation {
    fn marker_path(&self) -> PathBuf {
        self.root
            .join("outputs/KOFAS-Local-Server/launcher-session.json")
    }

    fn booting(&self) -> Option<BootMarker> {
        let marker: BootMarker =
            serde_json::from_slice(&fs::read(self.marker_path()).ok()?).ok()?;
        let candidate = process::identity(marker.pid);
        let actual = candidate
            .as_ref()
            .map(|value| (value.pid, value.created, value.executable.as_path()));
        let expected = process::normalized(&self.root.join("python/pythonw.exe"));
        core::process_matches(marker.pid, marker.created, actual, &expected).then_some(marker)
    }

    fn status(&self) -> Result<Status, String> {
        core::launch_spec(&self.root)?;
        if self.stopping.load(Ordering::SeqCst) {
            return Ok(Status {
                phase: "stopping",
                detail: None,
                revision: 0,
            });
        }
        if process::find_game(&self.root.join("outputs/KOFAS-PC-Test/KOF ALLSTAR.exe")).is_some() {
            return Ok(Status {
                phase: "running",
                detail: None,
                revision: 0,
            });
        }
        if let Some(marker) = self.booting() {
            let elapsed = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map_err(|error| error.to_string())?
                .as_secs()
                .saturating_sub(marker.started);
            return Ok(Status { phase: "starting", detail: (elapsed > 45).then(|| "A inicialização está demorando. Confira launcher-error.log na pasta do servidor.".to_string()), revision: 0 });
        }
        Ok(Status {
            phase: "ready",
            detail: None,
            revision: 0,
        })
    }

    fn publish(self: &Arc<Self>, app: &tauri::AppHandle) -> Result<Status, String> {
        if let Some(game) =
            process::find_game(&self.root.join("outputs/KOFAS-PC-Test/KOF ALLSTAR.exe"))
        {
            self.watch(app, game, false)?;
        }
        if let Some(marker) = self.booting() {
            if let Some(bootstrap) = process::identity(marker.pid) {
                self.watch(app, bootstrap, true)?;
            }
        }
        let mut status = self.status()?;
        status.revision = self.revision.fetch_add(1, Ordering::SeqCst);
        app.emit("game-state-changed", &status)
            .map_err(|error| error.to_string())?;
        Ok(status)
    }

    fn reconcile(self: &Arc<Self>, app: &tauri::AppHandle) -> Result<Status, String> {
        let _guard = self
            .gate
            .lock()
            .map_err(|_| "Estado do launcher indisponível.")?;
        self.publish(app)
    }

    fn watch(
        self: &Arc<Self>,
        app: &tauri::AppHandle,
        identity: process::Identity,
        bootstrap: bool,
    ) -> Result<(), String> {
        let key = (identity.pid, identity.created);
        if !self
            .watched
            .lock()
            .map_err(|_| "Monitor de processo indisponível.")?
            .insert(key)
        {
            return Ok(());
        }
        let installation = self.clone();
        let app = app.clone();
        std::thread::spawn(move || {
            let result = (|| {
                if bootstrap && !process::wait_exit(&identity, 46000)? {
                    installation.reconcile(&app)?;
                }
                process::wait_exit(&identity, u32::MAX)?;
                Ok::<(), String>(())
            })();
            if let Ok(mut watched) = installation.watched.lock() {
                watched.remove(&key);
            }
            match result.and_then(|_| installation.reconcile(&app).map(|_| ())) {
                Ok(()) => {}
                Err(error) => {
                    let _ = app.emit("launcher-error", error);
                }
            }
        });
        Ok(())
    }
}

#[tauri::command]
async fn game_status(
    app: tauri::AppHandle,
    installation: State<'_, Arc<Installation>>,
) -> Result<Status, String> {
    let installation = installation.inner().clone();
    tauri::async_runtime::spawn_blocking(move || installation.reconcile(&app))
        .await
        .map_err(|error| error.to_string())?
}

#[tauri::command]
async fn play_game(
    app: tauri::AppHandle,
    installation: State<'_, Arc<Installation>>,
) -> Result<Status, String> {
    let installation = installation.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = installation
            .gate
            .lock()
            .map_err(|_| "Não foi possível iniciar o jogo.".to_string())?;
        let spec = core::launch_spec(&installation.root)?;
        let game = process::find_game(
            &installation
                .root
                .join("outputs/KOFAS-PC-Test/KOF ALLSTAR.exe"),
        );
        match core::start_action(game.is_some(), installation.booting().is_some()) {
            core::StartAction::Focus => {
                if let Some(game) = game {
                    process::focus(game.pid);
                }
            }
            core::StartAction::Wait => {}
            core::StartAction::Spawn => {
                let pending = installation.marker_path().with_extension("pending");
                fs::write(&pending, b"").map_err(|error| {
                    format!("Não foi possível gravar o estado do launcher: {error}")
                })?;
                process::spawn_registered(&spec, |identity| {
                    let marker = BootMarker {
                        pid: identity.pid,
                        created: identity.created,
                        started: SystemTime::now()
                            .duration_since(UNIX_EPOCH)
                            .map_err(|error| error.to_string())?
                            .as_secs(),
                    };
                    fs::write(
                        &pending,
                        serde_json::to_vec(&marker).map_err(|error| error.to_string())?,
                    )
                    .map_err(|error| error.to_string())?;
                    fs::rename(&pending, installation.marker_path())
                        .map_err(|error| error.to_string())
                })?;
            }
        }
        installation.publish(&app)
    })
    .await
    .map_err(|error| error.to_string())?
}

#[tauri::command]
async fn stop_game(
    app: tauri::AppHandle,
    installation: State<'_, Arc<Installation>>,
) -> Result<Status, String> {
    let installation = installation.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = installation
            .gate
            .lock()
            .map_err(|_| "Não foi possível fechar o jogo.".to_string())?;
        let game = process::find_game(
            &installation
                .root
                .join("outputs/KOFAS-PC-Test/KOF ALLSTAR.exe"),
        );
        let Some(game) = game else {
            return installation.publish(&app);
        };
        installation.stopping.store(true, Ordering::SeqCst);
        let _ = installation.publish(&app);
        let bootstrap = installation
            .booting()
            .and_then(|marker| process::identity(marker.pid));
        let result = process::stop_game(&game);
        if result.is_ok() {
            if let Some(bootstrap) = bootstrap {
                let _ = process::wait_exit(&bootstrap, 5000);
            }
        }
        installation.stopping.store(false, Ordering::SeqCst);
        let status = installation.publish(&app);
        result?;
        status
    })
    .await
    .map_err(|error| error.to_string())?
}

fn main() {
    let root = installation_root().expect("Não foi possível localizar a pasta do launcher");
    if let Some(runtime) = core::fixed_runtime(&root).expect("WebView2 portátil incompleto") {
        runtime::grant_webview_read_access(&runtime)
            .expect("Não foi possível preparar as permissões do WebView2 portátil");
        std::env::set_var("WEBVIEW2_BROWSER_EXECUTABLE_FOLDER", runtime);
    }
    std::env::set_var(
        "WEBVIEW2_USER_DATA_FOLDER",
        root.join("outputs/launcher-webview"),
    );
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .setup(move |app| {
            let installation = Arc::new(Installation {
                root,
                gate: Mutex::new(()),
                stopping: AtomicBool::new(false),
                watched: Mutex::new(HashSet::new()),
                revision: AtomicU64::new(0),
            });
            core::launch_spec(&installation.root)?;
            let (ready_tx, ready_rx) = std::sync::mpsc::sync_channel(1);
            let monitor = installation.clone();
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                let mut watcher = match directory::DirectoryWatcher::open(
                    &monitor.root.join("outputs/KOFAS-Local-Server"),
                ) {
                    Ok(watcher) => {
                        let _ = ready_tx.send(Ok::<(), String>(()));
                        watcher
                    }
                    Err(error) => {
                        let _ = ready_tx.send(Err(error));
                        return;
                    }
                };
                loop {
                    match watcher.next() {
                        Ok(false) => {}
                        Ok(true) => {
                            if let Err(error) = monitor.reconcile(&handle) {
                                let _ = handle.emit("launcher-error", error);
                            }
                        }
                        Err(error) => {
                            let _ = handle.emit("launcher-error", error);
                            break;
                        }
                    }
                }
            });
            ready_rx.recv()??;
            installation.reconcile(app.handle())?;
            app.manage(installation);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            game_status,
            play_game,
            stop_game,
            get_keybindings,
            save_keybindings
        ])
        .run(tauri::generate_context!())
        .expect("Não foi possível abrir o launcher");
}

#[tauri::command]
async fn get_keybindings(
    installation: State<'_, Arc<Installation>>,
) -> Result<keybindings::KeyConfig, String> {
    let installation = installation.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = installation
            .gate
            .lock()
            .map_err(|_| "Configurações indisponíveis.")?;
        keybindings::load(&installation.root)
    })
    .await
    .map_err(|error| error.to_string())?
}

#[tauri::command]
async fn save_keybindings(
    config: keybindings::KeyConfig,
    installation: State<'_, Arc<Installation>>,
) -> Result<keybindings::KeyConfig, String> {
    let installation = installation.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = installation
            .gate
            .lock()
            .map_err(|_| "Configurações indisponíveis.")?;
        keybindings::save(&installation.root, &config)?;
        Ok(config)
    })
    .await
    .map_err(|error| error.to_string())?
}

fn installation_root() -> Result<PathBuf, String> {
    let executable = std::env::current_exe().map_err(|error| error.to_string())?;
    let mut root = executable
        .parent()
        .ok_or("Launcher sem diretório de instalação.")?
        .to_path_buf();
    if cfg!(debug_assertions) && core::launch_spec(&root).is_err() {
        root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .and_then(|value| value.parent())
            .ok_or("Diretório de desenvolvimento inválido.")?
            .to_path_buf();
    }
    Ok(process::normalized(&root))
}
