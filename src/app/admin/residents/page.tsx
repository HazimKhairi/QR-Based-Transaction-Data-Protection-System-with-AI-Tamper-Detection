"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import Header from "@/app/components/ui/Header";
import { CardWithHeader } from "@/app/components/ui/Card";
import Button from "@/app/components/ui/Button";
import { StatusBadge } from "@/app/components/ui/Badge";
import {
    MagnifyingGlassIcon,
    PlusIcon,
    EnvelopeIcon,
    PhoneIcon,
    HomeIcon,
    XMarkIcon,
    PencilIcon,
    TrashIcon,
    ArrowPathIcon,
} from "@heroicons/react/24/outline";

type Resident = {
    id: number;
    full_name: string;
    email: string;
    phone_number: string;
    unit_number: string;
    community_name?: string;
    is_active: boolean;
    transactions_count?: number;
    created_at: string;
};

type ModalType = "add" | "view" | "edit" | "delete" | null;

export default function ResidentsPage() {
    const [searchQuery, setSearchQuery] = useState("");
    const [residents, setResidents] = useState<Resident[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Modal states
    const [modalType, setModalType] = useState<ModalType>(null);
    const [selectedResident, setSelectedResident] = useState<Resident | null>(null);
    const [formData, setFormData] = useState({
        full_name: "",
        email: "",
        phone_number: "",
        unit_number: "",
        community_name: "Taman Harmoni Residence",
        password: "",
    });
    const [formLoading, setFormLoading] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);
    const [formSuccess, setFormSuccess] = useState<string | null>(null);

    const fetchResidents = async () => {
        try {
            setLoading(true);
            const response = await apiFetch<any>("/api/admin/users?role=resident&per_page=50");
            const users = response?.users || [];
            setResidents(users.map((u: any) => ({
                id: u.id,
                full_name: u.full_name || u.name || "Unknown",
                email: u.email,
                phone_number: u.phone_number || "-",
                unit_number: u.unit_number || "-",
                community_name: u.community_name || "-",
                is_active: u.is_active,
                transactions_count: u.total_transactions || 0,
                created_at: u.created_at,
            })));
            setError(null);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchResidents();
    }, []);

    const filteredResidents = residents.filter(r =>
        r.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.unit_number?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const activeCount = residents.filter(r => r.is_active).length;
    const inactiveCount = residents.filter(r => !r.is_active).length;

    const openModal = (type: ModalType, resident?: Resident) => {
        setModalType(type);
        setFormError(null);
        setFormSuccess(null);

        if (resident) {
            setSelectedResident(resident);
            setFormData({
                full_name: resident.full_name,
                email: resident.email,
                phone_number: resident.phone_number,
                unit_number: resident.unit_number,
                community_name: resident.community_name || "Taman Harmoni Residence",
                password: "",
            });
        } else {
            setSelectedResident(null);
            setFormData({
                full_name: "",
                email: "",
                phone_number: "",
                unit_number: "",
                community_name: "Taman Harmoni Residence",
                password: "",
            });
        }
    };

    const closeModal = () => {
        setModalType(null);
        setSelectedResident(null);
        setFormError(null);
        setFormSuccess(null);
    };

    const handleAddResident = async () => {
        setFormLoading(true);
        setFormError(null);
        try {
            await apiFetch("/api/auth/register", {
                method: "POST",
                body: {
                    email: formData.email,
                    password: formData.password || "Resident@123",
                    full_name: formData.full_name,
                    phone_number: formData.phone_number,
                    unit_number: formData.unit_number,
                    community_name: formData.community_name,
                    role: "resident",
                },
            });
            setFormSuccess("Resident added successfully!");
            await fetchResidents();
            setTimeout(() => closeModal(), 1500);
        } catch (err: any) {
            setFormError(err.message || "Failed to add resident");
        } finally {
            setFormLoading(false);
        }
    };

    const handleEditResident = async () => {
        if (!selectedResident) return;
        setFormLoading(true);
        setFormError(null);
        try {
            await apiFetch(`/api/admin/users/${selectedResident.id}`, {
                method: "PUT",
                body: {
                    full_name: formData.full_name,
                    phone_number: formData.phone_number,
                    unit_number: formData.unit_number,
                    community_name: formData.community_name,
                },
            });
            setFormSuccess("Resident updated successfully!");
            await fetchResidents();
            setTimeout(() => closeModal(), 1500);
        } catch (err: any) {
            setFormError(err.message || "Failed to update resident");
        } finally {
            setFormLoading(false);
        }
    };

    const handleDeleteResident = async () => {
        if (!selectedResident) return;
        setFormLoading(true);
        setFormError(null);
        try {
            await apiFetch(`/api/admin/users/${selectedResident.id}`, {
                method: "DELETE",
            });
            setFormSuccess("Resident deleted successfully!");
            await fetchResidents();
            setTimeout(() => closeModal(), 1500);
        } catch (err: any) {
            setFormError(err.message || "Failed to delete resident");
        } finally {
            setFormLoading(false);
        }
    };

    return (
        <div className="animate-fadeIn">
            <Header
                title="Residents"
                subtitle="Resident Management"
                description="Manage registered residents and their accounts"
            />

            {error && (
                <div className="mb-6 p-4 rounded-xl bg-[var(--danger-soft)] text-[var(--danger)] text-sm">
                    Error loading residents: {error}
                </div>
            )}

            {/* Actions Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
                <div className="relative flex-1 max-w-md">
                    <MagnifyingGlassIcon className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
                    <input
                        type="text"
                        placeholder="Search residents..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="input pl-10"
                    />
                </div>
                <div className="flex gap-2">
                    <Button variant="secondary" onClick={fetchResidents} disabled={loading}>
                        <ArrowPathIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                    <Button variant="primary" onClick={() => openModal("add")}>
                        <PlusIcon className="w-4 h-4" />
                        Add Resident
                    </Button>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="card card-body">
                    <div className="text-sm text-[var(--text-muted)]">Total Residents</div>
                    <div className="text-2xl font-bold text-[var(--text-main)]">
                        {loading ? "..." : residents.length}
                    </div>
                </div>
                <div className="card card-body">
                    <div className="text-sm text-[var(--text-muted)]">Active</div>
                    <div className="text-2xl font-bold text-[var(--success)]">
                        {loading ? "..." : activeCount}
                    </div>
                </div>
                <div className="card card-body">
                    <div className="text-sm text-[var(--text-muted)]">Inactive</div>
                    <div className="text-2xl font-bold text-[var(--warning)]">
                        {loading ? "..." : inactiveCount}
                    </div>
                </div>
                <div className="card card-body">
                    <div className="text-sm text-[var(--text-muted)]">Verified</div>
                    <div className="text-2xl font-bold text-[var(--primary)]">
                        {loading ? "..." : residents.length}
                    </div>
                </div>
            </div>

            {/* Residents Grid */}
            {loading ? (
                <div className="text-center py-12 text-[var(--text-muted)]">
                    Loading residents...
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredResidents.map((resident) => (
                        <div key={resident.id} className="card hover:shadow-md transition-shadow">
                            <div className="p-5">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-12 h-12 rounded-full bg-[var(--primary-soft)] overflow-hidden">
                                            <img
                                                src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${resident.full_name}`}
                                                alt={resident.full_name}
                                                className="w-full h-full"
                                            />
                                        </div>
                                        <div>
                                            <h3 className="font-semibold">{resident.full_name}</h3>
                                            <StatusBadge status={resident.is_active ? "Active" : "Inactive"} />
                                        </div>
                                    </div>
                                    <div className="flex gap-1">
                                        <button
                                            onClick={() => openModal("edit", resident)}
                                            className="p-1.5 hover:bg-[var(--primary-soft)] rounded text-[var(--primary)]"
                                            title="Edit"
                                        >
                                            <PencilIcon className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => openModal("delete", resident)}
                                            className="p-1.5 hover:bg-[var(--danger-soft)] rounded text-[var(--danger)]"
                                            title="Delete"
                                        >
                                            <TrashIcon className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>

                                <div className="space-y-2 text-sm">
                                    <div className="flex items-center gap-2 text-[var(--text-muted)]">
                                        <EnvelopeIcon className="w-4 h-4" />
                                        <span>{resident.email}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-[var(--text-muted)]">
                                        <PhoneIcon className="w-4 h-4" />
                                        <span>{resident.phone_number}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-[var(--text-muted)]">
                                        <HomeIcon className="w-4 h-4" />
                                        <span>Unit {resident.unit_number}</span>
                                    </div>
                                </div>

                                <div className="mt-4 pt-4 border-t border-[var(--border-soft)] flex items-center justify-between">
                                    <div className="text-sm">
                                        <span className="text-[var(--text-muted)]">Joined: </span>
                                        <span className="font-semibold">
                                            {new Date(resident.created_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                    <Button variant="ghost" size="sm" onClick={() => openModal("view", resident)}>
                                        View Details
                                    </Button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {!loading && filteredResidents.length === 0 && (
                <div className="text-center py-12 text-[var(--text-muted)]">
                    No residents found matching your search.
                </div>
            )}

            {/* Modal */}
            {modalType && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold">
                                {modalType === "add" && "Add New Resident"}
                                {modalType === "view" && "Resident Details"}
                                {modalType === "edit" && "Edit Resident"}
                                {modalType === "delete" && "Delete Resident"}
                            </h3>
                            <button onClick={closeModal} className="p-1 hover:bg-gray-100 rounded">
                                <XMarkIcon className="w-5 h-5" />
                            </button>
                        </div>

                        {formSuccess ? (
                            <div className="text-center py-8">
                                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--success-soft)] flex items-center justify-center">
                                    <svg className="w-8 h-8 text-[var(--success)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                </div>
                                <p className="text-[var(--success)] font-medium">{formSuccess}</p>
                            </div>
                        ) : modalType === "view" && selectedResident ? (
                            <div className="space-y-4">
                                <div className="flex items-center gap-4 pb-4 border-b border-[var(--border-soft)]">
                                    <div className="w-16 h-16 rounded-full bg-[var(--primary-soft)] overflow-hidden">
                                        <img
                                            src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${selectedResident.full_name}`}
                                            alt={selectedResident.full_name}
                                            className="w-full h-full"
                                        />
                                    </div>
                                    <div>
                                        <h4 className="font-semibold text-lg">{selectedResident.full_name}</h4>
                                        <StatusBadge status={selectedResident.is_active ? "Active" : "Inactive"} />
                                    </div>
                                </div>
                                <div className="space-y-3">
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Email</span>
                                        <span className="font-medium">{selectedResident.email}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Phone</span>
                                        <span className="font-medium">{selectedResident.phone_number}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Unit</span>
                                        <span className="font-medium">{selectedResident.unit_number}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Community</span>
                                        <span className="font-medium">{selectedResident.community_name}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Joined</span>
                                        <span className="font-medium">{new Date(selectedResident.created_at).toLocaleDateString()}</span>
                                    </div>
                                </div>
                                <div className="pt-4">
                                    <Button variant="secondary" fullWidth onClick={closeModal}>
                                        Close
                                    </Button>
                                </div>
                            </div>
                        ) : modalType === "delete" && selectedResident ? (
                            <div className="space-y-4">
                                <div className="text-center py-4">
                                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--danger-soft)] flex items-center justify-center">
                                        <TrashIcon className="w-8 h-8 text-[var(--danger)]" />
                                    </div>
                                    <p className="text-[var(--text-main)]">
                                        Are you sure you want to delete <strong>{selectedResident.full_name}</strong>?
                                    </p>
                                    <p className="text-sm text-[var(--text-muted)] mt-2">
                                        This action cannot be undone.
                                    </p>
                                </div>
                                {formError && (
                                    <div className="text-sm text-[var(--danger)] text-center">{formError}</div>
                                )}
                                <div className="flex gap-3">
                                    <Button variant="secondary" fullWidth onClick={closeModal}>
                                        Cancel
                                    </Button>
                                    <Button variant="danger" fullWidth onClick={handleDeleteResident} loading={formLoading}>
                                        Delete
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div>
                                    <label className="label">Full Name *</label>
                                    <input
                                        type="text"
                                        className="input"
                                        value={formData.full_name}
                                        onChange={(e) => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
                                        placeholder="Enter full name"
                                    />
                                </div>
                                {modalType === "add" && (
                                    <>
                                        <div>
                                            <label className="label">Email *</label>
                                            <input
                                                type="email"
                                                className="input"
                                                value={formData.email}
                                                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                                                placeholder="Enter email"
                                            />
                                        </div>
                                        <div>
                                            <label className="label">Password</label>
                                            <input
                                                type="password"
                                                className="input"
                                                value={formData.password}
                                                onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                                                placeholder="Default: Resident@123"
                                            />
                                        </div>
                                    </>
                                )}
                                <div>
                                    <label className="label">Phone Number</label>
                                    <input
                                        type="tel"
                                        className="input"
                                        value={formData.phone_number}
                                        onChange={(e) => setFormData(prev => ({ ...prev, phone_number: e.target.value }))}
                                        placeholder="+60123456789"
                                    />
                                </div>
                                <div>
                                    <label className="label">Unit Number</label>
                                    <input
                                        type="text"
                                        className="input"
                                        value={formData.unit_number}
                                        onChange={(e) => setFormData(prev => ({ ...prev, unit_number: e.target.value }))}
                                        placeholder="e.g., A-12-01"
                                    />
                                </div>
                                <div>
                                    <label className="label">Community</label>
                                    <input
                                        type="text"
                                        className="input"
                                        value={formData.community_name}
                                        onChange={(e) => setFormData(prev => ({ ...prev, community_name: e.target.value }))}
                                    />
                                </div>

                                {formError && (
                                    <div className="text-sm text-[var(--danger)]">{formError}</div>
                                )}

                                <div className="flex gap-3 pt-2">
                                    <Button variant="secondary" fullWidth onClick={closeModal}>
                                        Cancel
                                    </Button>
                                    <Button
                                        variant="primary"
                                        fullWidth
                                        onClick={modalType === "add" ? handleAddResident : handleEditResident}
                                        loading={formLoading}
                                    >
                                        {modalType === "add" ? "Add Resident" : "Save Changes"}
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
