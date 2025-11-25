'use client'

import { useState, useEffect } from 'react'
import { Plus, Clock, Check, X, Edit, Trash2 } from 'lucide-react'
import { apiClient, Medication } from '@/lib/api'
import { format } from 'date-fns'

export default function MedicationReminders() {
  const [medications, setMedications] = useState<Medication[]>([])
  const [dueMedications, setDueMedications] = useState<Medication[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  
  const [formData, setFormData] = useState({
    medication_name: '',
    time: '',
  })

  useEffect(() => {
    loadMedications()
    loadDueMedications()
    
    // Check for due medications every minute
    const interval = setInterval(() => {
      loadDueMedications()
    }, 60000)
    
    return () => clearInterval(interval)
  }, [])

  const loadMedications = async () => {
    try {
      const data = await apiClient.getMedications()
      setMedications(data)
    } catch (error) {
      console.error('Failed to load medications:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadDueMedications = async () => {
    try {
      const data = await apiClient.getMedicationsDue()
      setDueMedications(data)
    } catch (error) {
      console.error('Failed to load due medications:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    
    if (!formData.medication_name.trim() || !formData.time) {
      setError('Please fill in both medication name and time')
      return
    }
    
    setSaving(true)
    try {
      if (editingId) {
        await apiClient.updateMedication(editingId, formData)
        setSuccess('Medication updated successfully!')
        setEditingId(null)
      } else {
        const result = await apiClient.addMedication(formData)
        console.log('Medication added:', result)
        setSuccess('Medication added successfully!')
      }
      setFormData({ medication_name: '', time: '' })
      setShowAddForm(false)
      // Reload medications to show the new one
      await loadMedications()
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000)
    } catch (error: any) {
      console.error('Failed to save medication:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to save medication'
      setError(errorMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleEdit = (med: Medication) => {
    setFormData({
      medication_name: med.medication_name,
      time: med.time,
    })
    setEditingId(med.id!)
    setShowAddForm(true)
  }

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this medication?')) {
      try {
        await apiClient.deleteMedication(id)
        loadMedications()
      } catch (error) {
        console.error('Failed to delete medication:', error)
        alert('Failed to delete medication. Please try again.')
      }
    }
  }

  const markAsTaken = async (id: number) => {
    try {
      await apiClient.updateMedication(id, {
        last_taken: new Date().toISOString(),
      })
      loadMedications()
      loadDueMedications()
    } catch (error) {
      console.error('Failed to mark as taken:', error)
    }
  }

  if (loading) {
    return <div className="text-center text-2xl">Loading medications...</div>
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-800">Medication Reminders</h2>
        <button
          onClick={() => {
            setShowAddForm(!showAddForm)
            setEditingId(null)
            setFormData({ medication_name: '', time: '' })
          }}
          className="button-large bg-primary-600 text-white hover:bg-primary-700 flex items-center gap-2"
        >
          <Plus size={24} />
          {showAddForm ? 'Cancel' : 'Add Medication'}
        </button>
      </div>

      {/* Due Medications Alert */}
      {dueMedications.length > 0 && (
        <div className="bg-yellow-100 border-l-4 border-yellow-500 p-6 rounded-lg">
          <h3 className="text-2xl font-semibold text-yellow-800 mb-4">⚠️ Medications Due Now</h3>
          <div className="space-y-3">
            {dueMedications.map((med) => (
              <div key={med.id} className="bg-white p-4 rounded-lg flex items-center justify-between">
                <div>
                  <p className="text-xl font-semibold">{med.medication_name}</p>
                  <p className="text-lg text-gray-600">Due at {med.time}</p>
                </div>
                <button
                  onClick={() => med.id && markAsTaken(med.id)}
                  className="button-large bg-green-600 text-white hover:bg-green-700 flex items-center gap-2"
                >
                  <Check size={20} />
                  Mark as Taken
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className="bg-green-100 border-l-4 border-green-500 text-green-700 p-4 rounded-lg">
          <p className="text-lg font-semibold">{success}</p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-lg">
          <p className="text-lg font-semibold">Error</p>
          <p className="text-base">{error}</p>
        </div>
      )}

      {/* Add/Edit Form */}
      {showAddForm && (
        <form onSubmit={handleSubmit} className="bg-gray-50 p-6 rounded-lg space-y-4">
          <div>
            <label className="block text-xl font-semibold text-gray-700 mb-2">
              Medication Name
            </label>
            <input
              type="text"
              value={formData.medication_name}
              onChange={(e) => {
                setFormData({ ...formData, medication_name: e.target.value })
                setError(null)
              }}
              className="w-full px-4 py-3 text-xl border-2 border-gray-300 rounded-lg focus:border-primary-500 focus-visible-large"
              placeholder="e.g., Blood Pressure Pill"
              required
              disabled={saving}
            />
          </div>
          <div>
            <label className="block text-xl font-semibold text-gray-700 mb-2">
              Time (HH:MM)
            </label>
            <input
              type="time"
              value={formData.time}
              onChange={(e) => {
                setFormData({ ...formData, time: e.target.value })
                setError(null)
              }}
              className="w-full px-4 py-3 text-xl border-2 border-gray-300 rounded-lg focus:border-primary-500 focus-visible-large"
              required
              disabled={saving}
            />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="button-large bg-primary-600 text-white hover:bg-primary-700 w-full disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : (editingId ? 'Update Medication' : 'Add Medication')}
          </button>
        </form>
      )}

      {/* Medications List */}
      <div className="space-y-4">
        <h3 className="text-2xl font-semibold text-gray-800">Your Medications</h3>
        {medications.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-lg">
            <p className="text-xl text-gray-600">No medications scheduled yet.</p>
            <p className="text-lg text-gray-500 mt-2">Click "Add Medication" to get started.</p>
          </div>
        ) : (
          medications.map((med) => (
            <div
              key={med.id}
              className="bg-white border-2 border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <Clock size={24} className="text-primary-600" />
                    <h4 className="text-2xl font-semibold text-gray-800">{med.medication_name}</h4>
                  </div>
                  <p className="text-xl text-gray-600 ml-9">Time: {med.time}</p>
                  {med.last_taken && (
                    <p className="text-lg text-green-600 ml-9 mt-1">
                      Last taken: {format(new Date(med.last_taken), 'MMM d, yyyy h:mm a')}
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => med.id && markAsTaken(med.id)}
                    className="p-3 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 focus-visible-large"
                    aria-label="Mark as taken"
                  >
                    <Check size={24} />
                  </button>
                  <button
                    onClick={() => med.id && handleEdit(med)}
                    className="p-3 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 focus-visible-large"
                    aria-label="Edit"
                  >
                    <Edit size={24} />
                  </button>
                  <button
                    onClick={() => med.id && handleDelete(med.id)}
                    className="p-3 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 focus-visible-large"
                    aria-label="Delete"
                  >
                    <Trash2 size={24} />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

