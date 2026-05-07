"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, getUserRole, defaultLandingFor } from "@/lib/api";
import Sidebar from "@/app/components/ui/Sidebar";

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();
    const [authorized, setAuthorized] = useState(false);

    useEffect(() => {
        if (!isAuthenticated()) {
            router.replace("/login");
            return;
        }
        const role = getUserRole();
        if (role !== "admin" && role !== "super_admin") {
            // Logged in but not allowed here — bounce to their proper landing
            router.replace(defaultLandingFor(role));
            return;
        }
        setAuthorized(true);
    }, [router]);

    if (!authorized) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[var(--background)] text-[var(--text-muted)] text-sm">
                Checking access...
            </div>
        );
    }

    return (
        <div className="flex min-h-screen bg-[var(--background)]">
            {/* Fixed Sidebar */}
            <Sidebar />

            {/* Main Content Area */}
            <main className="flex-1 ml-[260px]">
                <div className="p-8 max-w-[1400px]">
                    {children}
                </div>
            </main>
        </div>
    );
}
