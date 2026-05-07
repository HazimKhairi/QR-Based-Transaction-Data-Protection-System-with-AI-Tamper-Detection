"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { getCurrentUser, type AuthUser } from "@/lib/api";
import {
    HomeIcon,
    CreditCardIcon,
    ChartBarIcon,
    UserGroupIcon,
    DocumentTextIcon,
    Cog6ToothIcon,
    ShieldCheckIcon,
    KeyIcon,
} from "@heroicons/react/24/outline";

type NavItem = {
    label: string;
    href: string;
    icon: typeof HomeIcon;
    superAdminOnly?: boolean;
};

const navItems: NavItem[] = [
    { label: "Admin Dashboard", href: "/admin/dashboard", icon: HomeIcon },
    { label: "Transactions", href: "/admin/transactions", icon: CreditCardIcon },
    { label: "Analytics", href: "/admin/analytics", icon: ChartBarIcon },
    { label: "Residents", href: "/admin/residents", icon: UserGroupIcon },
    { label: "Admin Accounts", href: "/admin/admin-users", icon: KeyIcon, superAdminOnly: true },
    { label: "Reports", href: "/admin/reports", icon: DocumentTextIcon },
    { label: "Settings", href: "/admin/settings", icon: Cog6ToothIcon },
];

export default function Sidebar() {
    const pathname = usePathname();
    const [user, setUser] = useState<AuthUser | null>(null);

    useEffect(() => {
        setUser(getCurrentUser());
    }, []);

    const visibleItems = navItems.filter((item) => {
        if (item.superAdminOnly) return user?.role === "super_admin";
        return true;
    });

    const roleLabel =
        user?.role === "super_admin"
            ? "Super Admin"
            : user?.role === "admin"
                ? "System Admin"
                : user?.role
                    ? user.role.replace(/_/g, " ")
                    : "Loading...";

    return (
        <aside className="sidebar fixed left-0 top-0 h-screen z-50">
            {/* Logo Section */}
            <div className="sidebar-logo">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
                        <ShieldCheckIcon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <div className="font-semibold text-white">
                            {user?.role === "super_admin" ? "Super Admin" : "Admin"}
                        </div>
                        <div className="text-xs text-white/70">Encryption Transfer</div>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav className="sidebar-nav">
                {visibleItems.map((item) => {
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
                            src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(user?.email || "admin")}`}
                            alt="Admin"
                            className="w-full h-full object-cover"
                        />
                    </div>
                    <div className="min-w-0">
                        <div className="text-sm font-medium text-white truncate">
                            {user?.full_name || user?.email || "Admin"}
                        </div>
                        <div className="text-xs text-white/60 capitalize">{roleLabel}</div>
                    </div>
                </div>
            </div>
        </aside>
    );
}
