 'use client'

import { useState, useEffect } from 'react'
import VoiceInterface from '@/components/VoiceInterface'
import { apiClient } from '@/lib/api'

type VoiceGender = 'male' | 'female'

export default function Home() {
  const [voiceGender, setVoiceGender] = useState<VoiceGender>('female')
  const [isInitialized, setIsInitialized] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Load voice gender from settings
    const loadSettings = async () => {
      try {
        const settings = await apiClient.getSettings()
        if (settings.voice_gender === 'male' || settings.voice_gender === 'female') {
          setVoiceGender(settings.voice_gender)
        }
      } catch (error) {
        console.error('Failed to load settings:', error)
      } finally {
        setIsLoading(false)
      }
    }
    loadSettings()
  }, [])

  const handleVoiceSelect = async (gender: VoiceGender) => {
    setVoiceGender(gender)
    setIsInitialized(true)
    
    // Save voice gender to settings
    try {
      await apiClient.updateSettings({ voice_gender: gender })
    } catch (error) {
      console.error('Failed to save voice gender:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center bg-white/30 backdrop-blur-sm rounded-lg p-8">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-2xl text-gray-700">Loading...</p>
        </div>
      </div>
    )
  }

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="max-w-4xl w-full">
          {/* Header */}
          <div className="text-center mb-12">
            <h1 className="text-6xl font-light text-gray-800 mb-4 tracking-wide">
            <b>NIVARA </b>
            </h1>
            
            <p className="text-2xl text-gray-600 font-light">
            Your trusted AI SAATHI, listening deeply, caring quietly, supporting your wellness gently.
            </p>
          </div>

          {/* Voice Selection */}
          <div className="rounded-3xl p-12">
            <h2 className="text-4xl font-light text-gray-800 text-center mb-8">
              Choose Your Companion's Voice
            </h2>
            
            <div className="grid md:grid-cols-2 gap-8 max-w-2xl mx-auto">
              {/* Female Voice Option */}
              <button
                onClick={() => handleVoiceSelect('female')}
                className="group relative overflow-hidden bg-gradient-to-br from-pink-50 to-rose-50 rounded-2xl p-8 border-2 border-pink-200 hover:border-pink-400 transition-all duration-300 hover:shadow-xl transform hover:scale-105"
              >
                <div className="text-center">
                  <div className="mb-6">
                    <div className="w-32 h-32 mx-auto bg-gradient-to-br from-pink-200 to-rose-300 rounded-full flex items-center justify-center shadow-lg group-hover:shadow-xl transition-shadow">
                      <svg className="w-16 h-16 text-pink-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </div>
                  <h3 className="text-3xl font-light text-gray-800 mb-2">Female Voice</h3>
                  <p className="text-lg text-gray-600 font-light">Warm and soothing</p>
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-pink-400/0 to-rose-400/0 group-hover:from-pink-400/10 group-hover:to-rose-400/10 transition-all duration-300"></div>
              </button>

              {/* Male Voice Option */}
              <button
                onClick={() => handleVoiceSelect('male')}
                className="group relative overflow-hidden bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-8 border-2 border-blue-200 hover:border-blue-400 transition-all duration-300 hover:shadow-xl transform hover:scale-105"
              >
                <div className="text-center">
                  <div className="mb-6">
                    <div className="w-32 h-32 mx-auto bg-gradient-to-br from-blue-200 to-indigo-300 rounded-full flex items-center justify-center shadow-lg group-hover:shadow-xl transition-shadow">
                      <svg className="w-16 h-16 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </div>
                  <h3 className="text-3xl font-light text-gray-800 mb-2">Male Voice</h3>
                  <p className="text-lg text-gray-600 font-light">Calm and reassuring</p>
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-blue-400/0 to-indigo-400/0 group-hover:from-blue-400/10 group-hover:to-indigo-400/10 transition-all duration-300"></div>
              </button>
            </div>
          </div>

          {/* Decorative elements */}
          <div className="mt-12 text-center">
            <p className="text-lg text-gray-500 font-light">
              Select a voice to begin your conversation
            </p>
          </div>
        </div>
      </div>
    )
  }

  // Show voice interface after selection
  return (
    <div className="min-h-screen">
      <VoiceInterface voiceGender={voiceGender} />
    </div>
  )
}
