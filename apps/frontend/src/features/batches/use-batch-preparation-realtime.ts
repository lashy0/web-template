import { useEffect } from 'react'

type RealtimeEvent = Readonly<{
  data: Readonly<{ batch_id?: string }>
  type: string
}>

function eventsUrl(): string {
  if (import.meta.env.DEV) return '/realtime/events'

  const hostname = window.location.hostname
  const baseDomain = hostname.startsWith('app.') ? hostname.slice(4) : hostname
  return `${window.location.protocol}//realtime.${baseDomain}/events`
}

export function useBatchPreparationRealtime(batchId: string, onPreparationUpdated: () => void) {
  useEffect(() => {
    const source = new EventSource(eventsUrl())
    source.onmessage = (message) => {
      let event: RealtimeEvent
      try {
        event = JSON.parse(message.data) as RealtimeEvent
      } catch {
        return
      }

      if (event.type === 'batch.preparation_updated' && event.data.batch_id === batchId) {
        onPreparationUpdated()
      }
    }
    return () => source.close()
  }, [batchId, onPreparationUpdated])
}
