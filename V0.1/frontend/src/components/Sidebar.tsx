'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import {
    LayoutDashboard,
    Library,
    Languages,
    Cpu,
    Menu,
    FileVideo,
} from 'lucide-react';

const navItems = [
    { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/libraries', icon: Library, label: 'Libraries' },
    { href: '/translation', icon: Languages, label: 'Translation' },
    { href: '/manual', icon: FileVideo, label: 'Manual Generation' },
    { href: '/ai-config', icon: Cpu, label: 'AI Configuration' },
];

export default function Sidebar() {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);
    const { t } = useLanguage();

    return (
        <>
            <button
                className="hamburger-btn"
                onClick={() => setCollapsed(!collapsed)}
                style={{ left: collapsed ? 12 : `calc(var(--sidebar-width) + 12px)` }}
                aria-label="Toggle sidebar"
            >
                <Menu size={18} />
            </button>

            <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
                <div className="sidebar-header">
                    <img src="/logo.png" alt="SubMasterDC" className="sidebar-logo" />
                    <span className="sidebar-title">SubMasterDC</span>
                </div>

                <nav className="sidebar-nav">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`nav-item ${isActive ? 'active' : ''}`}
                            >
                                <Icon className="nav-icon" size={18} strokeWidth={isActive ? 2.2 : 1.8} />
                                {t(item.label)}
                            </Link>
                        );
                    })}
                </nav>
            </aside>
        </>
    );
}
