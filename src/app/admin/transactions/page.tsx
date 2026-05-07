"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import Header from "@/app/components/ui/Header";
import { StatusBadge } from "@/app/components/ui/Badge";
import Button from "@/app/components/ui/Button";
import {
    MagnifyingGlassIcon,
    FunnelIcon,
    ArrowDownTrayIcon,
    ChevronLeftIcon,
    ChevronRightIcon,
    XMarkIcon,
    ArrowPathIcon,
    ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";

type Transaction = {
    id: number;
    transaction_ref: string;
    amount: number;
    currency: string;
    status: string;
    is_flagged: boolean;
    flag_reason?: string;
    created_at: string;
    completed_at?: string;
    resident_name?: string;
    description?: string;
    transaction_type?: string;
    user_id?: number;
    tamper_score?: number;
};

type TransactionsResponse = {
    success: boolean;
    transactions: Transaction[];
    total: number;
    pages: number;
    current_page: number;
    per_page: number;
};

export default function TransactionsPage() {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [total, setTotal] = useState(0);
    const [flaggedOnly, setFlaggedOnly] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState("");

    // Modal states
    const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
    const [showViewModal, setShowViewModal] = useState(false);

    const loadTransactions = async (pageNum = 1) => {
        setLoading(true);
        setError(null);
        try {
            const qs = new URLSearchParams({ page: String(pageNum), per_page: "10" });
            if (flaggedOnly) qs.set("flagged_only", "true");
            if (searchQuery) qs.set("search", searchQuery);

            const res = await apiFetch<TransactionsResponse>(`/api/admin/transactions?${qs.toString()}`);
            setTransactions(res.transactions || []);
            setPage(res.current_page || pageNum);
            setTotalPages(res.pages || 1);
            setTotal(res.total || 0);
        } catch (err: any) {
            setError(err.message);
            // Demo data fallback
            setTransactions([
                { id: 1, transaction_ref: "QRT-20260114-001", amount: 25.40, currency: "MYR", status: "completed", is_flagged: false, created_at: new Date().toISOString(), resident_name: "Ahmad bin Abdullah", description: "Water Bill", transaction_type: "maintenance_fee" },
                { id: 2, transaction_ref: "QRT-20260114-002", amount: 50.00, currency: "MYR", status: "pending", is_flagged: false, created_at: new Date().toISOString(), resident_name: "Siti Aminah", description: "Maintenance", transaction_type: "maintenance_fee" },
                { id: 3, transaction_ref: "QRT-20260114-003", amount: 27.00, currency: "MYR", status: "failed", is_flagged: true, flag_reason: "Suspicious activity", created_at: new Date().toISOString(), resident_name: "Rajesh Kumar", description: "Parking", transaction_type: "facility_booking" },
                { id: 4, transaction_ref: "QRT-20260114-004", amount: 120.00, currency: "MYR", status: "failed", is_flagged: true, flag_reason: "QR Tampering", created_at: new Date().toISOString(), resident_name: "Tan Mei Ling", description: "Security Fee", transaction_type: "security_payment", tamper_score: -0.75 },
                { id: 5, transaction_ref: "QRT-20260114-005", amount: 85.00, currency: "MYR", status: "completed", is_flagged: false, created_at: new Date().toISOString(), resident_name: "Farah Hanim", description: "Utility Bill", transaction_type: "maintenance_fee" },
            ]);
            setTotal(5);
        } finally {
            setLoading(false);
        }
    };

    // Read URL params on first mount: ?flagged=1 (preset filter) and ?id=N (auto-open modal)
    useEffect(() => {
        if (typeof window === "undefined") return;
        const params = new URLSearchParams(window.location.search);
        if (params.get("flagged") === "1") {
            setFlaggedOnly(true);
        }
    }, []);

    useEffect(() => {
        loadTransactions(1);
    }, [flaggedOnly]);

    // After transactions load, if ?id=N is in URL, auto-open that transaction's modal
    useEffect(() => {
        if (typeof window === "undefined") return;
        if (transactions.length === 0) return;
        const params = new URLSearchParams(window.location.search);
        const idParam = params.get("id");
        if (!idParam) return;
        const targetId = Number(idParam);
        const match = transactions.find((t) => t.id === targetId);
        if (match) {
            setSelectedTransaction(match);
            setShowViewModal(true);
            // Clean the query so reload doesn't keep re-opening
            const url = new URL(window.location.href);
            url.searchParams.delete("id");
            window.history.replaceState({}, "", url.toString());
        }
    }, [transactions]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        loadTransactions(1);
    };

    const handleViewTransaction = (tx: Transaction) => {
        setSelectedTransaction(tx);
        setShowViewModal(true);
    };

    const handleExport = () => {
        // Create CSV content
        const headers = ["Reference", "Resident", "Description", "Amount", "Currency", "Status", "Flagged", "Flag Reason", "Date"];
        const rows = transactions.map(tx => [
            tx.transaction_ref,
            tx.resident_name || "Unknown",
            tx.description || "-",
            tx.amount.toFixed(2),
            tx.currency,
            tx.status,
            tx.is_flagged ? "Yes" : "No",
            tx.flag_reason || "-",
            new Date(tx.created_at).toLocaleString()
        ]);

        const csvContent = [
            headers.join(","),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(","))
        ].join("\n");

        // Download file
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `transactions_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
    };

    const getStatusForBadge = (status: string): string => {
        const statusMap: Record<string, string> = {
            completed: "Completed",
            pending: "Pending",
            failed: "Failed",
            cancelled: "Cancelled",
        };
        return statusMap[status.toLowerCase()] || status;
    };

    return (
        <div className="animate-fadeIn">
            <Header
                title="Transactions"
                subtitle="Transaction Management"
                description="View and manage all QR-based transactions"
            />

            {/* Filters & Actions Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
                {/* Search */}
                <form onSubmit={handleSearch} className="flex-1 max-w-md">
                    <div className="relative">
                        <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                        <input
                            type="text"
                            placeholder="Search by reference or resident..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="input pl-10"
                        />
                    </div>
                </form>

                {/* Actions */}
                <div className="flex items-center gap-3">
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                            type="checkbox"
                            checked={flaggedOnly}
                            onChange={(e) => setFlaggedOnly(e.target.checked)}
                            className="w-4 h-4 rounded border-[var(--border-soft)] text-[var(--primary)] focus:ring-[var(--primary)]"
                        />
                        <span>Flagged Only</span>
                    </label>

                    <Button variant="secondary" size="sm" onClick={handleExport}>
                        <ArrowDownTrayIcon className="w-4 h-4" />
                        Export CSV
                    </Button>

                    <Button variant="primary" size="sm" onClick={() => loadTransactions(page)} disabled={loading}>
                        <ArrowPathIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </div>
            </div>

            {/* Error Banner */}
            {error && (
                <div className="mb-6 p-4 rounded-xl bg-[var(--warning-soft)] text-sm">
                    <strong>Note:</strong> Using demo data. {error}
                </div>
            )}

            {/* Transactions Table */}
            <div className="card">
                <div className="overflow-x-auto">
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Reference</th>
                                <th>Resident</th>
                                <th>Description</th>
                                <th>Amount</th>
                                <th>Status</th>
                                <th>Flag</th>
                                <th>Date</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr>
                                    <td colSpan={8} className="text-center py-12">
                                        <div className="inline-flex items-center gap-2 text-[var(--text-muted)]">
                                            <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                            </svg>
                                            Loading transactions...
                                        </div>
                                    </td>
                                </tr>
                            ) : transactions.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="text-center py-12 text-[var(--text-muted)]">
                                        No transactions found
                                    </td>
                                </tr>
                            ) : (
                                transactions.map((tx) => (
                                    <tr key={tx.id} className={tx.is_flagged ? "bg-[var(--danger-soft)]" : ""}>
                                        <td>
                                            <span className="font-mono text-xs bg-[var(--background)] px-2 py-1 rounded">
                                                {tx.transaction_ref}
                                            </span>
                                        </td>
                                        <td>
                                            <div className="flex items-center gap-2">
                                                <div className="w-8 h-8 rounded-full bg-[var(--primary-soft)] overflow-hidden">
                                                    <img
                                                        src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${tx.resident_name || tx.id}`}
                                                        alt=""
                                                        className="w-full h-full"
                                                    />
                                                </div>
                                                <span>{tx.resident_name || "Unknown"}</span>
                                            </div>
                                        </td>
                                        <td>{tx.description || "-"}</td>
                                        <td className="font-medium">
                                            {tx.currency} {tx.amount.toFixed(2)}
                                        </td>
                                        <td>
                                            <StatusBadge status={getStatusForBadge(tx.status)} />
                                        </td>
                                        <td>
                                            {tx.is_flagged ? (
                                                <span className="badge badge-danger text-xs">
                                                    {tx.flag_reason || "Flagged"}
                                                </span>
                                            ) : (
                                                <span className="text-[var(--text-muted)] text-xs">—</span>
                                            )}
                                        </td>
                                        <td className="text-sm text-[var(--text-muted)]">
                                            {new Date(tx.created_at).toLocaleString()}
                                        </td>
                                        <td>
                                            <Button variant="ghost" size="sm" onClick={() => handleViewTransaction(tx)}>
                                                View
                                            </Button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                <div className="p-4 border-t border-[var(--border-soft)] flex items-center justify-between">
                    <div className="text-sm text-[var(--text-muted)]">
                        Showing {transactions.length} of {total} • Page {page} of {totalPages}
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="secondary"
                            size="sm"
                            disabled={page <= 1 || loading}
                            onClick={() => loadTransactions(page - 1)}
                        >
                            <ChevronLeftIcon className="w-4 h-4" />
                            Previous
                        </Button>
                        <Button
                            variant="secondary"
                            size="sm"
                            disabled={page >= totalPages || loading}
                            onClick={() => loadTransactions(page + 1)}
                        >
                            Next
                            <ChevronRightIcon className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </div>

            {/* View Transaction Modal */}
            {showViewModal && selectedTransaction && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold">Transaction Details</h3>
                            <button onClick={() => setShowViewModal(false)} className="p-1 hover:bg-gray-100 rounded">
                                <XMarkIcon className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            {/* Header */}
                            <div className="flex items-center justify-between pb-4 border-b border-[var(--border-soft)]">
                                <div>
                                    <div className="font-mono text-sm bg-[var(--background)] px-3 py-1 rounded inline-block">
                                        {selectedTransaction.transaction_ref}
                                    </div>
                                    <div className="mt-2">
                                        <StatusBadge status={getStatusForBadge(selectedTransaction.status)} />
                                        {selectedTransaction.is_flagged && (
                                            <span className="badge badge-danger ml-2">Flagged</span>
                                        )}
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-2xl font-bold text-[var(--primary)]">
                                        {selectedTransaction.currency} {selectedTransaction.amount.toFixed(2)}
                                    </div>
                                </div>
                            </div>

                            {/* Details */}
                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <span className="text-[var(--text-muted)]">Resident</span>
                                    <span className="font-medium">{selectedTransaction.resident_name || "Unknown"}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-[var(--text-muted)]">Description</span>
                                    <span className="font-medium">{selectedTransaction.description || "-"}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-[var(--text-muted)]">Type</span>
                                    <span className="font-medium capitalize">{selectedTransaction.transaction_type?.replace(/_/g, ' ') || "-"}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-[var(--text-muted)]">Created At</span>
                                    <span className="font-medium">{new Date(selectedTransaction.created_at).toLocaleString()}</span>
                                </div>
                                {selectedTransaction.completed_at && (
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Completed At</span>
                                        <span className="font-medium">{new Date(selectedTransaction.completed_at).toLocaleString()}</span>
                                    </div>
                                )}
                            </div>

                            {/* Flagged Info */}
                            {selectedTransaction.is_flagged && (
                                <div className="p-4 rounded-lg bg-[var(--danger-soft)] border border-[var(--danger)]">
                                    <div className="font-medium text-[var(--danger)] mb-1 flex items-center gap-1.5">
                                        <ExclamationTriangleIcon className="w-4 h-4" />
                                        Flagged Transaction
                                    </div>
                                    <div className="text-sm">{selectedTransaction.flag_reason || "This transaction has been flagged for review."}</div>
                                    {selectedTransaction.tamper_score !== undefined && (
                                        <div className="text-sm mt-2">
                                            <span className="text-[var(--text-muted)]">Tamper Score: </span>
                                            <span className="font-mono">{selectedTransaction.tamper_score.toFixed(3)}</span>
                                        </div>
                                    )}
                                </div>
                            )}

                            <div className="pt-4">
                                <Button variant="secondary" fullWidth onClick={() => setShowViewModal(false)}>
                                    Close
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
