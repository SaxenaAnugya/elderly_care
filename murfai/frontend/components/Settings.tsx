'use client'

import { useState, useEffect } from 'react'
import { Save, Volume2, Clock, Heart } from 'lucide-react'
import { apiClient } from '@/lib/api'

export default function Settings() {
  const [settings, setSettings] = useState({
    volume: 80,
    speech_rate: 1.0,
    patience_mode: 2000,
    sundowning_hour: 17,
    medication_reminders_enabled: true,
    word_of_day_enabled: true,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await apiClient.getSettings()
      setSettings({ ...settings, ...data })
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      setLoading(false)
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
      </div>
    </div>
  )
}

