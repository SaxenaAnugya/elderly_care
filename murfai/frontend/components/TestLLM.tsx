'use client'

import { useState } from 'react'
import { TestTube, Send } from 'lucide-react'
import { apiClient } from '@/lib/api'

export default function TestLLM() {
  const [message, setMessage] = useState('Hello, how are you?')
  const [response, setResponse] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const testLLM = async () => {
    try {
      setLoading(true)
      setError(null)
      setResponse(null)

      const result = await apiClient.testLLM(message)
      setResponse(result)
    } catch (err: any) {
      setError(err.message || 'Failed to test LLM')
      console.error('LLM test error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 p-6 bg-white rounded-lg border-2 border-gray-200">
      <div className="flex items-center gap-3 mb-4">
        <TestTube size={24} className="text-primary-600" />
        <h3 className="text-2xl font-semibold text-gray-800">Test LLM Integration</h3>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-xl font-semibold text-gray-700 mb-2">
            Test Message
          </label>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="w-full px-4 py-3 text-xl border-2 border-gray-300 rounded-lg focus:border-primary-500 focus-visible-large"
            placeholder="Enter a test message..."
          />
        </div>

        <button
          onClick={testLLM}
          disabled={loading || !message.trim()}
          className="button-large bg-primary-600 text-white hover:bg-primary-700 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send size={20} />
          {loading ? 'Testing...' : 'Test LLM'}
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-lg">
          <p className="text-lg font-semibold">Error</p>
          <p className="text-base">{error}</p>
        </div>
      )}

      {response && (
        <div className="space-y-4">
          <div className="bg-green-100 border-l-4 border-green-500 text-green-700 p-4 rounded-lg">
            <p className="text-lg font-semibold">Status: {response.status}</p>
            {response.provider && <p className="text-base">Provider: {response.provider}</p>}
          </div>

          {response.input && (
            <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4">
              <h4 className="text-xl font-semibold text-blue-800 mb-2">Input:</h4>
              <p className="text-lg text-gray-700">{response.input}</p>
            </div>
          )}

          {response.sentiment && (
            <div className="bg-purple-50 border-2 border-purple-200 rounded-lg p-4">
              <h4 className="text-xl font-semibold text-purple-800 mb-2">Sentiment:</h4>
              <p className="text-lg text-gray-700">{response.sentiment}</p>
            </div>
          )}

          {response.response && (
            <div className="bg-green-50 border-2 border-green-200 rounded-lg p-4">
              <h4 className="text-xl font-semibold text-green-800 mb-2">LLM Response:</h4>
              <p className="text-lg text-gray-700">{response.response}</p>
            </div>
          )}

          {response.error && (
            <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
              <h4 className="text-xl font-semibold text-red-800 mb-2">Error:</h4>
              <p className="text-lg text-gray-700">{response.error}</p>
              {response.message && <p className="text-base text-gray-600 mt-2">{response.message}</p>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

