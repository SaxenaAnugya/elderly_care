'use client'

import { useState, useEffect } from 'react'
import { Book, RefreshCw } from 'lucide-react'
import { apiClient, WordOfDay } from '@/lib/api'

export default function WordOfDayComponent() {
  const [word, setWord] = useState<WordOfDay | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadWord()
  }, [])

  const loadWord = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiClient.getWordOfDay()
      setWord(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load word of the day')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <p className="text-2xl text-gray-600">Loading word of the day...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-100 border-l-4 border-red-500 p-6 rounded-lg">
        <p className="text-xl font-semibold text-red-700">Error</p>
        <p className="text-lg text-red-600">{error}</p>
        <button
          onClick={loadWord}
          className="mt-4 button-large bg-red-600 text-white hover:bg-red-700"
        >
          Try Again
        </button>
      </div>
    )
  }

  if (!word) {
    return (
      <div className="text-center py-12">
        <p className="text-xl text-gray-600">No word available</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
          <Book size={32} className="text-primary-600" />
          Word of the Day
        </h2>
        <button
          onClick={loadWord}
          className="button-large bg-primary-600 text-white hover:bg-primary-700 flex items-center gap-2"
        >
          <RefreshCw size={20} />
          New Word
        </button>
      </div>

      <div className="bg-gradient-to-br from-purple-50 to-blue-50 border-4 border-primary-300 rounded-2xl p-8 shadow-xl">
        <div className="text-center mb-6">
          <h3 className="text-5xl font-bold text-primary-700 mb-4">{word.word}</h3>
          <div className="w-24 h-1 bg-primary-500 mx-auto rounded"></div>
        </div>

        <div className="bg-white rounded-lg p-6 mb-6">
          <h4 className="text-2xl font-semibold text-gray-800 mb-3">Definition</h4>
          <p className="text-xl text-gray-700 leading-relaxed">{word.definition}</p>
        </div>

        <div className="bg-white rounded-lg p-6 mb-6">
          <h4 className="text-2xl font-semibold text-gray-800 mb-3">Question for You</h4>
          <p className="text-xl text-gray-700 leading-relaxed italic">"{word.prompt}"</p>
        </div>

        <div className="bg-primary-100 rounded-lg p-6">
          <h4 className="text-2xl font-semibold text-primary-800 mb-3">💭 Think About It</h4>
          <p className="text-xl text-primary-700 leading-relaxed">{word.follow_up}</p>
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-6">
        <h4 className="text-2xl font-semibold text-gray-800 mb-3">How to Use</h4>
        <ol className="list-decimal list-inside space-y-2 text-lg text-gray-700">
          <li>Read the word and its definition</li>
          <li>Think about the question</li>
          <li>Share your thoughts with the companion in the "Talk" tab</li>
          <li>Click "New Word" to get another word anytime</li>
        </ol>
      </div>
    </div>
  )
}

