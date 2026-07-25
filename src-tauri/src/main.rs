#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

#[cfg(target_os = "windows")]
use tauri::Manager;

/// Aspetta che il backend risponda sulla porta 8000 (max ~18s).
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
/// - macOS: comportamento storico (venv Python del progetto in ~/Documents/...).
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
        let home = std::env::var("HOME").ok()?;
        let project_dir =
            std::path::PathBuf::from(&home).join("Documents/Claude/Projects/mp3-downloader");
        let python = project_dir.join(".venv/bin/python3.11");
        let backend_dir = project_dir.join("backend");
        Command::new(&python)
            .args([
                "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000",
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
        .setup(move |app| {
            let child = spawn_backend(app);
            if child.is_some() {
                // Attende che uvicorn sia pronto prima di caricare la WebView
                wait_for_backend(60);
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
