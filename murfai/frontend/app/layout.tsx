import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Sidebar from '@/components/Sidebar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Loneliness Companion - Your Caring AI Friend',
  description: 'A voice-first AI companion for elderly care',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Sidebar />
        <div className="min-h-screen">
          {/* Main content will sit under the fixed sidebar (sidebar overlays content when open) */}
          <main className="p-6">{children}</main>
        </div>
      </body>
    </html>
  )
}

