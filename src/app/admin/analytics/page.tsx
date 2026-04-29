"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import Header from "@/app/components/ui/Header";
import { CardWithHeader } from "@/app/components/ui/Card";
import LineChart from "@/app/components/ui/LineChart";
import DonutChart from "@/app/components/ui/DonutChart";
import StatCard from "@/app/components/ui/StatCard";
import {
    ArrowTrendingUpIcon,
    CurrencyDollarIcon,
    UserGroupIcon,
    ShieldCheckIcon,
    ClockIcon,
    ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";

type DashboardData = {
    users: { total: number; active: number; new_this_week: number };
    transactions: { total: number; completed: number; pending: number; flagged: number; today: number; total_value: number };
    security: { recent_events: number; anomalies_month: number };
};

type TopResident = {
    id: number;
    name: string;
    email: string;
    transactions: number;
    total_amount: number;
};

export default function AnalyticsPage() {
    const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
    const [topResidents, setTopResidents] = useState<TopResident[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);

                const dashRes = await apiFetch<any>("/api/admin/dashboard");
                setDashboardData(dashRes?.dashboard || null);

                const usersRes = await apiFetch<any>("/api/admin/users?role=resident&per_page=5");
                const users = usersRes?.users || [];

                // Fetch per-user stats in parallel from admin user-detail endpoint
                const enriched = await Promise.all(
                    users.map(async (u: any) => {
                        try {
                            const detail = await apiFetch<any>(`/api/admin/users/${u.id}`);
                            const stats = detail?.statistics || {};
                            return {
                                id: u.id,
                                name: u.full_name || u.name || "Unknown",
                                email: u.email,
                                transactions: stats.total_transactions ?? stats.total_count ?? 0,
                                total_amount: stats.total_amount ?? 0,
                            };
                        } catch {
                            return {
                                id: u.id,
                                name: u.full_name || u.name || "Unknown",
                                email: u.email,
                                transactions: 0,
                                total_amount: 0,
                            };
                        }
                    })
                );

                // Sort by transaction count, descending
                enriched.sort((a, b) => b.transactions - a.transactions);
                setTopResidents(enriched);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const successRate = dashboardData
        ? Math.round((dashboardData.transactions.completed / Math.max(dashboardData.transactions.total, 1)) * 100)
        : 0;

    return (
        <div className="animate-fadeIn">
            <Header
                title="Analytics"
                subtitle="Performance Metrics"
                description="View detailed analytics and insights"
            />

            {error && (
                <div className="mb-6 p-4 rounded-xl bg-[var(--danger-soft)] text-[var(--danger)] text-sm">
                    Error loading analytics: {error}
                </div>
            )}

            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <StatCard
                    title="Total Revenue"
                    value={loading ? "..." : `RM ${dashboardData?.transactions.total_value?.toLocaleString() || 0}`}
                    variant="primary"
                    icon={<CurrencyDollarIcon className="w-6 h-6 text-white" />}
                    trend={{ value: "+12.5%", positive: true }}
                />
                <StatCard
                    title="Active Users"
                    value={loading ? "..." : String(dashboardData?.users.active || 0)}
                    variant="success"
                    icon={<UserGroupIcon className="w-6 h-6 text-white" />}
                    trend={{ value: "+5.2%", positive: true }}
                />
                <StatCard
                    title="Success Rate"
                    value={loading ? "..." : `${successRate}%`}
                    variant="warning"
                    icon={<ShieldCheckIcon className="w-6 h-6 text-white" />}
                />
                <StatCard
                    title="Avg. Response Time"
                    value="0.8s"
                    variant="primary"
                    icon={<ClockIcon className="w-6 h-6 text-white" />}
                />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
                <CardWithHeader
                    title="Transaction Volume"
                    action={
                        <select className="text-sm border border-[var(--border-soft)] rounded px-2 py-1">
                            <option>Last 7 Days</option>
                            <option>Last 30 Days</option>
                            <option>Last 90 Days</option>
                        </select>
                    }
                    className="xl:col-span-2"
                >
                    <LineChart
                        data={[45, 52, 38, 65, 48, 72, 55, 80]}
                        height={200}
                        showGrowth={true}
                    />
                </CardWithHeader>

                <CardWithHeader title="Payment Methods">
                    <div className="space-y-4">
                        <DonutChart
                            percentage={successRate}
                            label="QR Payments"
                            sublabel="Success Rate"
                        />
                        <div className="grid grid-cols-2 gap-4 text-center pt-4 border-t border-[var(--border-soft)]">
                            <div>
                                <div className="text-2xl font-bold text-[var(--primary)]">
                                    {dashboardData?.transactions.completed || 0}
                                </div>
                                <div className="text-xs text-[var(--text-muted)]">Completed</div>
                            </div>
                            <div>
                                <div className="text-2xl font-bold text-[var(--warning)]">
                                    {dashboardData?.transactions.pending || 0}
                                </div>
                                <div className="text-xs text-[var(--text-muted)]">Pending</div>
                            </div>
                        </div>
                    </div>
                </CardWithHeader>
            </div>

            {/* Bottom Row */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                {/* Top Performing Residents */}
                <CardWithHeader title="Top Performing Residents">
                    {loading ? (
                        <div className="text-center py-8 text-[var(--text-muted)]">Loading...</div>
                    ) : (
                        <div className="space-y-4">
                            {topResidents.map((resident, i) => (
                                <div key={resident.id} className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-[var(--primary-soft)] flex items-center justify-center text-sm font-semibold text-[var(--primary)]">
                                            {i + 1}
                                        </div>
                                        <div>
                                            <div className="font-medium">{resident.name}</div>
                                            <div className="text-xs text-[var(--text-muted)]">{resident.email}</div>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className="font-semibold">RM {resident.total_amount.toLocaleString()}</div>
                                        <div className="text-xs text-[var(--text-muted)]">{resident.transactions} transactions</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardWithHeader>

                {/* Security Overview */}
                <CardWithHeader title="Security Overview">
                    <div className="space-y-4">
                        <div className="flex items-center justify-between p-4 rounded-xl bg-[var(--success-soft)]">
                            <div className="flex items-center gap-3">
                                <ShieldCheckIcon className="w-8 h-8 text-[var(--success)]" />
                                <div>
                                    <div className="font-semibold">AES-256 Encryption</div>
                                    <div className="text-sm text-[var(--text-muted)]">All transactions encrypted</div>
                                </div>
                            </div>
                            <span className="badge badge-success">Active</span>
                        </div>
                        <div className="flex items-center justify-between p-4 rounded-xl bg-[var(--primary-soft)]">
                            <div className="flex items-center gap-3">
                                <ShieldCheckIcon className="w-8 h-8 text-[var(--primary)]" />
                                <div>
                                    <div className="font-semibold">AI Tamper Detection</div>
                                    <div className="text-sm text-[var(--text-muted)]">Isolation Forest model</div>
                                </div>
                            </div>
                            <span className="badge badge-primary">Active</span>
                        </div>
                        <div className="flex items-center justify-between p-4 rounded-xl bg-[var(--warning-soft)]">
                            <div className="flex items-center gap-3">
                                <ExclamationTriangleIcon className="w-8 h-8 text-[var(--warning)]" />
                                <div>
                                    <div className="font-semibold">Anomalies Detected</div>
                                    <div className="text-sm text-[var(--text-muted)]">Last 30 days</div>
                                </div>
                            </div>
                            <span className="text-2xl font-bold text-[var(--warning)]">
                                {dashboardData?.security.anomalies_month || 0}
                            </span>
                        </div>
                    </div>
                </CardWithHeader>
            </div>
        </div>
    );
}
