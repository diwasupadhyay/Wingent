use std::io::{self, Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

#[cfg(windows)]
use std::os::windows::process::CommandExt;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Emitter, LogicalSize, Manager, WindowEvent};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, ShortcutState};

const COLLAPSED_HEIGHT: f64 = 92.0;
const EXPANDED_HEIGHT: f64 = 300.0;
const REQUIRED_BACKEND_RUNTIME: &str = "operator-v5";

#[derive(Clone, Copy, PartialEq, Eq)]
enum BackendHealth {
  Ready,
  Incompatible,
  Unavailable,
}

impl BackendHealth {
  fn as_str(self) -> &'static str {
    match self {
      Self::Ready => "ready",
      Self::Incompatible => "incompatible",
      Self::Unavailable => "unavailable",
    }
  }
}

struct BackendProcess(Mutex<Option<Child>>);

impl BackendProcess {
  fn stop(&self) {
    if let Ok(mut child_slot) = self.0.lock() {
      if let Some(mut child) = child_slot.take() {
        if child.try_wait().ok().flatten().is_none() {
          #[cfg(windows)]
          {
            let _ = Command::new("taskkill")
              .args(["/PID", &child.id().to_string(), "/T", "/F"])
              .stdin(Stdio::null())
              .stdout(Stdio::null())
              .stderr(Stdio::null())
              .creation_flags(0x08000000)
              .status();
            let _ = child.kill();
          }
          #[cfg(not(windows))]
          let _ = child.kill();
        }
        let _ = child.wait();
      }
    }
  }
}

impl Drop for BackendProcess {
  fn drop(&mut self) {
    self.stop();
  }
}

fn classify_backend_response(response: &str) -> BackendHealth {
  if !response.starts_with("HTTP/1.1 200") {
    return BackendHealth::Incompatible;
  }
  let Some((_, body)) = response.split_once("\r\n\r\n") else {
    return BackendHealth::Incompatible;
  };
  let Ok(value) = serde_json::from_str::<serde_json::Value>(body) else {
    return BackendHealth::Incompatible;
  };
  if value.get("service").and_then(|item| item.as_str()) == Some("wingent")
    && value.get("runtime").and_then(|item| item.as_str()) == Some(REQUIRED_BACKEND_RUNTIME)
  {
    BackendHealth::Ready
  } else {
    BackendHealth::Incompatible
  }
}

fn backend_health() -> BackendHealth {
  let address = SocketAddr::from(([127, 0, 0, 1], 8000));
  let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(300)) else {
    return BackendHealth::Unavailable;
  };
  let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
  let _ = stream.set_write_timeout(Some(Duration::from_millis(500)));
  if stream
    .write_all(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
    .is_err()
  {
    return BackendHealth::Incompatible;
  }
  let mut response = Vec::with_capacity(512);
  let mut buffer = [0u8; 512];
  while response.len() < 2048 {
    match stream.read(&mut buffer) {
      Ok(0) => break,
      Ok(count) => response.extend_from_slice(&buffer[..count]),
      Err(_) => break,
    }
  }
  let response = String::from_utf8_lossy(&response);
  classify_backend_response(&response)
}

#[tauri::command]
fn backend_status() -> &'static str {
  backend_health().as_str()
}

fn start_backend_sidecar() -> Result<Child, String> {
  let mut candidates = Vec::new();
  if let Ok(current_exe) = std::env::current_exe() {
    if let Some(directory) = current_exe.parent() {
      candidates.push(directory.join("wingent-backend.exe"));
    }
  }
  candidates.push(
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
      .join("binaries")
      .join("wingent-backend-x86_64-pc-windows-msvc.exe"),
  );

  let mut last_error: Option<io::Error> = None;
  for executable in candidates {
    let mut command = Command::new(executable);
    command
      .stdin(Stdio::null())
      .stdout(Stdio::null())
      .stderr(Stdio::null());
    #[cfg(windows)]
    command.creation_flags(0x08000000);
    match command.spawn() {
      Ok(child) => return Ok(child),
      Err(error) => last_error = Some(error),
    }
  }

  Err(format!(
    "Packaged backend could not be started: {}",
    last_error.map(|error| error.to_string()).unwrap_or_default()
  ))
}

fn show_overlay(app: &AppHandle) {
  if let Some(window) = app.get_webview_window("main") {
    let _ = window.show();
    let _ = window.center();
    let _ = window.set_focus();
    let _ = app.emit("wingent://focus", ());
  }
}

fn toggle_overlay(app: &AppHandle) {
  if let Some(window) = app.get_webview_window("main") {
    if window.is_visible().unwrap_or(false) {
      let _ = window.hide();
    } else {
      show_overlay(app);
    }
  }
}

