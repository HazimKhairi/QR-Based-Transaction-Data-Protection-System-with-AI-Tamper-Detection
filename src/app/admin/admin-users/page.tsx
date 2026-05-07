"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, getCurrentUser, type AuthUser } from "@/lib/api";
import Header from "@/app/components/ui/Header";
import { CardWithHeader } from "@/app/components/ui/Card";
import Button from "@/app/components/ui/Button";
import {
    KeyIcon,
    ShieldCheckIcon,
    TrashIcon,
    XMarkIcon,
    ArrowPathIcon,
    ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";

type AdminUser = {
    id: number;
    full_name: string;
    email: string;
    role: "admin" | "super_admin";
    is_active: boolean;
    is_2fa_enabled?: boolean;
    last_login?: string | null;
    created_at?: string;
};

export default function AdminUsersPage() {
    const router = useRouter();
    const [me, setMe] = useState<AuthUser | null>(null);
    const [admins, setAdmins] = useState<AdminUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Delete modal
    const [deleteTarget, setDeleteTarget] = useState<AdminUser | null>(null);
    const [deleteLoading, setDeleteLoading] = useState(false);
    const [deleteError, setDeleteError] = useState<string | null>(null);
    const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null);

    const isSuperAdmin = me?.role === "super_admin";

    useEffect(() => {
        const u = getCurrentUser();
        setMe(u);
    }, []);

    const loadAdmins = async () => {
        setLoading(true);
        setError(null);
        try {
            // Backend list_users supports a single role filter at a time; merge two calls
            const [a, sa] = await Promise.all([
                apiFetch<{ users: AdminUser[] }>("/api/admin/users?role=admin&per_page=100"),
                apiFetch<{ users: AdminUser[] }>("/api/admin/users?role=super_admin&per_page=100"),
            ]);
            const merged = [...(sa.users || []), ...(a.users || [])];
            setAdmins(merged);
        } catch (err: any) {
            setError(err.message || "Failed to load admin users");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadAdmins();
    }, []);

    const handleDelete = async () => {
        if (!deleteTarget) return;
        setDeleteLoading(true);
        setDeleteError(null);
        setDeleteSuccess(null);
        try {
            await apiFetch(`/api/admin/users/${deleteTarget.id}`, { method: "DELETE" });
            setDeleteSuccess(`${deleteTarget.full_name || deleteTarget.email} deleted.`);
            // Optimistic refresh
            setAdmins((prev) => prev.filter((u) => u.id !== deleteTarget.id));
            setTimeout(() => {
                setDeleteTarget(null);
                setDeleteSuccess(null);
            }, 1800);
        } catch (err: any) {
            setDeleteError(err.message || "Delete failed");
        } finally {
            setDeleteLoading(false);
        }
    };

    const isSelf = (u: AdminUser) => u.id === me?.id;
    const adminTryingToDeleteSuper = (u: AdminUser) => !isSuperAdmin && u.role === "super_admin";

    const superAdmins = admins.filter((u) => u.role === "super_admin");
    const regularAdmins = admins.filter((u) => u.role === "admin");

    return (
        <div className="animate-fadeIn">
            <Header
                title="Admin Accounts"
                subtitle="User management"
                description={
                    isSuperAdmin
                        ? "Super Admin view — you can delete any admin or super admin account (except your own)."
                        : "Regular Admin view — you can delete admin accounts but NOT super admin accounts (enforced server-side)."
                }
            />

            <div className="space-y-6">
                <div className="flex justify-end">
                    <Button variant="secondary" size="sm" onClick={loadAdmins}>
                        <ArrowPathIcon className="w-4 h-4" />
                        Refresh
                    </Button>
                </div>

                {error && (
                    <div className="card p-4 bg-[var(--danger-soft)] border border-[var(--danger)] text-[var(--danger)] text-sm">
                        {error}
                    </div>
                )}

                {/* Super Admin Section */}
                <CardWithHeader
                    title="Super Administrators"
                    action={<span className="badge badge-warning text-xs">{superAdmins.length} account{superAdmins.length === 1 ? "" : "s"}</span>}
                >
                    <UserTable
                        rows={superAdmins}
                        loading={loading}
                        emptyText="No super admin accounts."
                        onDelete={(u) => setDeleteTarget(u)}
                        currentUserId={me?.id}
                        viewerRole={me?.role}
                    />
                </CardWithHeader>

                {/* Admin Section */}
                <CardWithHeader
                    title="Administrators"
                    action={<span className="badge badge-primary text-xs">{regularAdmins.length} account{regularAdmins.length === 1 ? "" : "s"}</span>}
                >
                    <UserTable
                        rows={regularAdmins}
                        loading={loading}
                        emptyText="No admin accounts."
                        onDelete={(u) => setDeleteTarget(u)}
                        currentUserId={me?.id}
                        viewerRole={me?.role}
                    />
                </CardWithHeader>

                {/* Role-difference explanation */}
                <div className="card card-body bg-[var(--background)]">
                    <div className="flex items-start gap-3">
                        <ShieldCheckIcon className="w-5 h-5 text-[var(--primary)] flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-[var(--text-muted)]">
                            <strong className="text-[var(--text)]">How role-based access control works here:</strong>
                            <ul className="list-disc list-inside mt-2 space-y-1">
                                <li>Both <code>admin</code> and <code>super_admin</code> can view and delete <em>regular admin</em> accounts.</li>
                                <li>Only <code>super_admin</code> can delete <em>another super admin</em>. A regular admin attempting this gets HTTP 403 from the backend (<code>admin.py:421</code>).</li>
                                <li>No one can delete their own account (server-side guard, <code>admin.py:412</code>).</li>
                                <li>Deletes are <em>soft</em>: row stays for transaction-history integrity, but <code>is_active=false</code> and email/name anonymised.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            {/* Delete Confirmation Modal */}
            {deleteTarget && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold flex items-center gap-2 text-[var(--danger)]">
                                <ExclamationTriangleIcon className="w-5 h-5" />
                                Delete account
                            </h3>
                            <button
                                onClick={() => {
                                    setDeleteTarget(null);
                                    setDeleteError(null);
                                    setDeleteSuccess(null);
                                }}
                                className="p-1 hover:bg-gray-100 rounded"
                            >
                                <XMarkIcon className="w-5 h-5" />
                            </button>
                        </div>

                        {deleteSuccess ? (
                            <div className="text-center py-6 text-[var(--success)] font-medium">
                                {deleteSuccess}
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="text-sm">
                                    Soft-delete <strong>{deleteTarget.full_name || deleteTarget.email}</strong> (<code>{deleteTarget.role}</code>)?
                                    The row stays in the database but is marked inactive and the email/name are anonymised.
                                </div>

                                {isSelf(deleteTarget) && (
                                    <div className="p-3 rounded-lg bg-[var(--danger-soft)] text-[var(--danger)] text-xs">
                                        You cannot delete your own account. Backend will reject with 403.
                                    </div>
                                )}

                                {adminTryingToDeleteSuper(deleteTarget) && !isSelf(deleteTarget) && (
                                    <div className="p-3 rounded-lg bg-[var(--warning-soft)] text-[var(--warning)] text-xs">
                                        You are signed in as a regular admin. Deleting a super admin will be rejected by the backend (<code>403 — Only super admins can delete super admin accounts</code>). This is the demo for role-based access control.
                                    </div>
                                )}

                                {deleteError && (
                                    <div className="p-3 rounded-lg bg-[var(--danger-soft)] text-[var(--danger)] text-xs">
                                        Backend response: {deleteError}
                                    </div>
                                )}

                                <div className="flex gap-3 pt-2">
                                    <Button
                                        variant="secondary"
                                        fullWidth
                                        onClick={() => {
                                            setDeleteTarget(null);
                                            setDeleteError(null);
                                        }}
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        variant="danger"
                                        fullWidth
                                        onClick={handleDelete}
                                        loading={deleteLoading}
                                        disabled={isSelf(deleteTarget)}
                                    >
                                        Delete account
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

function UserTable({
    rows,
    loading,
    emptyText,
    onDelete,
    currentUserId,
    viewerRole,
}: {
    rows: AdminUser[];
    loading: boolean;
    emptyText: string;
    onDelete: (u: AdminUser) => void;
    currentUserId?: number;
    viewerRole?: AuthUser["role"];
}) {
    if (loading) {
        return <div className="py-8 text-center text-[var(--text-muted)] text-sm">Loading...</div>;
    }
    if (rows.length === 0) {
        return <div className="py-8 text-center text-[var(--text-muted)] text-sm">{emptyText}</div>;
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-[var(--text-muted)]">
                    <tr>
                        <th className="py-2 pr-4">Name</th>
                        <th className="py-2 pr-4">Email</th>
                        <th className="py-2 pr-4">Role</th>
                        <th className="py-2 pr-4">2FA</th>
                        <th className="py-2 pr-4">Status</th>
                        <th className="py-2 pr-4">Last login</th>
                        <th className="py-2 pr-4 text-right">Actions</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-soft)]">
                    {rows.map((u) => {
                        const self = u.id === currentUserId;
                        const isAdminTryingSuper = u.role === "super_admin" && viewerRole === "admin";
                        return (
                            <tr key={u.id} className="hover:bg-[var(--background)]">
                                <td className="py-3 pr-4 font-medium flex items-center gap-2">
                                    {u.full_name || "—"}
                                    {self && <span className="badge badge-primary text-[10px]">you</span>}
                                </td>
                                <td className="py-3 pr-4 text-[var(--text-muted)]">{u.email}</td>
                                <td className="py-3 pr-4">
                                    <span
                                        className={`badge text-[11px] ${
                                            u.role === "super_admin" ? "badge-warning" : "badge-primary"
                                        }`}
                                    >
                                        <KeyIcon className="w-3 h-3" />
                                        {u.role === "super_admin" ? "Super Admin" : "Admin"}
                                    </span>
                                </td>
                                <td className="py-3 pr-4">
                                    {u.is_2fa_enabled ? (
                                        <span className="text-[var(--success)] text-xs">Enabled</span>
                                    ) : (
                                        <span className="text-[var(--text-muted)] text-xs">Disabled</span>
                                    )}
                                </td>
                                <td className="py-3 pr-4">
                                    {u.is_active ? (
                                        <span className="badge badge-success text-[11px]">Active</span>
                                    ) : (
                                        <span className="badge text-[11px]">Inactive</span>
                                    )}
                                </td>
                                <td className="py-3 pr-4 text-[var(--text-muted)] text-xs">
                                    {u.last_login ? new Date(u.last_login).toLocaleString() : "Never"}
                                </td>
                                <td className="py-3 pr-4 text-right">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => onDelete(u)}
                                        disabled={self}
                                        title={
                                            self
                                                ? "Cannot delete your own account"
                                                : isAdminTryingSuper
                                                    ? "Backend will reject — only super admins can delete super admins"
                                                    : "Soft-delete this account"
                                        }
                                    >
                                        <TrashIcon className="w-4 h-4 text-[var(--danger)]" />
                                    </Button>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
