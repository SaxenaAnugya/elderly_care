'use client'

import React from 'react'
import { useSidebar } from '@/contexts/SidebarContext'

export default function SidebarContent({ children }: { children: React.ReactNode }) {
  const { isOpen } = useSidebar()
  
  return (
    <div 
      className="min-h-screen relative transition-all duration-300" 
      style={{ 
        zIndex: 1,
        marginLeft: isOpen ? '256px' : '0'
      }}
    >
      <main className="p-6">{children}</main>
    </div>
  )
}

