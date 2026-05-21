use std::io::BufRead;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

pub struct BackendProcess {
    child: Mutex<Option<Child>>,
}

impl BackendProcess {
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
        }
    }

    pub fn spawn(&self) -> Result<u16, String> {
        let mut child = Command::new("free-for-read")
            .args(["serve", "--port", "0"])
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .map_err(|e| format!("Failed to spawn sidecar: {e}"))?;

        let stdout = child.stdout.take().ok_or("No stdout from sidecar")?;
        let reader = std::io::BufReader::new(stdout);
        let mut port: Option<u16> = None;

        for line in reader.lines() {
            let line = line.map_err(|e| format!("Read error: {e}"))?;
            println!("[sidecar] {line}");
            if line.starts_with("READY http://127.0.0.1:") {
                port = line.rsplit(':').next().and_then(|p| p.parse::<u16>().ok());
                break;
            }
        }

        let port = port.ok_or("Sidecar did not print READY line")?;
        *self.child.lock().unwrap_or_else(|e| e.into_inner()) = Some(child);
        Ok(port)
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
