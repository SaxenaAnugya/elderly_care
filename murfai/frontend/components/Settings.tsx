'use client'

import { useState, useEffect } from 'react'
import { Save, Volume2, Clock, Heart, Mic, Plus, Trash2, CheckCircle, Circle, Phone } from 'lucide-react'
import { apiClient, VoiceClone } from '@/lib/api'

export default function Settings() {
  const [settings, setSettings] = useState({
    volume: 80,
    speech_rate: 1.0,
    patience_mode: 2000,
    sundowning_hour: 17,
    medication_reminders_enabled: true,
    word_of_day_enabled: true,
    emergency_number: '',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [voiceClones, setVoiceClones] = useState<VoiceClone[]>([])
  const [activeVoiceId, setActiveVoiceId] = useState<number | null>(null)
  const [showAddVoice, setShowAddVoice] = useState(false)
  const [newVoice, setNewVoice] = useState({ name: '', reference_id: '', description: '' })

  useEffect(() => {
    loadSettings()
    loadVoiceClones()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await apiClient.getSettings()
      setSettings({ ...settings, ...data, emergency_number: data.emergency_number || '' })
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadVoiceClones = async () => {
    try {
      const voices = await apiClient.getVoiceClones()
      setVoiceClones(voices)
      
      const activeVoice = await apiClient.getActiveVoiceClone()
      if (activeVoice?.id) {
        setActiveVoiceId(activeVoice.id)
      }
    } catch (error) {
      console.error('Failed to load voice clones:', error)
    }
  }

  const handleAddVoice = async () => {
    if (!newVoice.name || !newVoice.reference_id) {
      setMessage({ type: 'error', text: 'Please provide a name and reference ID' })
      return
    }

    try {
      await apiClient.addVoiceClone(newVoice)
      setMessage({ type: 'success', text: 'Voice clone added successfully!' })
      setNewVoice({ name: '', reference_id: '', description: '' })
      setShowAddVoice(false)
      await loadVoiceClones()
      setTimeout(() => setMessage(null), 3000)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to add voice clone' })
    }
  }

  const handleActivateVoice = async (voiceId: number) => {
    try {
      await apiClient.activateVoiceClone(voiceId)
      setActiveVoiceId(voiceId)
      setMessage({ type: 'success', text: 'Voice activated successfully!' })
      await loadVoiceClones()
      setTimeout(() => setMessage(null), 3000)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to activate voice' })
    }
  }

  const handleDeleteVoice = async (voiceId: number) => {
    if (!confirm('Are you sure you want to delete this voice clone?')) {
      return
    }

    try {
      await apiClient.deleteVoiceClone(voiceId)
      setMessage({ type: 'success', text: 'Voice clone deleted successfully!' })
      if (activeVoiceId === voiceId) {
        setActiveVoiceId(null)
      }
      await loadVoiceClones()
      setTimeout(() => setMessage(null), 3000)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to delete voice clone' })
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setMessage(null)
      await apiClient.updateSettings(settings)
      setMessage({ type: 'success', text: 'Settings saved successfully!' })
      setTimeout(() => setMessage(null), 3000)
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save settings. Please try again.' })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <p className="text-2xl text-gray-600">Loading settings...</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-800">Settings</h2>
        <button
          onClick={handleSave}
          disabled={saving}
          className="button-large bg-primary-600 text-white hover:bg-primary-700 flex items-center gap-2 disabled:opacity-50"
        >
          <Save size={20} />
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>

      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-100 text-green-700 border-l-4 border-green-500'
              : 'bg-red-100 text-red-700 border-l-4 border-red-500'
          }`}
        >
          <p className="text-lg font-semibold">{message.text}</p>
        </div>
      )}

      <div className="space-y-6">
        {/* Audio Settings */}
        <div className="bg-white border-2 border-gray-200 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <Volume2 size={24} className="text-primary-600" />
            <h3 className="text-2xl font-semibold text-gray-800">Audio Settings</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xl font-semibold text-gray-700 mb-2">
                Volume: {settings.volume}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={settings.volume}
                onChange={(e) => setSettings({ ...settings, volume: parseInt(e.target.value) })}
                className="w-full h-4 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <label className="block text-xl font-semibold text-gray-700 mb-2">
                Speech Rate: {settings.speech_rate.toFixed(1)}x
              </label>
              <input
                type="range"
                min="0.5"
                max="2.0"
                step="0.1"
                value={settings.speech_rate}
                onChange={(e) => setSettings({ ...settings, speech_rate: parseFloat(e.target.value) })}
                className="w-full h-4 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        </div>

        {/* Conversation Settings */}
        <div className="bg-white border-2 border-gray-200 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <Clock size={24} className="text-primary-600" />
            <h3 className="text-2xl font-semibold text-gray-800">Conversation Settings</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xl font-semibold text-gray-700 mb-2">
                Patience Mode (silence detection): {settings.patience_mode}ms
              </label>
              <input
                type="range"
                min="1000"
                max="5000"
                step="100"
                value={settings.patience_mode}
                onChange={(e) => setSettings({ ...settings, patience_mode: parseInt(e.target.value) })}
                className="w-full h-4 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <p className="text-base text-gray-600 mt-1">
                Higher values wait longer for you to finish speaking
              </p>
            </div>

            <div>
              <label className="block text-xl font-semibold text-gray-700 mb-2">
                Sundowning Hour (calming mode starts): {settings.sundowning_hour}:00
              </label>
              <input
                type="range"
                min="12"
                max="22"
                value={settings.sundowning_hour}
                onChange={(e) => setSettings({ ...settings, sundowning_hour: parseInt(e.target.value) })}
                className="w-full h-4 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <p className="text-base text-gray-600 mt-1">
                Voice becomes calmer after this hour
              </p>
            </div>
          </div>
        </div>

        {/* Emergency Contact */}
        <div className="bg-white border-2 border-gray-200 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <Phone size={24} className="text-red-600" />
            <h3 className="text-2xl font-semibold text-gray-800">Emergency Contact</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xl font-semibold text-gray-700 mb-2">
                Emergency Phone Number
              </label>
              <input
                type="tel"
                value={settings.emergency_number || ''}
                onChange={(e) => setSettings({ ...settings, emergency_number: e.target.value })}
                placeholder="+1234567890 or 123-456-7890"
                className="w-full px-4 py-3 text-xl border-2 border-gray-300 rounded-lg focus:border-red-500 focus:ring-2 focus:ring-red-500 focus:outline-none"
              />
              <p className="text-base text-gray-600 mt-2">
                <strong>Important:</strong> This number will be automatically called if 5 or more depressive/risky conversations are detected in a row. 
                Please ensure this is a trusted contact (family member, caregiver, or emergency services).
              </p>
              <p className="text-sm text-gray-500 mt-1">
                The system monitors conversation sentiment and will trigger an emergency call if concerning patterns are detected.
              </p>
            </div>
          </div>
        </div>

        {/* Feature Toggles */}
        <div className="bg-white border-2 border-gray-200 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <Heart size={24} className="text-primary-600" />
            <h3 className="text-2xl font-semibold text-gray-800">Features</h3>
          </div>

          <div className="space-y-4">
            <label className="flex items-center gap-4 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.medication_reminders_enabled}
                onChange={(e) =>
                  setSettings({ ...settings, medication_reminders_enabled: e.target.checked })
                }
                className="w-6 h-6 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-xl text-gray-700">Enable Medication Reminders</span>
            </label>

            <label className="flex items-center gap-4 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.word_of_day_enabled}
                onChange={(e) => setSettings({ ...settings, word_of_day_enabled: e.target.checked })}
                className="w-6 h-6 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-xl text-gray-700">Enable Word of the Day</span>
            </label>
          </div>
        </div>

        {/* Voice Cloning */}
        <div className="bg-white border-2 border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Mic size={24} className="text-primary-600" />
              <h3 className="text-2xl font-semibold text-gray-800">Voice Clones (Fish Audio)</h3>
            </div>
            <button
              onClick={() => setShowAddVoice(!showAddVoice)}
              className="button-large bg-primary-600 text-white hover:bg-primary-700 flex items-center gap-2"
            >
              <Plus size={20} />
              Add Voice
            </button>
          </div>

          {showAddVoice && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg border-2 border-gray-300">
              <h4 className="text-xl font-semibold text-gray-800 mb-4">Add New Voice Clone</h4>
              <div className="space-y-4">
                <div>
                  <label className="block text-lg font-semibold text-gray-700 mb-2">
                    Voice Name
                  </label>
                  <input
                    type="text"
                    value={newVoice.name}
                    onChange={(e) => setNewVoice({ ...newVoice, name: e.target.value })}
                    placeholder="e.g., Grandma's Voice"
                    className="w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-lg font-semibold text-gray-700 mb-2">
                    Reference ID
                  </label>
                  <input
                    type="text"
                    value={newVoice.reference_id}
                    onChange={(e) => setNewVoice({ ...newVoice, reference_id: e.target.value })}
                    placeholder="e.g., 8ef4a238714b45718ce04243307c57a7"
                    className="w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                  <p className="text-sm text-gray-600 mt-1">
                    Get the reference_id from fish.audio voice page URL (e.g., fish.audio/m/8ef4a238714b45718ce04243307c57a7)
                  </p>
                </div>
                <div>
                  <label className="block text-lg font-semibold text-gray-700 mb-2">
                    Description (Optional)
                  </label>
                  <input
                    type="text"
                    value={newVoice.description}
                    onChange={(e) => setNewVoice({ ...newVoice, description: e.target.value })}
                    placeholder="e.g., Warm and friendly voice"
                    className="w-full px-4 py-2 text-lg border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={handleAddVoice}
                    className="button-large bg-green-600 text-white hover:bg-green-700 flex items-center gap-2"
                  >
                    <Save size={20} />
                    Save Voice
                  </button>
                  <button
                    onClick={() => {
                      setShowAddVoice(false)
                      setNewVoice({ name: '', reference_id: '', description: '' })
                    }}
                    className="button-large bg-gray-500 text-white hover:bg-gray-600"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-3">
            {voiceClones.length === 0 ? (
              <p className="text-lg text-gray-600 text-center py-8">
                No voice clones added yet. Click "Add Voice" to get started.
              </p>
            ) : (
              voiceClones.map((voice) => (
                <div
                  key={voice.id}
                  className={`p-4 rounded-lg border-2 ${
                    voice.id === activeVoiceId
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-300 bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1">
                      {voice.id === activeVoiceId ? (
                        <CheckCircle size={24} className="text-green-600" />
                      ) : (
                        <Circle size={24} className="text-gray-400" />
                      )}
                      <div className="flex-1">
                        <h4 className="text-xl font-semibold text-gray-800">{voice.name}</h4>
                        <p className="text-sm text-gray-600 font-mono">{voice.reference_id}</p>
                        {voice.description && (
                          <p className="text-base text-gray-700 mt-1">{voice.description}</p>
                        )}
                        {voice.id === activeVoiceId && (
                          <span className="inline-block mt-2 px-3 py-1 bg-green-600 text-white text-sm font-semibold rounded-full">
                            Active
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {voice.id !== activeVoiceId && (
                        <button
                          onClick={() => voice.id && handleActivateVoice(voice.id)}
                          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-semibold"
                        >
                          Activate
                        </button>
                      )}
                      <button
                        onClick={() => voice.id && handleDeleteVoice(voice.id)}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2"
                      >
                        <Trash2 size={18} />
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {voiceClones.length > 0 && (
            <div className="mt-4 p-4 bg-blue-50 border-2 border-blue-300 rounded-lg">
              <p className="text-base text-blue-800">
                <strong>Note:</strong> The active voice clone will be used for all conversations. 
                Make sure you have set FISH_AUDIO_API_KEY in your .env file.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
