#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

#[cfg(any(target_os = "windows", target_os = "macos"))]
use tauri::Manager;

/// Aspetta che il backend risponda sulla porta 8000.
fn wait_for_backend(attempts: u32) {
    for _ in 0..attempts {
        if TcpStream::connect("127.0.0.1:8000").is_ok() {
            return;
        }
        thread::sleep(Duration::from_millis(300));
    }
}

/// Avvia il backend FastAPI. La strategia dipende dalla piattaforma:
/// - Windows: esegue il backend impacchettato (`drops-backend.exe`) dalle risorse
///   dell'app, passando la cartella di ffmpeg via DROPS_FFMPEG_DIR.
/// - macOS: backend Mach-O impacchettato nell'.app se presente, altrimenti
///   fallback al venv Python del progetto (modalità sviluppo).
#[allow(unused_variables)]
fn spawn_backend(app: &tauri::App) -> Option<Child> {
    #[cfg(target_os = "windows")]
    {
        let res = match app.path().resource_dir() {
            Ok(p) => p,
            Err(e) => {
                eprintln!("❌ resource_dir non risolvibile: {e}");
                return None;
            }
        };
        let backend = res.join("drops-backend.exe");
        let ffmpeg_dir = res.join("ffmpeg");
        match Command::new(&backend)
            .env("DROPS_FFMPEG_DIR", &ffmpeg_dir)
            .env("DROPS_PARENT_PID", std::process::id().to_string())
            .env("DROPS_APP_VERSION", env!("CARGO_PKG_VERSION"))
            .current_dir(&res)
            .spawn()
        {
            Ok(child) => Some(child),
            Err(e) => {
                eprintln!("❌ Impossibile avviare drops-backend.exe: {e}");
                None
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        // 1) App impacchettata (.dmg): backend Mach-O dentro le risorse dell'.app
        if let Ok(res) = app.path().resource_dir() {
            let backend = res.join("drops-backend");
            if backend.exists() {
                let ffmpeg_dir = res.join("ffmpeg");
                // Le risorse impacchettate possono perdere il bit di esecuzione:
                // lo riforziamo prima di lanciarle.
                {
                    use std::os::unix::fs::PermissionsExt;
                    let _ =
                        std::fs::set_permissions(&backend, std::fs::Permissions::from_mode(0o755));
                    let _ = std::fs::set_permissions(
                        ffmpeg_dir.join("ffmpeg"),
                        std::fs::Permissions::from_mode(0o755),
                    );
                }
                return Command::new(&backend)
                    .env("DROPS_FFMPEG_DIR", &ffmpeg_dir)
                    .env("DROPS_PARENT_PID", std::process::id().to_string())
                    .env("DROPS_APP_VERSION", env!("CARGO_PKG_VERSION"))
                    .current_dir(&res)
                    .spawn()
                    .ok();
            }
        }

        // 2) Sviluppo (launch-desktop.sh): venv Python del progetto (comportamento storico)
        let home = std::env::var("HOME").ok()?;
        let project_dir =
            std::path::PathBuf::from(&home).join("Documents/Claude/Projects/mp3-downloader");
        let python = project_dir.join(".venv/bin/python3.11");
        let backend_dir = project_dir.join("backend");
        Command::new(&python)
            .env("DROPS_PARENT_PID", std::process::id().to_string())
            .env("DROPS_APP_VERSION", env!("CARGO_PKG_VERSION"))
            .args([
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ])
            .current_dir(&backend_dir)
            .spawn()
            .ok()
    }

    #[cfg(not(any(target_os = "windows", target_os = "macos")))]
    {
        None
    }
}

fn main() {
    let backend: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(None));
    let backend_for_exit = backend.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .setup(move |app| {
            let child = spawn_backend(app);
            if child.is_some() {
                // Attende che uvicorn sia pronto prima di caricare la WebView
                // PyInstaller onefile può impiegare 15-20 secondi al primo avvio.
                wait_for_backend(120);
            }
            *backend.lock().unwrap() = child;

            tauri::WebviewWindowBuilder::new(
                app,
                "main",
                tauri::WebviewUrl::External("http://127.0.0.1:8000".parse().unwrap()),
            )
            .title("Drops")
            .inner_size(560.0, 760.0)
            .resizable(false)
            .center()
            .build()?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Errore nell'avvio di Drops")
        .run(move |_app_handle, event| {
            // Killa il backend alla chiusura dell'app
            if let tauri::RunEvent::Exit = event {
                if let Some(mut child) = backend_for_exit.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}
