"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    HomeIcon,
    CreditCardIcon,
    ChartBarIcon,
    UserGroupIcon,
    DocumentTextIcon,
    Cog6ToothIcon,
    ShieldCheckIcon,
} from "@heroicons/react/24/outline";

const navItems = [
    { label: "Admin Dashboard", href: "/admin/dashboard", icon: HomeIcon },
    { label: "Transactions", href: "/admin/transactions", icon: CreditCardIcon },
    { label: "Analytics", href: "/admin/analytics", icon: ChartBarIcon },
    { label: "Residents", href: "/admin/residents", icon: UserGroupIcon },
    { label: "Reports", href: "/admin/reports", icon: DocumentTextIcon },
    { label: "Settings", href: "/admin/settings", icon: Cog6ToothIcon },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="sidebar fixed left-0 top-0 h-screen z-50">
            {/* Logo Section */}
            <div className="sidebar-logo">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
                        <ShieldCheckIcon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <div className="font-semibold text-white">Admin</div>
                        <div className="text-xs text-white/70">Encryption Transfer</div>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav className="sidebar-nav">
                {navItems.map((item) => {
                    const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                    const Icon = item.icon;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`sidebar-item ${isActive ? "active" : ""}`}
                        >
                            <Icon className="w-5 h-5" />
                            <span>{item.label}</span>
                        </Link>
                    );
                })}
            </nav>

            {/* User Profile Footer */}
            <div className="sidebar-footer">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center overflow-hidden">
                        <img
                            src="https://api.dicebear.com/7.x/avataaars/svg?seed=admin"
                            alt="Admin"
                            className="w-full h-full object-cover"
                        />
                    </div>
                    <div>
                        <div className="text-sm font-medium text-white">Nuraisha Saiful</div>
                        <div className="text-xs text-white/60">System Admin</div>
                    </div>
                </div>
            </div>
        </aside>
    );
}
