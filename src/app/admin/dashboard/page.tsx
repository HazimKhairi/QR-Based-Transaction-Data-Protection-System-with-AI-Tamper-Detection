"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import Header from "@/app/components/ui/Header";
import StatCard from "@/app/components/ui/StatCard";
import { CardWithHeader } from "@/app/components/ui/Card";
import { TransactionsTable } from "@/app/components/ui/DataTable";
import { StatusBadge } from "@/app/components/ui/Badge";
import Button from "@/app/components/ui/Button";
import LineChart from "@/app/components/ui/LineChart";
import DonutChart from "@/app/components/ui/DonutChart";
import {
    ChartBarIcon,
    ExclamationTriangleIcon,
    LockClosedIcon,
    ShieldCheckIcon,
} from "@heroicons/react/24/outline";

// Types
type DashboardStats = {
    total_transactions?: number;
    flagged_transactions?: number;
    users_count?: number;
    fraud_alerts?: number;
    secured_qr?: number;
    encryption_enabled?: boolean;
};

type Transaction = {
    id?: number;
    transaction_ref?: string;
    amount?: number;
    currency?: string;
    status?: string;
    is_flagged?: boolean;
    created_at?: string;
    resident?: string;
    name?: string;
    date?: string;
};

type FraudAlert = {
    id?: number;
    resident?: string;
    reason?: string;
    transaction_ref?: string;
    created_at?: string;
};

