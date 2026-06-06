import { ref, computed } from 'vue'

export interface StudyParameterEntry {
    source: string;
    params: any;
    metrics: any;
    elapsedSeconds: number;
    timestamp: string;
}

const sessionActive = ref(false)
const sessionStartTime = ref<number | null>(null)
const parameterLog = ref<StudyParameterEntry[]>([])
const bestAri = ref<number>(-1)
const bestAriParams = ref<any>(null)
const bestAriTime = ref<number>(0)

export function useStudySession() {
    const startSession = () => {
        sessionActive.value = true
        sessionStartTime.value = Date.now()
        parameterLog.value = []
        bestAri.value = -1
        bestAriParams.value = null
        bestAriTime.value = 0
        console.log('[StudySession] Started new study session')
    }

    const logParameterSet = async (source: string, params: any, metrics: any) => {
        // Auto-start session if not active yet (e.g. user navigated directly to clustering)
        if (!sessionActive.value || !sessionStartTime.value) {
            startSession()
        }

        const elapsedSeconds = Math.floor((Date.now() - sessionStartTime.value) / 1000)

        // Check for best ARI (only log to console)
        const currentAri = metrics?.ari || -1
        if (currentAri > bestAri.value) {
            bestAri.value = currentAri
            bestAriParams.value = params
            bestAriTime.value = elapsedSeconds
            console.log(`[StudySession] New best ARI achieved: ${currentAri.toFixed(3)} (Elapsed: ${elapsedSeconds}s, Params: ${JSON.stringify(params)})`)
        }

        const entry: StudyParameterEntry = {
            source,
            params,
            metrics,
            elapsedSeconds,
            timestamp: new Date().toISOString()
        }

        parameterLog.value.push(entry)

        // Attempt to persist to Redis via API
        try {
            await fetch('/api/study-session/current/log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(entry)
            })
        } catch (e) {
            console.warn('[StudySession] Failed to persist log entry to Redis', e)
        }
    }

    const loadSessionHistory = async (sessionId: string = 'current') => {
        try {
            const response = await fetch(`/api/study-session/${sessionId}`)
            if (response.ok) {
                const entries = await response.json()
                if (Array.isArray(entries) && entries.length > 0) {
                    // Merge with existing entries, avoiding duplicates by timestamp
                    const existingTimestamps = new Set(parameterLog.value.map(e => e.timestamp))
                    const newEntries = entries.filter((e: StudyParameterEntry) => !existingTimestamps.has(e.timestamp))
                    parameterLog.value = [...parameterLog.value, ...newEntries]
                    console.log(`[StudySession] Loaded ${newEntries.length} entries from backend (session: ${sessionId})`)
                }
            }
        } catch (e) {
            console.warn('[StudySession] Failed to load session history from backend', e)
        }
    }

    const clearSession = async (sessionId: string = 'current') => {
        try {
            await fetch(`/api/study-session/${sessionId}`, { method: 'DELETE' })
        } catch (e) {
            console.warn('[StudySession] Failed to clear session in Redis', e)
        }
        // Reset local state
        sessionActive.value = false
        sessionStartTime.value = null
        parameterLog.value = []
        bestAri.value = -1
        bestAriParams.value = null
        bestAriTime.value = 0
        console.log('[StudySession] Session cleared')
    }

    const downloadSessionLog = () => {
        const entries = parameterLog.value.map(entry => ({
            timestamp: entry.timestamp,
            source: entry.source,
            elapsedSeconds: entry.elapsedSeconds,
            params: entry.params,
            metrics: entry.metrics
        }))

        // Find the best ARI entry across all logged runs
        let bestEntry: (typeof entries)[0] | null = null
        let bestAriValue = -Infinity
        for (const entry of entries) {
            const ari = entry.metrics?.ari
            if (typeof ari === 'number' && ari > bestAriValue) {
                bestAriValue = ari
                bestEntry = entry
            }
        }

        const summary = {
            totalParametersTested: entries.length,
            parametersBySource: entries.reduce((acc: Record<string, number>, e) => {
                acc[e.source] = (acc[e.source] || 0) + 1
                return acc
            }, {}),
            bestAri: bestEntry ? bestAriValue : null,
            bestAriParams: bestEntry?.params ?? null,
            bestAriAchievedAfterSeconds: bestEntry?.elapsedSeconds ?? null,
            bestAriTimestamp: bestEntry?.timestamp ?? null,
            exportedAt: new Date().toISOString()
        }

        const data = { summary, entries }

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `session-log-${new Date().toISOString().slice(0, 10)}.json`
        a.click()
        URL.revokeObjectURL(url)
        console.log(`[StudySession] Downloaded session log with ${entries.length} entries`)
    }

    return {
        sessionActive,
        sessionStartTime,
        parameterLog,
        sessionHistory: computed(() => parameterLog.value),
        bestAri,
        startSession,
        logParameterSet,
        loadSessionHistory,
        clearSession,
        downloadSessionLog,
        elapsedSeconds: computed(() => {
            if (!sessionStartTime.value) return 0
            return Math.floor((Date.now() - sessionStartTime.value) / 1000)
        })
    }
}
