export async function openFileDialog(accept: string): Promise<File | null> {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const path = await open({
      filters: [{ name: 'Books', extensions: accept.split(',').map(e => e.replace('.', '')) }],
      multiple: false,
    })
    if (!path || typeof path !== 'string') return null
    const { readFile } = await import('@tauri-apps/plugin-fs')
    const data = await readFile(path)
    const name = path.replace(/^.*[/\\]/, '') || 'unknown'
    return new File([data], name)
  } catch (e) {
    console.error('openFileDialog failed:', e)
    return null
  }
}