export default function AdminDashboard() {
    const router = useRouter();
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [alerts, setAlerts] = useState<FraudAlert[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                // Fetch dashboard stats
                const dashRes = await apiFetch<any>("/api/admin/dashboard");
                const dash = dashRes?.dashboard || dashRes;
                setStats({
                    total_transactions: dash?.transactions?.total ?? dashRes?.total_transactions ?? 0,
                    flagged_transactions: dash?.transactions?.flagged ?? dash?.security?.anomalies_month ?? 0,
                    users_count: dash?.users?.total ?? dashRes?.users_count ?? 0,
                    secured_qr: dash?.transactions?.completed ?? dash?.secured_qr ?? 0,
                    encryption_enabled: true, // AES is always enabled
                });

                // Fetch transactions
                const txRes = await apiFetch<any>("/api/admin/transactions?per_page=4");
                const txList = txRes?.transactions || txRes?.items || [];
                setTransactions(
                    txList.slice(0, 4).map((tx: any) => ({
                        id: tx.id,
                        resident: tx.resident_name || tx.user || "Resident",
                        name: tx.description || tx.name || "Payment",
                        date: tx.created_at ? new Date(tx.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "--:--",
                        amount: tx.amount,
                        status: tx.is_flagged ? "Failed" : tx.status || "Successful",
                    }))
                );

                // Fetch fraud alerts (only anomalies)
                const alertRes = await apiFetch<any>("/api/admin/tamper-detections?anomalies_only=true&per_page=10");
                setAlerts(
                    (alertRes?.detections || []).slice(0, 3).map((a: any) => ({
                        id: a.id,
                        resident: `Transaction #${a.transaction_id}`,
                        reason: a.detection_type
                            ? `${a.detection_type.replace(/_/g, ' ')} (score ${Number(a.anomaly_score).toFixed(2)})`
                            : "QR Code Tampering Detected",
                        transaction_ref: String(a.transaction_id),
                        created_at: a.detected_at,
                    }))
                );
            } catch (err: any) {
                setError(err.message);
                // Set fallback data for demo
                setStats({
                    total_transactions: 0,
                    flagged_transactions: 0,
                    secured_qr: 0,
                    encryption_enabled: true,
                });
                setTransactions([
                    { resident: "Nuraisha Saiful", name: "Water Bill", date: "09:24", amount: 25.40, status: "Successful" },
                    { resident: "Acfir in Sertani", name: "Maintenance", date: "08:45", amount: 50.00, status: "Pending" },
                    { resident: "Ali W. Mohen", name: "Parking", date: "10:05", amount: 27.00, status: "Failed" },
                    { resident: "Rohaya Saiful", name: "Security Fee", date: "10:22", amount: 120.00, status: "Failed" },
                ]);
                setAlerts([
                    { resident: "Lnessa, Kalisa", reason: "QR Code Tampering Detected" },
                    { resident: "Althda, Fathri", reason: "QR Code Tampering Detected" },
                    { resident: "Tawi, Atika", reason: "QR Code Tampering Detected" },
                ]);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    return (
        <div className="animate-fadeIn">
            {/* Header */}
            <Header title="Admin Dashboard" />

            {/* Error Banner */}
            {error && (
                <div className="mb-6 p-4 rounded-xl bg-[var(--warning-soft)] text-[var(--text-main)] text-sm">
                    <strong>Note:</strong> Using demo data. Backend connection: {error}
                </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <StatCard
                    title="Total Transactions"
                    value={stats?.total_transactions?.toLocaleString() ?? "---"}
                    variant="primary"
                    icon={<ChartBarIcon className="w-6 h-6 text-white" />}
                />
                <StatCard
                    title="Fraud Alerts"
                    value={String(stats?.flagged_transactions ?? "---")}
                    variant="danger"
                    icon={<ExclamationTriangleIcon className="w-6 h-6 text-white" />}
                />
                <StatCard
                    title="Secured QR"
                    value={String(stats?.secured_qr ?? "---")}
                    variant="warning"
                    icon={<LockClosedIcon className="w-6 h-6 text-white" />}
                />
                <StatCard
                    title="System Encryption"
                    value={stats?.encryption_enabled ? "AES Enabled" : "Disabled"}
                    variant="success"
                    icon={<ShieldCheckIcon className="w-6 h-6 text-white" />}
                />
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
                {/* Transactions Table */}
                <CardWithHeader
                    title="Transactions"
                    action={
                        <a href="/admin/transactions" className="text-sm font-medium text-[var(--primary)] hover:underline">
                            View All →
                        </a>
                    }
                    className="xl:col-span-2"
                >
                    <TransactionsTable
                        data={transactions}
                        loading={loading}
                    />
                </CardWithHeader>

                {/* Fraud Alerts Panel */}
                <CardWithHeader
                    title="Fraud Alerts"
                    action={
                        <span className="badge badge-danger text-xs">{alerts.length} alerts</span>
                    }
                >
                    <div className="space-y-4">
                        {loading ? (
                            <div className="text-center py-8 text-[var(--text-muted)]">Loading...</div>
                        ) : alerts.length === 0 ? (
                            <div className="text-center py-8 text-[var(--text-muted)]">No fraud alerts</div>
                        ) : (
                            alerts.map((alert, i) => (
                                <div key={i} className="flex items-start justify-between gap-3 p-3 rounded-lg bg-[var(--background)] hover:bg-[var(--danger-soft)] transition-colors">
                                    <div className="flex items-start gap-3">
                                        <div className="w-10 h-10 rounded-full bg-[var(--danger-soft)] flex items-center justify-center flex-shrink-0">
                                            <ExclamationTriangleIcon className="w-5 h-5 text-[var(--danger)]" />
                                        </div>
                                        <div>
                                            <div className="font-medium text-sm">{alert.resident}</div>
                                            <div className="text-xs text-[var(--danger)]">{alert.reason}</div>
                                        </div>
                                    </div>
                                    <Button
                                        variant="danger"
                                        size="sm"
                                        onClick={() =>
                                            router.push(
                                                `/admin/transactions?id=${alert.transaction_ref}`
                                            )
                                        }
                                    >
                                        Review
                                    </Button>
                                </div>
                            ))
                        )}
                    </div>
                    {alerts.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-[var(--border-soft)]">
                            <Button
                                variant="ghost"
                                fullWidth
                                onClick={() => router.push("/admin/transactions?flagged=1")}
                            >
                                View All Alerts →
                            </Button>
                        </div>
                    )}
                </CardWithHeader>
            </div>

            {/* Analytics Section */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                {/* Transaction Overview Chart */}
                <CardWithHeader
                    title="Transaction Overview"
                    action={
                        <span className="text-xs font-medium text-[var(--success)] flex items-center gap-1">
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clipRule="evenodd" />
                            </svg>
                            85% Growth
                        </span>
                    }
                    className="xl:col-span-2"
                >
                    <LineChart
                        data={[100, 120, 115, 140, 135, 160, 155, 180]}
                        height={180}
                        showGrowth={false}
                    />
                </CardWithHeader>

                {/* Encryption Activity Chart */}
                <CardWithHeader title="Encryption Activity">
                    <DonutChart
                        percentage={85}
                        label="AES Encryption"
                        sublabel="Growth"
                    />
                </CardWithHeader>
            </div>
        </div>
    );
}
