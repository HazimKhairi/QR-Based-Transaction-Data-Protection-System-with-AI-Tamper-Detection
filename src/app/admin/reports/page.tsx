"use client";

import { useState } from "react";
import Header from "@/app/components/ui/Header";
import { CardWithHeader } from "@/app/components/ui/Card";
import Button from "@/app/components/ui/Button";
import {
    DocumentArrowDownIcon,
    DocumentTextIcon,
    CalendarIcon,
    ChartBarIcon,
} from "@heroicons/react/24/outline";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";

export default function ReportsPage() {
    const [downloading, setDownloading] = useState<string | null>(null);

    const handleDownload = async (reportType: string, format: string = 'json') => {
        try {
            setDownloading(reportType);
            const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

            let endpoint = '';
            let filename = '';

            switch (reportType) {
                case 'transactions':
                    endpoint = `/api/admin/reports/transactions?format=${format}`;
                    filename = `transactions_report.${format}`;
                    break;
                case 'security':
                    endpoint = `/api/admin/reports/security`;
                    filename = `security_report.json`;
                    break;
                default:
                    endpoint = `/api/admin/reports/transactions?format=json`;
                    filename = `report.json`;
            }

            const response = await fetch(`${BACKEND_URL}${endpoint}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (!response.ok) {
                throw new Error('Failed to download report');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Download error:', error);
            alert('Failed to download report. Please try again.');
        } finally {
            setDownloading(null);
        }
    };

    const reports = [
        {
            id: 'transactions',
            title: "Monthly Transaction Report",
            description: "Complete overview of all transactions from the database",
            type: "Transactions",
            date: new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
            formats: ['json', 'csv'],
        },
        {
            id: 'security',
            title: "Security Audit Log",
            description: "System security events and audit trail",
            type: "Security",
            date: new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
            formats: ['json'],
        },
    ];

    return (
        <div className="animate-fadeIn">
            <Header
                title="Reports"
                subtitle="System Reports"
                description="Download and review real-time system reports"
            />

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <button
                    onClick={() => handleDownload('transactions', 'json')}
                    className="card card-body text-left hover:border-[var(--primary)] hover:shadow-md transition-all group"
                >
                    <DocumentTextIcon className="w-8 h-8 text-[var(--primary)] mb-2 group-hover:scale-110 transition-transform" />
                    <div className="font-semibold">Generate Report</div>
                    <div className="text-sm text-[var(--text-muted)]">Download JSON report</div>
                </button>
                <button
                    onClick={() => handleDownload('transactions', 'csv')}
                    className="card card-body text-left hover:border-[var(--primary)] hover:shadow-md transition-all group"
                >
                    <CalendarIcon className="w-8 h-8 text-[var(--success)] mb-2 group-hover:scale-110 transition-transform" />
                    <div className="font-semibold">Export CSV</div>
                    <div className="text-sm text-[var(--text-muted)]">Download spreadsheet</div>
                </button>
                <button
                    onClick={() => handleDownload('security')}
                    className="card card-body text-left hover:border-[var(--primary)] hover:shadow-md transition-all group"
                >
                    <ChartBarIcon className="w-8 h-8 text-[var(--warning)] mb-2 group-hover:scale-110 transition-transform" />
                    <div className="font-semibold">Security Report</div>
                    <div className="text-sm text-[var(--text-muted)]">Audit log export</div>
                </button>
                <button className="card card-body text-left hover:border-[var(--primary)] hover:shadow-md transition-all group">
                    <DocumentArrowDownIcon className="w-8 h-8 text-[var(--danger)] mb-2 group-hover:scale-110 transition-transform" />
                    <div className="font-semibold">Bulk Download</div>
                    <div className="text-sm text-[var(--text-muted)]">All reports (coming soon)</div>
                </button>
            </div>

            {/* Reports List */}
            <CardWithHeader
                title="Available Reports"
                action={
                    <span className="badge badge-primary">Real-time Data</span>
                }
            >
                <div className="divide-y divide-[var(--border-soft)]">
                    {reports.map((report) => (
                        <div key={report.id} className="flex items-center justify-between py-4 first:pt-0 last:pb-0">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 rounded-xl bg-[var(--primary-soft)] flex items-center justify-center">
                                    <DocumentTextIcon className="w-6 h-6 text-[var(--primary)]" />
                                </div>
                                <div>
                                    <h4 className="font-medium">{report.title}</h4>
                                    <p className="text-sm text-[var(--text-muted)]">{report.description}</p>
                                    <div className="flex items-center gap-3 mt-1 text-xs text-[var(--text-muted)]">
                                        <span className="badge badge-primary">{report.type}</span>
                                        <span>{report.date}</span>
                                        <span className="text-[var(--success)]">● Live Data</span>
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                {report.formats.includes('csv') && (
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        onClick={() => handleDownload(report.id, 'csv')}
                                        loading={downloading === report.id}
                                    >
                                        CSV
                                    </Button>
                                )}
                                <Button
                                    variant="primary"
                                    size="sm"
                                    onClick={() => handleDownload(report.id, 'json')}
                                    loading={downloading === report.id}
                                >
                                    <DocumentArrowDownIcon className="w-4 h-4" />
                                    JSON
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            </CardWithHeader>

            {/* Database Info */}
            <div className="mt-6 p-4 rounded-xl bg-[var(--success-soft)] border border-[var(--success)]">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-[var(--success)] flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                    </div>
                    <div>
                        <div className="font-semibold text-[var(--success)]">Connected to MySQL Database</div>
                        <div className="text-sm text-[var(--text-muted)]">All reports are generated from live database: qr_transaction</div>
                    </div>
                </div>
            </div>
        </div>
    );
}
