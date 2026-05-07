"use client";

import { ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, getUserRole, defaultLandingFor } from "@/lib/api";

export default function ResidentLayout({
    children,
}: {
    children: ReactNode;
}) {
    const router = useRouter();
    const [authorized, setAuthorized] = useState(false);

    useEffect(() => {
        if (!isAuthenticated()) {
            router.replace("/login");
            return;
        }
        const role = getUserRole();
        if (role !== "resident") {
            // Admin/super_admin shouldn't see the resident-only flow
            router.replace(defaultLandingFor(role));
            return;
        }
        setAuthorized(true);
    }, [router]);

    return (
        <div className="min-h-screen bg-gradient-to-br from-[var(--primary-dark)] via-[var(--primary)] to-[var(--primary-light)] flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                {authorized ? (
                    children
                ) : (
                    <div className="flex items-center justify-center gap-3 text-white/80 text-sm">
                        <svg
                            className="animate-spin w-5 h-5"
                            viewBox="0 0 24 24"
                            fill="none"
                            aria-hidden="true"
                        >
                            <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                            />
                            <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                            />
                        </svg>
                        <span>Loading your account…</span>
                    </div>
                )}
            </div>
        </div>
    );
}