fn ollama_is_running() -> bool {
  let address = SocketAddr::from(([127, 0, 0, 1], 11434));
  TcpStream::connect_timeout(&address, Duration::from_millis(300)).is_ok()
}

#[tauri::command]
fn ollama_status() -> bool {
  ollama_is_running()
}

#[tauri::command]
fn start_ollama() -> Result<(), String> {
  if ollama_is_running() {
    return Ok(());
  }

  let mut candidates = vec![PathBuf::from("ollama")];
  if let Some(local_app_data) = std::env::var_os("LOCALAPPDATA") {
    candidates.push(PathBuf::from(local_app_data).join("Programs").join("Ollama").join("ollama.exe"));
  }

  let mut last_error: Option<io::Error> = None;
  for executable in candidates {
    let mut command = Command::new(executable);
    command
      .arg("serve")
      .stdin(Stdio::null())
      .stdout(Stdio::null())
      .stderr(Stdio::null());
    #[cfg(windows)]
    command.creation_flags(0x08000000);

    match command.spawn() {
      Ok(_) => return Ok(()),
      Err(error) => last_error = Some(error),
    }
  }

  Err(format!(
    "Could not start Ollama. Install it or add ollama.exe to PATH. {}",
    last_error.map(|error| error.to_string()).unwrap_or_default()
  ))
}

#[tauri::command]
fn hide_overlay(app: AppHandle) {
  if let Some(window) = app.get_webview_window("main") {
    let _ = window.hide();
  }
}

#[tauri::command]
fn set_overlay_expanded(app: AppHandle, expanded: bool) {
  if let Some(window) = app.get_webview_window("main") {
    let height = if expanded { EXPANDED_HEIGHT } else { COLLAPSED_HEIGHT };
    let _ = window.set_size(LogicalSize::new(760.0, height));
    let _ = window.center();
  }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_global_shortcut::Builder::new().build())
    .invoke_handler(tauri::generate_handler![
      backend_status,
      ollama_status,
      start_ollama,
      hide_overlay,
      set_overlay_expanded
    ])
    .setup(|app| {
      let backend_child = match backend_health() {
        BackendHealth::Ready => None,
        BackendHealth::Incompatible => {
          log::error!("Another service or an outdated Wingent backend occupies 127.0.0.1:8000; refusing to use it.");
          None
        }
        BackendHealth::Unavailable => match start_backend_sidecar() {
          Ok(child) => Some(child),
          Err(error) => {
            log::error!("{error}");
            None
          }
        },
      };
      app.manage(BackendProcess(Mutex::new(backend_child)));

      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      let open_item = MenuItem::with_id(app, "open", "Open Wingent", true, None::<&str>)?;
      let quit_item = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
      let menu = Menu::with_items(app, &[&open_item, &quit_item])?;
      TrayIconBuilder::new()
        .icon(app.default_window_icon().expect("Wingent icon missing").clone())
        .tooltip("Wingent · Ctrl+Space")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
          "open" => show_overlay(app),
          "quit" => {
            app.state::<BackendProcess>().stop();
            app.exit(0);
          }
          _ => {}
        })
        .on_tray_icon_event(|tray, event| {
          if let TrayIconEvent::Click {
            button: MouseButton::Left,
            button_state: MouseButtonState::Up,
            ..
          } = event {
            toggle_overlay(tray.app_handle());
          }
        })
        .build(app)?;

      app.global_shortcut().on_shortcut("Ctrl+Space", |app_handle, _, event| {
        if event.state == ShortcutState::Pressed {
          toggle_overlay(app_handle);
        }
      })?;

      if let Some(window) = app.get_webview_window("main") {
        let window_handle = window.clone();
        window.on_window_event(move |event| {
          if let WindowEvent::CloseRequested { api, .. } = event {
            api.prevent_close();
            let _ = window_handle.hide();
          }
        });
      }

      Ok(())
    })
    .build(tauri::generate_context!())
    .expect("error while building Tauri application")
    .run(|app, event| {
      if matches!(event, tauri::RunEvent::Exit) {
        app.state::<BackendProcess>().stop();
      }
    });
}

#[cfg(test)]
mod tests {
  use super::{classify_backend_response, BackendHealth};

  #[test]
  fn refuses_stale_or_unrelated_loopback_backend() {
    let current = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"service\":\"wingent\",\"runtime\":\"operator-v5\"}";
    let stale = current.replace("operator-v5", "operator-v4");
    let unrelated = current.replace("wingent", "another-service");
    assert!(matches!(classify_backend_response(current), BackendHealth::Ready));
    assert!(matches!(classify_backend_response(&stale), BackendHealth::Incompatible));
    assert!(matches!(classify_backend_response(&unrelated), BackendHealth::Incompatible));
  }
}
