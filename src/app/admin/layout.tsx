"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/api";
import Sidebar from "@/app/components/ui/Sidebar";

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();

    useEffect(() => {
        // Check authentication on mount
        if (!isAuthenticated()) {
            router.push("/login");
        }
    }, [router]);

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
