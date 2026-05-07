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

    if (!authorized) {
        return (
            <div className="min-h-screen flex items-center justify-center text-white text-sm">
                Checking access...
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-[var(--primary-dark)] via-[var(--primary)] to-[var(--primary-light)] flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                {children}
            </div>
        </div>
    );
}
