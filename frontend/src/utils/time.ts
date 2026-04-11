export function formatDistanceToNow(ts: number): string {
  const diff = Date.now() - ts
  if (diff < 60000) return 'только что'
  if (diff < 3600000) return `${Math.floor(diff/60000)} мин назад`
  if (diff < 86400000) return `${Math.floor(diff/3600000)} ч назад`
  return new Date(ts).toLocaleDateString('ru')
}
