fn main() {
    ensure_dev_sidecar_placeholder();
    tauri_build::build()
}

fn ensure_dev_sidecar_placeholder() {
    let target = match std::env::var("TAURI_ENV_TARGET_TRIPLE")
        .or_else(|_| std::env::var("TARGET"))
    {
        Ok(target) => target,
        Err(_) => return,
    };
    let suffix = if target.contains("windows") { ".exe" } else { "" };
    let path =
        std::path::Path::new("binaries").join(format!("free-for-read-backend-{target}{suffix}"));
    if path.exists() {
        return;
    }
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;

        if std::fs::write(&path, "#!/bin/sh\nexit 1\n").is_ok() {
            let _ = std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755));
        }
    }
    #[cfg(not(unix))]
    {
        let _ = std::fs::write(&path, "");
    }
}
