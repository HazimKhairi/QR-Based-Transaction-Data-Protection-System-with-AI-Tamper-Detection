import { ReactNode } from "react";
import { StatusBadge } from "./Badge";
import Link from "next/link";

interface Column<T> {
    key: keyof T | string;
    header: string;
    render?: (item: T) => ReactNode;
    className?: string;
}

interface DataTableProps<T> {
    columns: Column<T>[];
    data: T[];
    loading?: boolean;
    emptyMessage?: string;
    viewAllLink?: string;
    onRowClick?: (item: T) => void;
}

export default function DataTable<T extends Record<string, any>>({
    columns,
    data,
    loading = false,
    emptyMessage = "No data available",
    viewAllLink,
    onRowClick,
}: DataTableProps<T>) {
    if (loading) {
        return (
            <div className="p-8 text-center">
                <div className="inline-flex items-center gap-2 text-[var(--text-muted)]">
                    <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                    </svg>
                    <span>Loading...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="table">
                <thead>
                    <tr>
                        {columns.map((col, index) => (
                            <th key={index} className={col.className}>
                                {col.header}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.length === 0 ? (
                        <tr>
                            <td colSpan={columns.length} className="text-center py-8 text-[var(--text-muted)]">
                                {emptyMessage}
                            </td>
                        </tr>
                    ) : (
                        data.map((item, rowIndex) => (
                            <tr
                                key={rowIndex}
                                onClick={() => onRowClick?.(item)}
                                className={onRowClick ? "cursor-pointer" : ""}
                            >
                                {columns.map((col, colIndex) => (
                                    <td key={colIndex} className={col.className}>
                                        {col.render
                                            ? col.render(item)
                                            : item[col.key as keyof T]
                                        }
                                    </td>
                                ))}
                            </tr>
                        ))
                    )}
                </tbody>
            </table>

            {viewAllLink && data.length > 0 && (
                <div className="p-3 border-t border-[var(--border-soft)] text-center">
                    <Link
                        href={viewAllLink}
                        className="text-sm font-medium text-[var(--primary)] hover:underline"
                    >
                        View All →
                    </Link>
                </div>
            )}
        </div>
    );
}

// Pre-configured table for transactions
interface Transaction {
    resident?: string;
    name?: string;
    date?: string;
    amount?: string | number;
    status?: string;
    id?: number | string;
}

export function TransactionsTable({
    data,
    loading,
    viewAllLink
}: {
    data: Transaction[];
    loading?: boolean;
    viewAllLink?: string;
}) {
    const columns: Column<Transaction>[] = [
        {
            key: "resident",
            header: "Resident",
            render: (item) => (
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-[var(--primary-soft)] flex items-center justify-center overflow-hidden">
                        <img
                            src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${item.resident || 'user'}`}
                            alt=""
                            className="w-full h-full"
                        />
                    </div>
                    <span className="font-medium">{item.resident || "Unknown"}</span>
                </div>
            )
        },
        { key: "name", header: "Name" },
        { key: "date", header: "Date" },
        {
            key: "amount",
            header: "Amount",
            render: (item) => (
                <span className="font-medium">
                    {typeof item.amount === "number" ? `RM ${item.amount.toFixed(2)}` : item.amount}
                </span>
            )
        },
        {
            key: "status",
            header: "Status",
            render: (item) => <StatusBadge status={item.status || "Unknown"} />
        },
    ];

    return (
        <DataTable
            columns={columns}
            data={data}
            loading={loading}
            viewAllLink={viewAllLink}
        />
    );
}
