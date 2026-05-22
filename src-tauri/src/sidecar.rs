use std::io::BufRead;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BackendReady {
    pub port: u16,
    pub shutdown_token: String,
}

pub struct BackendProcess {
    child: Mutex<Option<Child>>,
}

impl BackendProcess {
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
        }
    }

    pub fn spawn(&self) -> Result<BackendReady, String> {
        let mut child = Command::new(resolve_sidecar_command())
            .args(["serve", "--port", "0"])
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .map_err(|e| format!("Failed to spawn sidecar: {e}"))?;

        let stdout = child.stdout.take().ok_or("No stdout from sidecar")?;
        let reader = std::io::BufReader::new(stdout);
        let mut ready: Option<BackendReady> = None;

        for line in reader.lines() {
            let line = line.map_err(|e| format!("Read error: {e}"))?;
            println!("[sidecar] {line}");
            if let Some(parsed) = parse_ready_line(&line) {
                ready = Some(parsed);
                break;
            }
        }

        let ready = ready.ok_or("Sidecar did not print READY line")?;
        *self.child.lock().unwrap_or_else(|e| e.into_inner()) = Some(child);
        Ok(ready)
    }

    pub fn shutdown(&self) {
        if let Some(mut child) = self.child.lock().unwrap_or_else(|e| e.into_inner()).take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

impl Drop for BackendProcess {
    fn drop(&mut self) {
        self.shutdown();
    }
}

pub fn parse_ready_line(line: &str) -> Option<BackendReady> {
    let mut parts = line.split_whitespace();
    if parts.next()? != "READY" {
        return None;
    }
    let url = parts.next()?;
    let token_part = parts.find(|part| part.starts_with("shutdown_token="))?;
    let port = url.rsplit(':').next()?.parse::<u16>().ok()?;
    let shutdown_token = token_part.strip_prefix("shutdown_token=")?.to_string();
    if shutdown_token.is_empty() {
        return None;
    }
    Some(BackendReady {
        port,
        shutdown_token,
    })
}

fn resolve_sidecar_command() -> PathBuf {
    if let Ok(path) = std::env::var("FREE_FOR_READ_BACKEND") {
        return PathBuf::from(path);
    }

    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            if let Some(path) = find_sidecar_in(dir) {
                return path;
            }
            if let Some(resources) = dir.parent().map(|parent| parent.join("Resources")) {
                if let Some(path) = find_sidecar_in(&resources) {
                    return path;
                }
            }
        }
    }

    PathBuf::from("free-for-read")
}

fn find_sidecar_in(dir: &std::path::Path) -> Option<PathBuf> {
    let exact = dir.join("free-for-read-backend");
    if exact.is_file() {
        return Some(exact);
    }

    let entries = std::fs::read_dir(dir).ok()?;
    for entry in entries.flatten() {
        let path = entry.path();
        let name = path.file_name()?.to_string_lossy();
        if path.is_file() && name.starts_with("free-for-read-backend") {
            return Some(path);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::parse_ready_line;

    #[test]
    fn parse_ready_line_reads_port_and_shutdown_token() {
        let ready =
            parse_ready_line("READY http://127.0.0.1:49152 shutdown_token=abc123").unwrap();

        assert_eq!(ready.port, 49152);
        assert_eq!(ready.shutdown_token, "abc123");
    }

    #[test]
    fn parse_ready_line_rejects_missing_token() {
        assert!(parse_ready_line("READY http://127.0.0.1:49152").is_none());
    }
}
