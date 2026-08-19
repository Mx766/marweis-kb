/** File extension → background color for card icons */
export const FILE_ICON_BG: Record<string, string> = {
  pdf: '#ef4444', doc: '#3b82f6', docx: '#3b82f6',
  xls: '#16a34a', xlsx: '#16a34a', ppt: '#f97316', pptx: '#f97316',
  link: '#0891b2', txt: '#6b7280', md: '#6b7280',
  jpg: '#a855f7', jpeg: '#a855f7', png: '#a855f7',
  zip: '#78716c', rar: '#78716c', '7z': '#78716c',
  mp4: '#8b5cf6', avi: '#8b5cf6',
}

/** File extension → tag/semantic type */
export const FILE_TAG_TYPE: Record<string, string> = {
  pdf: 'danger', doc: 'primary', docx: 'primary',
  xls: 'success', xlsx: 'success', ppt: 'warning', pptx: 'warning',
  link: 'info', mp4: '', avi: '', zip: '', rar: '', '7z': '',
}

export function getFileIconBg(ext?: string | null): string {
  return FILE_ICON_BG[ext?.toLowerCase() || ''] || '#6b7280'
}

export function getFileTagType(ext?: string | null): string {
  return FILE_TAG_TYPE[ext?.toLowerCase() || ''] || ''
}

/** Extension label fallback */
export function getFileExtLabel(ext?: string | null): string {
  return ext?.toUpperCase()?.substring(0, 4) || 'FILE'
}
