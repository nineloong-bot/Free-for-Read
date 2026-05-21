// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod sidecar;

use std::sync::Arc;
use sidecar::BackendProcess;

struct BackendState {
    port: u16,
    process: Arc<BackendProcess>,
}

fn main() {
    let process = BackendProcess::new();

    let port = match process.spawn() {
        Ok(p) => p,
        Err(e) => {
            eprintln!("Failed to start backend: {e}");
            std::process::exit(1);
        }
    };

    let process = Arc::new(process);
    let process_for_shutdown = Arc::clone(&process);

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(BackendState { port, process })
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .on_window_event(move |_window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let _ = ureq::post(&format!("http://127.0.0.1:{port}/shutdown"))
                    .send_empty();
                std::thread::sleep(std::time::Duration::from_secs(2));
                process_for_shutdown.shutdown();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn get_backend_port(state: tauri::State<BackendState>) -> u16 {
    state.port
}
