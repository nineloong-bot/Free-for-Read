import { useState, useCallback, type DragEvent } from 'react'
import { Upload } from 'lucide-react'

export function DropZone({ onFile, accept = '.pdf,.docx,.pptx,.html,.epub,.fb2' }: { onFile: (f: File) => void; accept?: string }) {
  const [dragover, setDragover] = useState(false)
  const handleDrop = useCallback((e: DragEvent) => { e.preventDefault(); setDragover(false); const f = e.dataTransfer.files?.[0]; if (f) onFile(f) }, [onFile])

  return (
    <div
      className={`border-2 border-dashed rounded-[10px] p-8 text-center cursor-pointer transition-colors ${dragover ? 'border-[#d4641a] bg-[#fef7f0]' : 'border-[#e0d4c0]'}`}
      onDragOver={e => { e.preventDefault(); setDragover(true) }}
      onDragLeave={() => setDragover(false)}
      onDrop={handleDrop}
      onClick={() => { const i = document.createElement('input'); i.type = 'file'; i.accept = accept; i.onchange = e => { const f = (e.target as HTMLInputElement).files?.[0]; if (f) onFile(f) }; i.click() }}
      data-testid="dropzone"
    >
      <Upload size={28} strokeWidth={1.5} color="#c4b49a" className="mx-auto mb-2" />
      <p className="text-[13px] text-[#b8a48e] mb-0.5">拖放文件到此处</p>
      <p className="text-[11px] text-[#d0c4b0]">或点击选择文件</p>
      <p className="text-[10px] text-[#d8ccc0] mt-2">支持 PDF · Word · PPT · HTML · EPUB · FB2</p>
    </div>
  )
}
