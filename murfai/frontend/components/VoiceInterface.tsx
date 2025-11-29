'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Mic, MicOff, Volume2, VolumeX, Settings as SettingsIcon } from 'lucide-react'
import { apiClient } from '@/lib/api'

interface VoiceInterfaceProps {
  voiceGender: 'male' | 'female'
}

type VoiceInterfaceHandle = {
  startListening: () => Promise<void>
  stopListening: () => void
  wsConnected: boolean
}

export default function VoiceInterface({ voiceGender }: VoiceInterfaceProps) {
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [aiResponse, setAiResponse] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [userVolume, setUserVolume] = useState(80)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const sessionIdRef = useRef<string | null>(null)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const isRecordingRef = useRef(false)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const vadIntervalRef = useRef<number | null>(null)
  const inSpeechRef = useRef(false)
  const lastVoiceTimestampRef = useRef<number>(0)
  const pendingTranscriptRef = useRef(false)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  // Convert HTTP URL to WebSocket URL - handle both http and https
  const getWebSocketURL = (apiUrl: string) => {
    if (apiUrl.startsWith('https://')) {
      return apiUrl.replace('https://', 'wss://')
    } else if (apiUrl.startsWith('http://')) {
      return apiUrl.replace('http://', 'ws://')
    }
    // If no protocol, assume http
    return `ws://${apiUrl}`
  }
  const WS_URL = getWebSocketURL(API_URL)
  
  // Load user settings (volume etc.)
  const fetchUserSettings = async () => {
    try {
      const settings = await apiClient.getSettings()
      if (typeof settings.volume === 'number') {
        setUserVolume(settings.volume)
      }
    } catch (err) {
      console.error('[VoiceInterface] Failed to load settings:', err)
    }
  }

  useEffect(() => {
    fetchUserSettings()
  }, [])

  // Debug logging
  useEffect(() => {
    console.log('[VoiceInterface] Configuration:')
    console.log('  API_URL:', API_URL)
    console.log('  WS_URL:', WS_URL)
    console.log('  Full WebSocket URL:', `${WS_URL}/ws/voice`)
    console.log('  User volume:', userVolume)
  }, [API_URL, WS_URL, userVolume])

  useEffect(() => {
    // Check if server is reachable first
    const checkServer = async () => {
      try {
        const response = await fetch(`${API_URL}/health`)
        if (!response.ok) {
          throw new Error('Server not responding')
        }
      } catch (err) {
        setError('Backend server is not running. Please start the server first.')
        setWsConnected(false)
        return false
      }
      return true
    }

    // Initialize WebSocket connection
    const connectWebSocket = async () => {
      // Check server first
      const serverOk = await checkServer()
      if (!serverOk) {
        // Retry after 5 seconds
        setTimeout(connectWebSocket, 5000)
        return
      }

      try {
        console.log(`[WebSocket] Attempting to connect to: ${WS_URL}/ws/voice`)
        const ws = new WebSocket(`${WS_URL}/ws/voice`)
        wsRef.current = ws

        ws.onopen = () => {
          console.log('[WebSocket] Connected successfully')
          setWsConnected(true)
          setError(null)
          // Create a backend voice session for fallback POST uploads
          (async () => {
            try {
              const sess = await apiClient.startVoiceSession()
              if (sess && sess.session_id) {
                sessionIdRef.current = sess.session_id
                console.log('[VoiceInterface] Created voice session:', sess.session_id)
              }
            } catch (e) {
              console.warn('[VoiceInterface] startVoiceSession failed', e)
            }
          })()
        }

        ws.onmessage = async (event) => {
          try {
            const message = JSON.parse(event.data)
            console.log('[WebSocket] Message received:', message.type)

            switch (message.type) {
              case 'transcript':
                // Handle server transcript messages. Server may send status 'no_speech'.
                if (message.status === 'no_speech') {
                  // Server detected no speech — show processing/loading while server may synthesize fallback TTS
                  pendingTranscriptRef.current = false
                  setIsProcessing(true)
                  // Keep listening active but forwarding is gated by VAD + isSpeaking flag
                } else if (message.text) {
                  // Valid transcript arrived
                  pendingTranscriptRef.current = false
                  setTranscript(message.text)
                  setIsProcessing(true)
                }
                break

              case 'response':
                setAiResponse(message.text)
                setIsProcessing(false)
                break

                case 'audio':
                if (message.data) {
                  // When the companion speaks, pause sending audio to the server
                  // so the server can generate TTS without getting loopback.
                      pendingTranscriptRef.current = false
                      // Stop showing processing/loading when audio starts
                      setIsProcessing(false)
                      setIsSpeaking(true)

                  // Convert base64 to audio
                  const audioBytes = Uint8Array.from(atob(message.data), c => c.charCodeAt(0))
                  const audioBlob = new Blob([audioBytes], { type: `audio/${message.format || 'wav'}` })
                  const audioUrl = URL.createObjectURL(audioBlob)

                  // Stop any existing audio
                  if (currentAudioRef.current) {
                    currentAudioRef.current.pause()
                    currentAudioRef.current = null
                  }

                  const audio = new Audio(audioUrl)
                  audio.volume = Math.min(Math.max(userVolume / 100, 0), 1)
                  currentAudioRef.current = audio

                  audio.onended = () => {
                    setIsSpeaking(false)
                    URL.revokeObjectURL(audioUrl)
                    currentAudioRef.current = null
                    // keep listening active; forwarding will resume automatically when VAD detects speech
                  }

                  audio.onerror = () => {
                    setIsSpeaking(false)
                    URL.revokeObjectURL(audioUrl)
                    currentAudioRef.current = null
                    setError('Error playing audio')
                  }

                  await audio.play()
                }
                break

              case 'error':
                setError(message.message)
                setIsProcessing(false)
                setIsListening(false)
                break

              case 'pong':
                // Keep-alive response
                break
            }
          } catch (err) {
            console.error('[WebSocket] Error parsing message:', err)
          }
        }

        ws.onerror = (error) => {
          console.error('[WebSocket] Connection error:', error)
          const errorMsg = 'Failed to connect to server. Make sure the backend is running: python backend/api_server.py'
          setError(errorMsg)
          setWsConnected(false)
        }

        ws.onclose = (event) => {
          console.log('[WebSocket] Disconnected', { 
            code: event.code, 
            reason: event.reason,
            wasClean: event.wasClean 
          })
          setWsConnected(false)
          
          // Error code 1006 = abnormal closure (server not running or connection refused)
          if (event.code === 1006) {
            setError('Server connection refused. Please start the backend server first.')
          }
          
          // Only reconnect if it wasn't a manual close (code 1000) and not a refused connection
          if (event.code !== 1000 && event.code !== 1006) {
            // Attempt to reconnect after 3 seconds
            setTimeout(connectWebSocket, 3000)
          } else if (event.code === 1006) {
            // Retry after 5 seconds for connection refused
            setTimeout(connectWebSocket, 5000)
          }
          // Try to stop voice session if exists
          if (sessionIdRef.current) {
            try {
              apiClient.stopVoiceSession(sessionIdRef.current).catch(() => {})
            } catch {}
            sessionIdRef.current = null
          }
        }
      } catch (err: any) {
        console.error('[WebSocket] Connection error:', err)
        setError(`Failed to connect: ${err.message || 'Unknown error'}. Make sure the backend server is running.`)
        setWsConnected(false)
        // Retry after 5 seconds
        setTimeout(connectWebSocket, 5000)
      }
    }

    connectWebSocket()

    return () => {
      // Cleanup
      if (wsRef.current) {
        wsRef.current.close()
      }
      stopAllAudio()
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [WS_URL])

  const stopAllAudio = () => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current.currentTime = 0
      currentAudioRef.current = null
    }
    setIsSpeaking(false)
  }

  const startListening = async () => {
    try {
      setError(null)
      // Refresh latest settings before starting
      await fetchUserSettings()
      setTranscript('')
      setAiResponse('')
      
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('Not connected to server. Please wait...')
        return
      }

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      
      streamRef.current = stream
      // Setup Web Audio VAD (RMS-based) to avoid sending background noise
      try {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
        const audioCtx = new AudioCtx()
        audioContextRef.current = audioCtx
        const source = audioCtx.createMediaStreamSource(stream)
        const analyser = audioCtx.createAnalyser()
        analyser.fftSize = 2048
        source.connect(analyser)
        analyserRef.current = analyser

        // VAD parameters
        const VAD_THRESHOLD = 0.02 // RMS threshold
        const VAD_MIN_SPEECH_MS = 150 // require 150ms above threshold to start
        const VAD_SILENCE_MS = Number(process.env.NEXT_PUBLIC_PATIENCE_MS || 2000) // 2s default

        let speechStartCandidate = 0
        lastVoiceTimestampRef.current = Date.now()

        vadIntervalRef.current = window.setInterval(() => {
          try {
            const bufferLength = analyser.fftSize
            const data = new Float32Array(bufferLength)
            analyser.getFloatTimeDomainData(data)
            let sum = 0
            for (let i = 0; i < bufferLength; i++) {
              sum += data[i] * data[i]
            }
            const rms = Math.sqrt(sum / bufferLength)

            const now = Date.now()
            if (rms > VAD_THRESHOLD) {
              // possible speech
              if (!inSpeechRef.current) {
                if (!speechStartCandidate) speechStartCandidate = now
                if (now - speechStartCandidate > VAD_MIN_SPEECH_MS) {
                  inSpeechRef.current = true
                  lastVoiceTimestampRef.current = now
                  // If the companion is speaking or processing and user begins to speak,
                  // interrupt playback so user speech can take priority.
                  if (isSpeaking) {
                    try {
                      if (currentAudioRef.current) {
                        currentAudioRef.current.pause()
                        currentAudioRef.current = null
                      }
                    } catch (e) {
                      console.error('[VoiceInterface] Failed to interrupt playback', e)
                    }
                    setIsSpeaking(false)
                  }
                  if (isProcessing) {
                    // User speech should take precedence over processing UI
                    setIsProcessing(false)
                  }
                }
              } else {
                lastVoiceTimestampRef.current = now
              }
            } else {
              // below threshold
              speechStartCandidate = 0
              if (inSpeechRef.current) {
                // check if silence duration exceeded
                if (now - lastVoiceTimestampRef.current > VAD_SILENCE_MS) {
                  inSpeechRef.current = false
                  // trigger end of utterance: send control message but keep listening
                  setIsProcessing(true)
                  pendingTranscriptRef.current = true
                  if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                    try {
                      console.log('[VoiceInterface] Sending end_of_utterance')
                      wsRef.current.send(JSON.stringify({ type: 'end_of_utterance' }))
                    } catch (e) {
                      console.error('[VoiceInterface] Failed to send end_of_utterance', e)
                    }
                  }

                  // Also POST accumulated chunks as a single Blob fallback (multipart/form-data)
                  try {
                    const chunks = audioChunksRef.current.slice()
                    if (chunks && chunks.length > 0 && sessionIdRef.current) {
                      const blob = new Blob(chunks, { type: 'audio/webm' })
                      console.log('[VoiceInterface] Fallback: POSTing final blob', blob.size)
                      // fire-and-forget, update processing state
                      apiClient.sendVoiceMessage(sessionIdRef.current, blob)
                        .then((resp) => {
                          if (resp && resp.transcript) {
                            setTranscript(resp.transcript)
                            setAiResponse(resp.response || '')
                          }
                        })
                        .catch(err => {
                          console.warn('[VoiceInterface] sendVoiceMessage fallback failed', err)
                        })
                        .finally(() => {
                          // keep show processing until server sends websocket response
                        })
                    }
                  } catch (e) {
                    console.error('[VoiceInterface] Fallback POST failed', e)
                  }
                  // Continue listening and streaming; the server will process the buffered audio
                }
              }
            }
          } catch (e) {
            console.error('[VoiceInterface] VAD error', e)
          }
        }, 100)
      } catch (e) {
        console.warn('[VoiceInterface] WebAudio not available, falling back to no client-side VAD', e)
      }
      
      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          // Accumulate chunks and stream in real-time
          audioChunksRef.current.push(event.data)
          // only forward chunks when VAD indicates speech and not currently speaking or processing
          const shouldForward = inSpeechRef.current && !isSpeaking && !isProcessing
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && shouldForward) {
            try {
              console.log(`[VoiceInterface] Sending audio chunk: ${event.data.size} bytes`)
              wsRef.current.send(event.data)
            } catch (e) {
              console.error('[VoiceInterface] Failed to send audio chunk', e)
            }
          }
        }
      }

      mediaRecorder.onstop = () => {
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop())
        streamRef.current = null
        
        audioChunksRef.current = []
        setIsListening(false)
        isRecordingRef.current = false
      }

      // Start recording with timeslice for real-time streaming
      mediaRecorder.start(250) // Stream chunks every 250ms
      setIsListening(true)
      isRecordingRef.current = true
      
    } catch (err: any) {
      setError(err.message || 'Failed to start listening. Please check microphone permissions.')
      setIsListening(false)
    }
  }

  const stopListening = () => {
    if (mediaRecorderRef.current && isListening) {
      mediaRecorderRef.current.stop()
      setIsListening(false)
      isRecordingRef.current = false
    }
    // teardown VAD
    if (vadIntervalRef.current) {
      clearInterval(vadIntervalRef.current)
      vadIntervalRef.current = null
    }
    if (analyserRef.current) {
      try { analyserRef.current.disconnect() } catch {}
      analyserRef.current = null
    }
    if (audioContextRef.current) {
      try { audioContextRef.current.close() } catch {}
      audioContextRef.current = null
    }
  }

  const toggleVoice = () => {
    // Keep a toggle available for manual control, but the component auto-starts/stops.
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }

  useEffect(() => {
    // Auto-start listening once connected and not currently speaking
    if (wsConnected && !isListening && !isSpeaking) {
      // Defer to allow UI and permissions dialog
      const t = setTimeout(() => {
        startListening().catch(err => console.error('[VoiceInterface] auto start failed', err))
      }, 300)
      return () => clearTimeout(t)
    }
  }, [wsConnected])

  // Compute classes for the main voice button to avoid large inline template literals in JSX
  const buttonClass = (() => {
    const base = 'w-72 h-72 rounded-full flex flex-col items-center justify-center transition-all duration-300 transform hover:scale-105 focus:outline-none focus:ring-4 focus:ring-opacity-50'
    let stateClass = 'bg-black text-white hover:opacity-95 shadow-2xl'
    if (!wsConnected) stateClass = 'bg-gray-400 cursor-not-allowed'
    else if (isListening) stateClass = 'bg-red-600 hover:bg-red-700 animate-pulse shadow-2xl'
    else if (isSpeaking) stateClass = 'bg-blue-700 hover:bg-blue-800 shadow-2xl'
    return `${base} ${stateClass}`
  })()

  // Component does not expose imperative ref methods in this build —
  // keep the component as a normal client component and avoid
  // relying on a parent ref to prevent runtime errors.

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-gradient-to-br from-indigo-50 via-white to-rose-50">
      <div className="absolute top-6 left-6">
        <div className="flex items-center gap-3">
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-purple-600 to-indigo-500 shadow-lg flex items-center justify-center text-white text-2xl font-semibold">YC</div>
          <div>
            <div className="text-sm text-gray-600">Your Companion</div>
            <div className="text-sm font-medium text-gray-800">Warm & gentle voice</div>
          </div>
        </div>
      </div>

      <div className="w-full max-w-4xl backdrop-blur-sm bg-white/70 rounded-3xl p-8 shadow-2xl border border-white/40">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-6xl font-semibold text-gray-900 mb-2 tracking-wide" role="heading" aria-level={1}>
          Your Companion
        </h1>
        <p className="text-2xl text-gray-700 font-medium" aria-hidden={false}>
          {voiceGender === 'female' ? 'Warm and caring' : 'Calm and reassuring'}
        </p>
      </div>

      {/* Connection Status */}
      {!wsConnected && (
        <div className="mb-6 bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 rounded-lg max-w-md">
          <p className="text-lg font-semibold">Connecting to server...</p>
          <p className="text-sm mt-2">Make sure the backend server is running on port 8000</p>
          {error && (
            <p className="text-sm mt-2 font-semibold text-red-700">{error}</p>
          )}
        </div>
      )}
      
      {wsConnected && (
        <div className="mb-6 bg-green-50/80 border-l-4 border-green-400 text-green-700 p-4 rounded-lg max-w-md shadow-sm">
          <p className="text-lg font-semibold">✓ Connected</p>
          <p className="text-sm text-green-700/80">Voice assistant ready — just speak naturally</p>
        </div>
      )}

      {/* Main Voice Button */}
      <div className="flex flex-col items-center space-y-8 mb-8 mt-6">
        <button
          onClick={toggleVoice}
          disabled={!wsConnected}
          className={buttonClass}
          aria-label={isListening ? 'Stop listening' : isSpeaking ? 'Stop speaking' : 'Start listening'}
          aria-pressed={isListening}
          aria-live="polite"
        >
          {isListening ? (
            <MicOff size={80} className="text-white" />
          ) : (
            <Mic size={88} className="text-white" />
          )}
        </button>

        {/* Status Text */}
        <div className="text-center">
          {isListening && (
            <p className="text-3xl font-medium text-red-700 animate-pulse" role="status" aria-live="polite">Listening…</p>
          )}
          {isSpeaking && (
            <p className="text-3xl font-medium text-blue-700" role="status" aria-live="polite">Speaking…</p>
          )}
          {!isListening && !isSpeaking && wsConnected && (
            <p className="text-3xl font-medium text-gray-700">Tap to start talking</p>
          )}
        </div>
      </div>

      {/* Transcript Display */}
      {transcript && (
        <div className="w-full max-w-3xl bg-white/90 backdrop-blur-lg border-4 border-blue-300 rounded-2xl p-8 shadow-xl mb-6" role="region" aria-live="polite">
          <div className="flex items-center gap-3 mb-4">
            <Mic size={28} className="text-blue-600" />
            <h3 className="text-2xl font-light text-blue-800">You said:</h3>
          </div>
          <p className="text-2xl text-gray-900 font-medium leading-relaxed">{transcript}</p>
        </div>
      )}

      {/* Processing indicator */}
      {isProcessing && (
        <div className="w-full max-w-3xl bg-white/90 backdrop-blur-lg border-4 border-purple-300 rounded-2xl p-6 mb-6" role="status" aria-live="polite">
          <div className="flex items-center gap-4">
            <div className="animate-spin rounded-full h-10 w-10 border-b-4 border-purple-700"></div>
            <p className="text-2xl font-medium text-purple-900">Processing your message — please wait</p>
          </div>
        </div>
      )}

      {/* AI Response Display */}
      {aiResponse && (
        <div className="w-full max-w-3xl bg-white/80 backdrop-blur-lg border-2 border-green-200 rounded-2xl p-8 shadow-xl mb-6">
          <div className="flex items-center gap-3 mb-4">
            <Volume2 size={28} className="text-green-600" />
            <h3 className="text-2xl font-light text-green-800">Companion says:</h3>
            {isSpeaking && (
              <div className="ml-auto flex items-center gap-2">
                <div className="animate-pulse w-3 h-3 bg-green-600 rounded-full"></div>
                <span className="text-lg text-green-700 font-light">Speaking...</span>
              </div>
            )}
          </div>
          <p className="text-2xl text-gray-800 font-light leading-relaxed">{aiResponse}</p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="w-full max-w-3xl bg-red-100 border-l-4 border-red-500 text-red-700 p-6 rounded-lg mb-6">
          <p className="text-xl font-semibold">Error</p>
          <p className="text-lg">{error}</p>
        </div>
      )}

      {/* Status Indicators */}
      <div className="flex justify-center gap-8 mt-8">
        <div className={`
          flex items-center gap-3 px-6 py-3 rounded-lg backdrop-blur-lg
          ${isListening ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'}
        `}>
          {isListening ? <Mic size={24} /> : <MicOff size={24} />}
          <span className="text-xl font-light">
            {isListening ? 'Listening' : 'Not Listening'}
          </span>
        </div>
        
        <div className={`
          flex items-center gap-3 px-6 py-3 rounded-lg backdrop-blur-lg
          ${isSpeaking ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'}
        `}>
          {isSpeaking ? <Volume2 size={24} /> : <VolumeX size={24} />}
          <span className="text-xl font-light">
            {isSpeaking ? 'Speaking' : 'Silent'}
          </span>
        </div>
      </div>
    </div>
  )
}
