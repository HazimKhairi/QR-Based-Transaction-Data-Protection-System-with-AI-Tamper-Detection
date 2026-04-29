"use client";

import { useState, useRef, useEffect } from "react";
import { BellIcon, MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import { apiFetch } from "@/lib/api";

type TamperItem = {
    id?: number;
    transaction_ref?: string;
    reason?: string;
    created_at?: string;
    resident?: string;
};

interface HeaderProps {
    title: string;
    subtitle?: string;
    description?: string;
}

export default function Header({
    title,
    subtitle = "Secure QR-Based Transaction System",
    description = "Using AES Encryption & AI-Based Fraud Detection"
}: HeaderProps) {
    const [notifOpen, setNotifOpen] = useState(false);
    const [alerts, setAlerts] = useState<TamperItem[]>([]);
    const notifRef = useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
                setNotifOpen(false);
            }
        };
        document.addEventListener("click", handleClickOutside);
        return () => document.removeEventListener("click", handleClickOutside);
    }, []);

    // Fetch alerts when dropdown opens
    useEffect(() => {
        if (!notifOpen) return;
        (async () => {
            try {
                const res = await apiFetch<{ items?: TamperItem[] }>("/api/admin/tamper-detections");
                setAlerts(res.items || []);
            } catch {
                setAlerts([]);
            }
        })();
    }, [notifOpen]);

    return (
        <header className="flex items-start justify-between mb-6">
            {/* Title Section */}
            <div>
                <h1 className="text-2xl font-bold text-[var(--text-main)]">{title}</h1>
                <p className="text-sm font-medium text-[var(--primary)] mt-1">{subtitle}</p>
                <p className="text-xs text-[var(--text-muted)]">{description}</p>
            </div>

            {/* Right Section */}
            <div className="flex items-center gap-4">
                {/* AES Indicator */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--primary-soft)] text-[var(--primary)] text-sm font-medium">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
                    </svg>
                    AES
                </div>

                {/* Search */}
                <div className="relative hidden md:block">
                    <MagnifyingGlassIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                    <input
                        type="text"
                        placeholder="Search..."
                        className="input pl-10 py-2 w-48 text-sm"
                    />
                </div>

                {/* Notifications */}
                <div className="relative" ref={notifRef}>
                    <button
                        onClick={() => setNotifOpen((v) => !v)}
                        className="relative w-10 h-10 rounded-full bg-white border border-[var(--border-soft)] flex items-center justify-center hover:bg-[var(--background)] transition-colors"
                    >
                        <BellIcon className="w-5 h-5 text-[var(--text-muted)]" />
                        {alerts.length > 0 && (
                            <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[var(--danger)] text-white text-xs flex items-center justify-center font-medium">
                                {Math.min(9, alerts.length)}
                            </span>
                        )}
                    </button>

                    {/* Notifications Dropdown */}
                    {notifOpen && (
                        <div className="absolute right-0 mt-2 w-80 card animate-fadeIn z-50">
                            <div className="card-header flex items-center justify-between">
                                <span>Fraud Alerts</span>
                                <span className="badge badge-danger text-xs">
                                    {alerts.length} new
                                </span>
                            </div>
                            <div className="max-h-72 overflow-y-auto">
                                {alerts.length === 0 ? (
                                    <div className="p-4 text-center text-sm text-[var(--text-muted)]">
                                        No recent alerts
                                    </div>
                                ) : (
                                    alerts.map((alert, i) => (
                                        <div key={i} className="px-4 py-3 border-b border-[var(--border-soft)] last:border-0 hover:bg-[var(--background)]">
                                            <div className="flex items-start justify-between gap-2">
                                                <div>
                                                    <div className="font-medium text-sm">{alert.resident || "Unknown"}</div>
                                                    <div className="text-xs text-[var(--danger)]">{alert.reason || "QR Code Tampering Detected"}</div>
                                                    {alert.transaction_ref && (
                                                        <div className="text-xs text-[var(--text-muted)] mt-1">Ref: {alert.transaction_ref}</div>
                                                    )}
                                                </div>
                                                <button className="btn btn-danger text-xs py-1 px-2">
                                                    Review
                                                </button>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                            <div className="p-3 border-t border-[var(--border-soft)]">
                                <button className="btn btn-ghost w-full text-sm">
                                    View All Alerts
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* User Avatar */}
                <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-[var(--primary-soft)]">
                    <img
                        src="https://api.dicebear.com/7.x/avataaars/svg?seed=admin"
                        alt="User"
                        className="w-full h-full object-cover"
                    />
                </div>
            </div>
        </header>
    );
}
