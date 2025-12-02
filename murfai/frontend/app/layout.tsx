import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import { SidebarProvider } from '@/contexts/SidebarContext'
import SidebarContent from '@/components/SidebarContent'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: ' Nivara : Your Wellness, Gently Managed',
  description: 'A voice-first AI companion for elderly safe space',
  icons: {
    icon: [
      { url: '/logo.svg', type: 'image/svg+xml' },
    ],
    shortcut: '/logo.svg',
    apple: '/logo.svg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className} style={{ position: 'relative' }}>
        <SidebarProvider>
          {/* Background image - lowest layer */}
          <div 
            className="fixed inset-0 bg-cover bg-center bg-no-repeat"
            style={{ 
              backgroundImage: 'url(/bg-image.jpg)',
              opacity: 0.30,
              zIndex: -1,
              pointerEvents: 'none'
            }}
          />
          <Sidebar />
          <SidebarContent>{children}</SidebarContent>
        </SidebarProvider>
      </body>
    </html>
  )
}

