'use client';

import React from 'react';
import { useLanguage } from '@/contexts/LanguageContext';

export default function LanguageToggle() {
    const { language, setLanguage } = useLanguage();

    return (
        <div className="language-toggle">
            <button
                type="button"
                className={`lang-btn ${language === 'zh' ? 'active' : ''}`}
                onClick={() => setLanguage('zh')}
            >
                中文
            </button>
            <div className="lang-divider"></div>
            <button
                type="button"
                className={`lang-btn ${language === 'en' ? 'active' : ''}`}
                onClick={() => setLanguage('en')}
            >
                EN
            </button>

            <style jsx>{`
        .language-toggle {
          position: absolute;
          top: 16px;
          right: 32px;
          display: flex;
          align-items: center;
          background: var(--bg-secondary);
          border: 1px solid var(--border-light);
          border-radius: var(--radius-sm);
          padding: 2px;
          z-index: 100;
        }
        
        .lang-btn {
          background: transparent;
          border: none;
          color: var(--text-secondary);
          padding: 6px 12px;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          border-radius: calc(var(--radius-sm) - 2px);
          transition: all 0.2s;
        }

        .lang-btn:hover {
          color: var(--text-primary);
        }

        .lang-btn.active {
          background: var(--bg-hover);
          color: var(--text-primary);
          box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }

        .lang-divider {
          width: 1px;
          height: 16px;
          background: var(--border-subtle);
          margin: 0 2px;
        }
      `}</style>
        </div>
    );
}
