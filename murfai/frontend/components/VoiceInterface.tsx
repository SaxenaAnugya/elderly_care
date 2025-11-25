'use client'

import { useState, useEffect, useRef } from 'react'
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react'
import { apiClient } from '@/lib/api'

export default function VoiceInterface() {
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [aiResponse, setAiResponse] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  useEffect(() => {
    return () => {
      if (sessionId) {
        apiClient.stopVoiceSession(sessionId).catch(console.error)
      }
    }
  }, [sessionId])

  const startListening = async () => {
    try {
      setError(null)
      setTranscript('')
      setAiResponse('')
      
      console.log('[Voice] Starting voice session...')
      
      // Start voice session
      const session = await apiClient.startVoiceSession()
      console.log('[Voice] Session started:', session.session_id)
      const currentSessionId = session.session_id // Capture sessionId immediately
      setSessionId(currentSessionId)

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        // Use captured sessionId (not from state, which might be stale)
        
        // Stop all tracks first
        stream.getTracks().forEach(track => track.stop())
        
        if (audioChunksRef.current.length > 0 && currentSessionId) {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
          
          try {
            console.log('[Voice] Sending audio to backend...', {
              sessionId: currentSessionId,
              audioSize: audioBlob.size
            })
            
            setIsProcessing(true)
            const result = await apiClient.sendVoiceMessage(currentSessionId, audioBlob)
            
            console.log('[Voice] Received response:', result)
            
            if (!result.transcript) {
              throw new Error('No transcript received from server')
            }
            
            // Show transcript immediately - what you said
            setTranscript(result.transcript)
            setIsProcessing(false)
            
            if (!result.response) {
              throw new Error('No response generated from LLM')
            }
            
            // Small delay to show transcript before response
            await new Promise(resolve => setTimeout(resolve, 300))
            
            // Show response
            setAiResponse(result.response)
            setIsSpeaking(true)
            
            // Helper function for browser TTS (defined before use)
            const playBrowserTTS = (text: string) => {
              const utterance = new SpeechSynthesisUtterance(text)
              utterance.rate = 1.0
              utterance.pitch = 1.0
              utterance.volume = 1.0
              
              utterance.onend = () => {
                console.log('[Voice] Browser TTS finished')
                setIsSpeaking(false)
              }
              
              utterance.onerror = (e) => {
                console.error('[Voice] Browser TTS error:', e)
                setIsSpeaking(false)
              }
              
              speechSynthesis.speak(utterance)
            }
            
            // Play response audio if available (from Murf TTS)
            if (result.response_audio) {
              try {
                console.log('[Voice] Playing Murf TTS audio...')
                // Convert base64 to blob
                const audioBytes = Uint8Array.from(atob(result.response_audio), c => c.charCodeAt(0))
                const audioBlob = new Blob([audioBytes], { type: `audio/${result.response_audio_format || 'wav'}` })
                const audioUrl = URL.createObjectURL(audioBlob)
                
                const audio = new Audio(audioUrl)
                audio.volume = 1.0 // Full volume
                
                audio.onended = () => {
                  console.log('[Voice] Audio playback finished')
                  setIsSpeaking(false)
                  URL.revokeObjectURL(audioUrl)
                }
                
                audio.onerror = (e) => {
                  console.error('[Voice] Audio playback error:', e)
                  setIsSpeaking(false)
                  URL.revokeObjectURL(audioUrl)
                  // Fallback to browser TTS
                  playBrowserTTS(result.response)
                }
                
                await audio.play()
                console.log('[Voice] Murf TTS audio playing')
              } catch (error) {
                console.error('[Voice] Error playing Murf audio:', error)
                // Fallback to browser TTS
                playBrowserTTS(result.response)
              }
            } else if (result.response_audio_url) {
              // Legacy: direct URL
              try {
                const audio = new Audio(result.response_audio_url)
                audio.onended = () => setIsSpeaking(false)
                await audio.play()
              } catch (error) {
                console.error('[Voice] Error playing audio URL:', error)
                playBrowserTTS(result.response)
              }
            } else {
              // Fallback: Use browser text-to-speech
              console.log('[Voice] Using browser TTS (no Murf audio)')
              playBrowserTTS(result.response)
            }
          } catch (err: any) {
            console.error('[Voice] Error processing message:', err)
            const errorMessage = err.response?.data?.detail || err.message || 'Failed to process voice message'
            setError(errorMessage)
            setIsSpeaking(false)
            setIsProcessing(false)
          }
        } else {
          if (!currentSessionId) {
            setError('Session not started. Please try again.')
          } else if (audioChunksRef.current.length === 0) {
            setError('No audio recorded. Please speak clearly.')
          }
        }
      }

      mediaRecorder.start()
      setIsListening(true)
      
    } catch (err: any) {
      setError(err.message || 'Failed to start listening. Please check microphone permissions.')
      setIsListening(false)
    }
  }

  const stopListening = () => {
    if (mediaRecorderRef.current && isListening) {
      mediaRecorderRef.current.stop()
      setIsListening(false)
    }
  }

  const toggleVoice = () => {
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-800 mb-4">Voice Conversation</h2>
        <p className="text-xl text-gray-600">Click the microphone to start talking</p>
      </div>

      {/* Main Voice Button with Transcript Display */}
      <div className="flex flex-col items-center space-y-6">
        <button
          onClick={toggleVoice}
          disabled={isSpeaking}
          className={`
            w-48 h-48 rounded-full flex flex-col items-center justify-center
            transition-all duration-300 transform hover:scale-105
            focus-visible-large
            ${isListening
              ? 'bg-red-500 hover:bg-red-600 animate-pulse'
              : isSpeaking
              ? 'bg-blue-500 cursor-not-allowed'
              : 'bg-primary-600 hover:bg-primary-700'
            }
            shadow-2xl
          `}
          aria-label={isListening ? 'Stop listening' : 'Start listening'}
        >
          {isListening ? (
            <MicOff size={64} className="text-white" />
          ) : (
            <Mic size={64} className="text-white" />
          )}
        </button>

        {/* Transcript Display - Shows what you said */}
        {transcript && (
          <div className="w-full max-w-2xl bg-blue-50 border-4 border-blue-300 rounded-xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-3">
              <Mic size={28} className="text-blue-600" />
              <h3 className="text-2xl font-bold text-blue-800">You said:</h3>
            </div>
            <p className="text-2xl text-gray-800 font-medium leading-relaxed">{transcript}</p>
          </div>
        )}

        {/* Processing indicator */}
        {isListening && !transcript && !isProcessing && (
          <div className="w-full max-w-2xl bg-yellow-50 border-4 border-yellow-300 rounded-xl p-6">
            <div className="flex items-center gap-3">
              <div className="animate-pulse w-3 h-3 bg-yellow-600 rounded-full"></div>
              <p className="text-xl font-semibold text-yellow-800">Listening... Speak now</p>
            </div>
          </div>
        )}

        {/* Processing transcript indicator */}
        {isProcessing && (
          <div className="w-full max-w-2xl bg-purple-50 border-4 border-purple-300 rounded-xl p-6">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
              <p className="text-xl font-semibold text-purple-800">Processing your speech...</p>
            </div>
          </div>
        )}

        {/* AI Response Display - Shows what companion says */}
        {aiResponse && (
          <div className="w-full max-w-2xl bg-green-50 border-4 border-green-300 rounded-xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-3">
              <Volume2 size={28} className="text-green-600" />
              <h3 className="text-2xl font-bold text-green-800">Companion says:</h3>
              {isSpeaking && (
                <div className="ml-auto flex items-center gap-2">
                  <div className="animate-pulse w-3 h-3 bg-green-600 rounded-full"></div>
                  <span className="text-lg text-green-700">Speaking...</span>
                </div>
              )}
            </div>
            <p className="text-2xl text-gray-800 font-medium leading-relaxed">{aiResponse}</p>
          </div>
        )}
      </div>

      {/* Status Indicators */}
      <div className="flex justify-center gap-8">
        <div className={`
          flex items-center gap-3 px-6 py-3 rounded-lg
          ${isListening ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'}
        `}>
          {isListening ? <Mic size={24} /> : <MicOff size={24} />}
          <span className="text-xl font-semibold">
            {isListening ? 'Listening...' : 'Not Listening'}
          </span>
        </div>
        
        <div className={`
          flex items-center gap-3 px-6 py-3 rounded-lg
          ${isSpeaking ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'}
        `}>
          {isSpeaking ? <Volume2 size={24} /> : <VolumeX size={24} />}
          <span className="text-xl font-semibold">
            {isSpeaking ? 'Speaking...' : 'Silent'}
          </span>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-6 rounded-lg">
          <p className="text-xl font-semibold">Error</p>
          <p className="text-lg">{error}</p>
        </div>
      )}

      {/* Instructions */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h3 className="text-2xl font-semibold text-gray-800 mb-3">How to use:</h3>
        <ol className="list-decimal list-inside space-y-2 text-lg text-gray-700">
          <li>Click the large microphone button to start</li>
          <li>Speak clearly into your microphone</li>
          <li>Click again to stop and send your message</li>
          <li>Wait for the companion to respond</li>
        </ol>
      </div>
    </div>
  )
}

