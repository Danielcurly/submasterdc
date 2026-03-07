import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import { LanguageProvider } from '@/contexts/LanguageContext';
import LanguageToggle from '@/components/LanguageToggle';
import DebugPanel from '@/components/DebugPanel';
import { Toaster } from 'react-hot-toast';
export const metadata: Metadata = {
  title: 'SubMasterDC — NAS Subtitle Manager',
  description: 'Automated subtitle extraction, translation, and management for your NAS media library.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <LanguageProvider>
          <div className="app-layout">
            <Sidebar />
            <main className="main-content" style={{ position: 'relative' }}>
              <LanguageToggle />
              <DebugPanel />
              <Toaster position="bottom-right" toastOptions={{ style: { background: '#1f2937', color: '#fff', border: '1px solid #374151' } }} />
              {children}
            </main>
          </div>
        </LanguageProvider>
      </body>
    </html>
  );
}
