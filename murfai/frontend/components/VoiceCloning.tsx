'use client'

import { useState, useEffect } from 'react'
import { Mic, Search, Play, Loader2, Check, X } from 'lucide-react'
import { apiClient, FishAudioVoice } from '@/lib/api'

export default function VoiceCloning() {
  const [voices, setVoices] = useState<FishAudioVoice[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedVoice, setSelectedVoice] = useState<string | null>(null)
  const [testingVoice, setTestingVoice] = useState<string | null>(null)
  const [testAudio, setTestAudio] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [savedVoiceId, setSavedVoiceId] = useState<string | null>(null)

  useEffect(() => {
    loadVoices()
    loadSavedVoice()
  }, [])

  const loadVoices = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiClient.listFishAudioVoices(100)
      setVoices(response.voices || [])
    } catch (err: any) {
      console.error('Failed to load voices:', err)
      setError(err.message || 'Failed to load voices. Make sure FISH_AUDIO_API_KEY is configured.')
    } finally {
      setLoading(false)
    }
  }

  const loadSavedVoice = async () => {
    try {
      const settings = await apiClient.getSettings()
      if (settings.voice_clone_id) {
        setSavedVoiceId(settings.voice_clone_id)
        setSelectedVoice(settings.voice_clone_id)
      }
    } catch (err) {
      console.error('Failed to load saved voice:', err)
    }
  }

  const testVoice = async (voiceId: string) => {
    try {
      setTestingVoice(voiceId)
      setError(null)
      const testText = "Hello! This is a test of the voice cloning feature. How do I sound?"
      const result = await apiClient.testFishAudioVoice(testText, voiceId, 'en')
      
      if (result.audio) {
        setTestAudio(result.audio)
        // Auto-play the test audio
        playAudio(result.audio, result.format)
      }
    } catch (err: any) {
      console.error('Failed to test voice:', err)
      setError(err.message || 'Failed to test voice')
    } finally {
      setTestingVoice(null)
    }
  }

  const playAudio = (base64Audio: string, format: string = 'mp3') => {
    try {
      const audioBytes = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0))
      const audioBlob = new Blob([audioBytes], { type: `audio/${format}` })
      const audioUrl = URL.createObjectURL(audioBlob)
      const audio = new Audio(audioUrl)
      
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl)
      }
      
      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl)
        setError('Failed to play audio')
      }
      
      audio.play().catch(err => {
        console.error('Failed to play audio:', err)
        setError('Failed to play audio')
      })
    } catch (err: any) {
      console.error('Error playing audio:', err)
      setError('Error playing audio')
    }
  }

  const saveVoice = async (voiceId: string) => {
    try {
      setError(null)
      await apiClient.updateSettings({
        tts_provider: 'fish_audio',
        voice_clone_id: voiceId
      })
      setSavedVoiceId(voiceId)
      alert('Voice saved successfully! Your companion will now use this voice.')
    } catch (err: any) {
      console.error('Failed to save voice:', err)
      setError(err.message || 'Failed to save voice')
    }
  }

  const removeVoice = async () => {
    try {
      setError(null)
      await apiClient.updateSettings({
        tts_provider: 'murf',
        voice_clone_id: null
      })
      setSavedVoiceId(null)
      setSelectedVoice(null)
      alert('Voice removed. Your companion will now use the default Murf voice.')
    } catch (err: any) {
      console.error('Failed to remove voice:', err)
      setError(err.message || 'Failed to remove voice')
    }
  }

  const filteredVoices = voices.filter(voice => {
    if (!searchTerm) return true
    const search = searchTerm.toLowerCase()
    const name = (voice.name || '').toLowerCase()
    const description = (voice.description || '').toLowerCase()
    const id = (voice.id || '').toLowerCase()
    return name.includes(search) || description.includes(search) || id.includes(search)
  })

  if (loading) {
    return (
      <div className="text-center py-12">
        <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-primary-600" />
        <p className="text-2xl text-gray-600">Loading voices...</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold text-gray-800">Voice Cloning</h2>
          <p className="text-lg text-gray-600 mt-2">
            Choose a custom voice from Fish Audio or use the default Murf voice
          </p>
        </div>
        {savedVoiceId && (
          <button
            onClick={removeVoice}
            className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
          >
            <X size={20} />
            Remove Custom Voice
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-lg">
          <p className="font-semibold">Error</p>
          <p>{error}</p>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
        <input
          type="text"
          placeholder="Search voices by name, description, or ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-12 pr-4 py-3 border-2 border-gray-300 rounded-lg text-lg focus:border-primary-500 focus:outline-none"
        />
      </div>

      {/* Popular Voices */}
      <div>
        <h3 className="text-2xl font-semibold text-gray-800 mb-4">Popular Voices</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* E-Girl Voice */}
          <div className="bg-white border-2 border-gray-200 rounded-lg p-6 hover:border-primary-400 transition-all">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-xl font-semibold text-gray-800">E-Girl Voice</h4>
              {savedVoiceId === '8ef4a238714b45718ce04243307c57a7' && (
                <Check className="text-green-600" size={24} />
              )}
            </div>
            <p className="text-gray-600 mb-4">Energetic and friendly female voice</p>
            <div className="flex gap-2">
              <button
                onClick={() => testVoice('8ef4a238714b45718ce04243307c57a7')}
                disabled={testingVoice === '8ef4a238714b45718ce04243307c57a7'}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {testingVoice === '8ef4a238714b45718ce04243307c57a7' ? (
                  <Loader2 className="animate-spin" size={18} />
                ) : (
                  <Play size={18} />
                )}
                Test
              </button>
              <button
                onClick={() => saveVoice('8ef4a238714b45718ce04243307c57a7')}
                className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center justify-center gap-2"
              >
                <Check size={18} />
                Use
              </button>
            </div>
          </div>

          {/* User's Reference Voice */}
          <div className="bg-white border-2 border-gray-200 rounded-lg p-6 hover:border-primary-400 transition-all">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-xl font-semibold text-gray-800">Your Reference Voice</h4>
              {savedVoiceId === '61bdc9150d924bd0bdbefa7bb55a607c' && (
                <Check className="text-green-600" size={24} />
              )}
            </div>
            <p className="text-gray-600 mb-4">Custom voice from your reference ID: 61bdc9150d924bd0bdbefa7bb55a607c</p>
            <div className="flex gap-2">
              <button
                onClick={() => testVoice('61bdc9150d924bd0bdbefa7bb55a607c')}
                disabled={testingVoice === '61bdc9150d924bd0bdbefa7bb55a607c'}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {testingVoice === '61bdc9150d924bd0bdbefa7bb55a607c' ? (
                  <Loader2 className="animate-spin" size={18} />
                ) : (
                  <Play size={18} />
                )}
                Test
              </button>
              <button
                onClick={() => saveVoice('61bdc9150d924bd0bdbefa7bb55a607c')}
                className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center justify-center gap-2"
              >
                <Check size={18} />
                Use
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* All Voices */}
      <div>
        <h3 className="text-2xl font-semibold text-gray-800 mb-4">
          All Voices ({filteredVoices.length})
        </h3>
        {filteredVoices.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-lg">
            <p className="text-xl text-gray-600">No voices found matching your search.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredVoices.map((voice) => (
              <div
                key={voice.id}
                className={`bg-white border-2 rounded-lg p-6 transition-all ${
                  selectedVoice === voice.id
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-primary-400'
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-xl font-semibold text-gray-800">
                    {voice.name || voice.id}
                  </h4>
                  {savedVoiceId === voice.id && (
                    <Check className="text-green-600" size={24} />
                  )}
                </div>
                {voice.description && (
                  <p className="text-gray-600 mb-2 text-sm">{voice.description}</p>
                )}
                <div className="flex gap-2 text-sm text-gray-500 mb-4">
                  {voice.language && <span>Language: {voice.language}</span>}
                  {voice.gender && <span>• Gender: {voice.gender}</span>}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => testVoice(voice.id)}
                    disabled={testingVoice === voice.id}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {testingVoice === voice.id ? (
                      <Loader2 className="animate-spin" size={18} />
                    ) : (
                      <Play size={18} />
                    )}
                    Test
                  </button>
                  <button
                    onClick={() => saveVoice(voice.id)}
                    className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center justify-center gap-2"
                  >
                    <Check size={18} />
                    Use
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

