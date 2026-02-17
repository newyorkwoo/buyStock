export async function requestNotificationPermission() {
  if (!('Notification' in window)) {
    return { ok: false, message: '此裝置瀏覽器不支援通知 API' }
  }

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    return { ok: false, message: '通知權限未允許' }
  }

  return { ok: true, message: '已啟用通知' }
}

export function notifySignal(result) {
  if (!('Notification' in window)) return
  if (Notification.permission !== 'granted') return

  const title = `買進提醒：${result.signal}`
  const body = `NASDAQ ${result.nasdaqPrice.toFixed(2)} (${result.nasdaqChange.toFixed(2)}%), VIX ${result.vixValue.toFixed(2)}`
  new Notification(title, { body })
}