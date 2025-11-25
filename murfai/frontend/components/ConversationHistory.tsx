'use client'

import { useState, useEffect } from 'react'
import { MessageSquare, User, Bot } from 'lucide-react'
import { apiClient, ConversationMessage } from '@/lib/api'
import { format } from 'date-fns'

export default function ConversationHistory() {
  const [conversations, setConversations] = useState<ConversationMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiClient.getConversations(20)
      setConversations(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load conversations')
    } finally {
      setLoading(false)
    }
  }

  const getSentimentColor = (sentiment?: string) => {
    switch (sentiment) {
      case 'happy':
        return 'bg-green-100 text-green-700 border-green-300'
      case 'sad':
        return 'bg-blue-100 text-blue-700 border-blue-300'
      case 'neutral':
        return 'bg-gray-100 text-gray-700 border-gray-300'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-300'
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <p className="text-2xl text-gray-600">Loading conversation history...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-100 border-l-4 border-red-500 p-6 rounded-lg">
        <p className="text-xl font-semibold text-red-700">Error</p>
        <p className="text-lg text-red-600">{error}</p>
        <button
          onClick={loadConversations}
          className="mt-4 button-large bg-red-600 text-white hover:bg-red-700"
        >
          Try Again
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
          <MessageSquare size={32} className="text-primary-600" />
          Conversation History
        </h2>
        <button
          onClick={loadConversations}
          className="button-large bg-primary-600 text-white hover:bg-primary-700"
        >
          Refresh
        </button>
      </div>

      {conversations.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-xl text-gray-600">No conversations yet.</p>
          <p className="text-lg text-gray-500 mt-2">Start talking in the "Talk" tab to see your history here.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {conversations.map((conv, index) => (
            <div
              key={conv.id || index}
              className="bg-white border-2 border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-sm font-semibold border ${getSentimentColor(conv.sentiment)}`}>
                    {conv.sentiment || 'neutral'}
                  </span>
                </div>
                <span className="text-lg text-gray-500">
                  {format(new Date(conv.timestamp), 'MMM d, yyyy h:mm a')}
                </span>
              </div>

              <div className="space-y-4">
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <User size={20} className="text-blue-600" />
                    <h4 className="text-xl font-semibold text-blue-800">You</h4>
                  </div>
                  <p className="text-lg text-gray-700 ml-7">{conv.user_message}</p>
                </div>

                <div className="bg-green-50 border-l-4 border-green-400 p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Bot size={20} className="text-green-600" />
                    <h4 className="text-xl font-semibold text-green-800">Companion</h4>
                  </div>
                  <p className="text-lg text-gray-700 ml-7">{conv.ai_response}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

