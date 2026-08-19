// 示例组织架构（2026-08-04 按最新员工名单调整）
export const DEPARTMENTS = [
  '总经办',
  '人力资源部',
  '财务部',
  '市场部',
  '注册部',
  '医学部部',
  '临床运营部',
  '临床研究部',
  '质量部',
  '商务部',
  '国际部',
  '公共共享区',
]

export const DEPT_META: Record<string, { icon: string; color: string }> = {
  '总经办': { icon: 'E', color: '#1e40af' },
  '人力资源部': { icon: 'H', color: '#d97706' },
  '财务部': { icon: 'F', color: '#65a30d' },
  '市场部': { icon: 'M', color: '#ec4899' },
  '注册部': { icon: 'R', color: '#1e50ae' },
  '医学部部': { icon: 'Y', color: '#2e86c1' },
  '临床运营部': { icon: 'S', color: '#0891b2' },
  '临床研究部': { icon: 'C', color: '#059669' },
  '质量部': { icon: 'Q', color: '#a855f7' },
  '商务部': { icon: 'B', color: '#2563eb' },
  '国际部': { icon: 'K', color: '#e11d48' },
  '公共共享区': { icon: 'S', color: '#6366f1' },
}
