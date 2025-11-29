"use client"

import React, { useState } from 'react'
import Link from 'next/link'
import { Menu, X, User, MessagesSquare, Pill, Settings } from 'lucide-react'

export default function Sidebar() {
  const [open, setOpen] = useState(true)

  return (
    <>
      {/* Toggle button */}
      <button
        aria-label="Toggle sidebar"
        onClick={() => setOpen(o => !o)}
        className="fixed top-4 left-4 z-50 p-2 rounded-md bg-white/90 shadow-md backdrop-blur-sm"
      >
        {open ? <X size={20} /> : <Menu size={10} />}
      </button>

      {/* Sidebar panel */}
      <aside
        className={`fixed top-0 left-0 h-full z-40 w-64 transform transition-transform duration-300 bg-white/95 border-r shadow-xl ${open ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="h-full flex flex-col py-6">
          <div className="px-6 mb-6">
            <h2 className="text-2xl font-semibold">Your Companion</h2>
            <p className="text-sm text-gray-500">Voice-first AI for seniors</p>
          </div>

          <nav className="flex-1 px-2 space-y-1">
            <Link href="/" className="flex items-center gap-3 px-4 py-2 rounded hover:bg-gray-100">
              <User size={18} />
              <span>Companion</span>
            </Link>
            <Link href="/conversation" className="flex items-center gap-3 px-4 py-2 rounded hover:bg-gray-100">
              <MessagesSquare size={18} />
              <span>Conversation</span>
            </Link>
            <Link href="/medications" className="flex items-center gap-3 px-4 py-2 rounded hover:bg-gray-100">
              <Pill size={18} />
              <span>Medications</span>
            </Link>
            <Link href="/settings" className="flex items-center gap-3 px-4 py-2 rounded hover:bg-gray-100">
              <Settings size={18} />
              <span>Settings</span>
            </Link>
          </nav>

          <div className="px-4 py-4">
            <small className="text-xs text-gray-500">v1 • Local</small>
          </div>
        </div>
      </aside>
    </>
  )
}
