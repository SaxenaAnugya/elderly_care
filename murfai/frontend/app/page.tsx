'use client'

import { useState, useEffect } from 'react'
import VoiceInterface from '@/components/VoiceInterface'
import MedicationReminders from '@/components/MedicationReminders'
import WordOfDay from '@/components/WordOfDay'
import ConversationHistory from '@/components/ConversationHistory'
import Settings from '@/components/Settings'
import TestLLM from '@/components/TestLLM'
import { Mic, Pill, Book, MessageSquare, Settings as SettingsIcon, TestTube } from 'lucide-react'

type Tab = 'voice' | 'medications' | 'word' | 'history' | 'settings' | 'test'

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('voice')
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    // Check API connection on mount
    checkConnection()
  }, [])

  const checkConnection = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`)
      setIsConnected(response.ok)
    } catch (error) {
      setIsConnected(false)
    }
  }

  const tabs = [
    { id: 'voice' as Tab, label: 'Talk', icon: Mic, component: VoiceInterface },
    { id: 'medications' as Tab, label: 'Medications', icon: Pill, component: MedicationReminders },
    { id: 'word' as Tab, label: 'Word of Day', icon: Book, component: WordOfDay },
    { id: 'history' as Tab, label: 'History', icon: MessageSquare, component: ConversationHistory },
    { id: 'settings' as Tab, label: 'Settings', icon: SettingsIcon, component: Settings },
    { id: 'test' as Tab, label: 'Test LLM', icon: TestTube, component: TestLLM },
  ]

  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component || VoiceInterface

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-md py-6 px-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-4xl font-bold text-primary-700 text-center">
            Loneliness Companion
          </h1>
          <p className="text-xl text-gray-600 text-center mt-2">
            Your caring AI friend
          </p>
          {!isConnected && (
            <div className="mt-4 bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 rounded">
              <p className="text-lg font-semibold">⚠️ Not connected to server</p>
              <p className="text-base">Please check your connection</p>
            </div>
          )}
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b-4 border-primary-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex flex-wrap justify-center gap-2 py-4">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center gap-3 px-6 py-4 rounded-lg font-semibold text-xl
                    transition-all duration-200
                    ${activeTab === tab.id
                      ? 'bg-primary-600 text-white shadow-lg transform scale-105'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }
                    focus-visible-large
                    button-large
                  `}
                  aria-label={tab.label}
                >
                  <Icon size={28} />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-xl p-8 min-h-[600px]">
          <ActiveComponent />
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-800 text-white py-6 mt-8">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-lg">Made with ❤️ for elderly care</p>
        </div>
      </footer>
    </main>
  )
}

