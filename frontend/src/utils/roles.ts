/** Canonical role display labels */
export const ROLE_LABELS: Record<string, string> = {
  super_admin: '超级管理员',
  dept_admin: '部门管理员',
  editor: '编辑者',
  employee: '员工',
  guest: '访客',
}

/** Short role labels for badge/tag display */
export const ROLE_SHORT_LABELS: Record<string, string> = {
  super_admin: '超管',
  dept_admin: '部门管理员',
  editor: '编辑者',
  employee: '员工',
  guest: '访客',
}

export function getRoleLabel(role?: string | null): string {
  return ROLE_LABELS[role || ''] || role || '未知'
}

export function getRoleShortLabel(role?: string | null): string {
  return ROLE_SHORT_LABELS[role || ''] || role || '未知'
}
