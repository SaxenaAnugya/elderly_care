"use client"

import React from 'react'
import Link from 'next/link'
import { ChevronRight, X, User, MessagesSquare, Pill, Settings } from 'lucide-react'
import { useSidebar } from '@/contexts/SidebarContext'

export default function Sidebar() {
  const { isOpen: open, setIsOpen: setOpen } = useSidebar()

  return (
    <>
      {/* Small square button to open sidebar - visible when closed */}
      {!open && (
        <button
          aria-label="Open sidebar"
          onClick={() => setOpen(true)}
          className="fixed top-4 left-4 z-50 w-10 h-10 bg-white shadow-lg border border-gray-200 hover:bg-gray-50 hover:border-primary-400 hover:shadow-xl transition-all flex items-center justify-center"
        >
          <ChevronRight size={20} className="text-gray-700" />
        </button>
      )}

      {/* Sidebar panel */}
      <aside
        className={`fixed top-0 left-0 h-full z-40 transform transition-transform duration-300 bg-white/95 border-r shadow-xl ${
          open ? 'translate-x-0 w-64' : '-translate-x-full'
        }`}
      >
        <div className="h-full flex flex-col py-6 relative">
          {/* Close button - visible when open, positioned at top-right corner */}
          {open && (
            <button
              aria-label="Close sidebar"
              onClick={() => setOpen(false)}
              className="absolute top-0 -right-9 w-7 h-7 flex items-center justify-center rounded transition-all z-50 hover:opacity-70"
            >
              <X size={18} className="text-gray-700" />
            </button>
          )}

          {/* Header - only visible when open */}
          <div className={`px-6 mb-6 mt-2 ${open ? 'block' : 'hidden'}`}>
            <h2 className="text-2xl font-semibold">Your Companion</h2>
            <p className="text-sm text-gray-500">Voice-first AI for seniors</p>
          </div>

          <nav className={`flex-1 px-2 space-y-1 ${open ? 'block' : 'hidden'}`}>
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

          <div className={`px-4 py-4 ${open ? 'block' : 'hidden'}`}>
            <small className="text-xs text-gray-500">v1 • Local</small>
          </div>
        </div>
      </aside>
    </>
  )
}
