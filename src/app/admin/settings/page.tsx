"use client";

import { useState, useEffect } from "react";
import QRCode from "qrcode";
import Header from "@/app/components/ui/Header";
import { CardWithHeader } from "@/app/components/ui/Card";
import Button from "@/app/components/ui/Button";
import { logout, apiFetch } from "@/lib/api";
import {
    UserIcon,
    LockClosedIcon,
    ShieldCheckIcon,
    GlobeAltIcon,
    XMarkIcon,
    DevicePhoneMobileIcon,
    ClipboardDocumentIcon,
} from "@heroicons/react/24/outline";

type ProfileResponse = {
    success: boolean;
    user?: {
        full_name?: string;
        email?: string;
        phone_number?: string;
        role?: string;
        is_2fa_enabled?: boolean;
    };
};

export default function SettingsPage() {
    const [notifications, setNotifications] = useState({
        email: true,
        push: true,
        sms: false,
        fraudAlerts: true,
    });

    // Password change modal state
    const [showPasswordModal, setShowPasswordModal] = useState(false);
    const [passwordForm, setPasswordForm] = useState({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
    });
    const [passwordError, setPasswordError] = useState<string | null>(null);
    const [passwordSuccess, setPasswordSuccess] = useState(false);
    const [passwordLoading, setPasswordLoading] = useState(false);

    // Profile form state
    const [profileForm, setProfileForm] = useState({
        fullName: "",
        email: "",
        phone: "",
        role: "",
        is2faEnabled: false,
    });
    const [profileLoading, setProfileLoading] = useState(true);
    const [profileSaving, setProfileSaving] = useState(false);
    const [profileMessage, setProfileMessage] = useState<string | null>(null);

    // 2FA modal state
    const [show2faModal, setShow2faModal] = useState(false);
    const [twoFaMode, setTwoFaMode] = useState<"setup" | "disable">("setup");
    const [twoFaStep, setTwoFaStep] = useState<"loading" | "scan" | "verify" | "success">("loading");
    const [twoFaSecret, setTwoFaSecret] = useState<string>("");
    const [twoFaQrUrl, setTwoFaQrUrl] = useState<string>("");
    const [twoFaOtp, setTwoFaOtp] = useState<string>("");
    const [twoFaError, setTwoFaError] = useState<string | null>(null);
    const [twoFaLoading, setTwoFaLoading] = useState(false);
    const [twoFaSecretCopied, setTwoFaSecretCopied] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const res = await apiFetch<ProfileResponse>("/api/auth/profile");
                const u = res.user || {};
                setProfileForm({
                    fullName: u.full_name || "",
                    email: u.email || "",
                    phone: u.phone_number || "",
                    role: u.role || "admin",
                    is2faEnabled: !!u.is_2fa_enabled,
                });
            } catch (err: any) {
                setProfileMessage("Failed to load profile: " + err.message);
            } finally {
                setProfileLoading(false);
            }
        })();
    }, []);

    const handlePasswordChange = async () => {
        setPasswordError(null);
        setPasswordSuccess(false);

        if (passwordForm.newPassword !== passwordForm.confirmPassword) {
            setPasswordError("New passwords do not match");
            return;
        }

        if (passwordForm.newPassword.length < 8) {
            setPasswordError("Password must be at least 8 characters");
            return;
        }

        setPasswordLoading(true);
        try {
            await apiFetch("/api/auth/password/change", {
                method: "POST",
                body: {
                    current_password: passwordForm.currentPassword,
                    new_password: passwordForm.newPassword,
                },
            });
            setPasswordSuccess(true);
            setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
            setTimeout(() => setShowPasswordModal(false), 2000);
        } catch (err: any) {
            setPasswordError(err.message || "Failed to change password");
        } finally {
            setPasswordLoading(false);
        }
    };

    const reset2faModal = () => {
        setShow2faModal(false);
        setTwoFaSecret("");
        setTwoFaQrUrl("");
        setTwoFaOtp("");
        setTwoFaError(null);
        setTwoFaLoading(false);
        setTwoFaSecretCopied(false);
    };

    const handleConfigure2fa = async () => {
        setTwoFaError(null);
        setTwoFaOtp("");
        setTwoFaSecretCopied(false);

        if (profileForm.is2faEnabled) {
            // Disable flow — just open modal asking for current OTP
            setTwoFaMode("disable");
            setTwoFaStep("verify");
            setShow2faModal(true);
            return;
        }

        // Setup flow — call backend, render QR
        setTwoFaMode("setup");
        setTwoFaStep("loading");
        setShow2faModal(true);
        try {
            const res = await apiFetch<{
                success: boolean;
                secret: string;
                provisioning_uri: string;
            }>("/api/auth/2fa/setup", { method: "POST" });

            setTwoFaSecret(res.secret);
            const qrUrl = await QRCode.toDataURL(res.provisioning_uri, { width: 220, margin: 2 });
            setTwoFaQrUrl(qrUrl);
            setTwoFaStep("scan");
        } catch (err: any) {
            setTwoFaError(err.message || "Failed to start 2FA setup");
            setTwoFaStep("scan");
        }
    };

    const handleVerify2fa = async () => {
        if (twoFaOtp.length !== 6) {
            setTwoFaError("Please enter the 6-digit code from your authenticator app");
            return;
        }
        setTwoFaError(null);
        setTwoFaLoading(true);
        try {
            await apiFetch("/api/auth/2fa/verify", {
                method: "POST",
                body: { otp_code: twoFaOtp },
            });
            setProfileForm((prev) => ({ ...prev, is2faEnabled: true }));
            setTwoFaStep("success");
            setTimeout(() => reset2faModal(), 2500);
        } catch (err: any) {
            setTwoFaError(err.message || "Invalid OTP code");
        } finally {
            setTwoFaLoading(false);
        }
    };

    const handleDisable2fa = async () => {
        if (twoFaOtp.length !== 6) {
            setTwoFaError("Please enter the 6-digit code from your authenticator app");
            return;
        }
        setTwoFaError(null);
        setTwoFaLoading(true);
        try {
            await apiFetch("/api/auth/2fa/disable", {
                method: "POST",
                body: { otp_code: twoFaOtp },
            });
            setProfileForm((prev) => ({ ...prev, is2faEnabled: false }));
            setTwoFaStep("success");
            setTimeout(() => reset2faModal(), 2000);
        } catch (err: any) {
            setTwoFaError(err.message || "Invalid OTP code");
        } finally {
            setTwoFaLoading(false);
        }
    };

    const copySecret = async () => {
        try {
            await navigator.clipboard.writeText(twoFaSecret);
            setTwoFaSecretCopied(true);
            setTimeout(() => setTwoFaSecretCopied(false), 2000);
        } catch {
            setTwoFaError("Could not copy to clipboard");
        }
    };

    const handleProfileSave = async () => {
        setProfileSaving(true);
        setProfileMessage(null);
        try {
            await apiFetch("/api/auth/profile", {
                method: "PUT",
                body: {
                    full_name: profileForm.fullName,
                    phone_number: profileForm.phone,
                },
            });
            setProfileMessage("Profile updated successfully!");
            setTimeout(() => setProfileMessage(null), 3000);
        } catch (err: any) {
            setProfileMessage("Failed to update profile: " + err.message);
        } finally {
            setProfileSaving(false);
        }
    };

    return (
        <div className="animate-fadeIn">
            <Header
                title="Settings"
                subtitle="System Configuration"
                description="Manage your account and system preferences"
            />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Settings */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Profile Settings */}
                    <div id="profile-section">
                        <CardWithHeader title="Profile Settings">
                            <div className="flex items-start gap-6">
                                <div className="w-20 h-20 rounded-full bg-[var(--primary-soft)] overflow-hidden">
                                    <img
                                        src="https://api.dicebear.com/7.x/avataaars/svg?seed=admin"
                                        alt="Profile"
                                        className="w-full h-full"
                                    />
                                </div>
                                <div className="flex-1 space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="label">Full Name</label>
                                            <input
                                                type="text"
                                                className="input"
                                                value={profileForm.fullName}
                                                onChange={(e) => setProfileForm(prev => ({ ...prev, fullName: e.target.value }))}
                                                disabled={profileLoading}
                                                placeholder={profileLoading ? "Loading..." : ""}
                                            />
                                        </div>
                                        <div>
                                            <label className="label">Email</label>
                                            <input
                                                type="email"
                                                className="input"
                                                value={profileForm.email}
                                                disabled
                                            />
                                        </div>
                                        <div>
                                            <label className="label">Phone</label>
                                            <input
                                                type="tel"
                                                className="input"
                                                value={profileForm.phone}
                                                onChange={(e) => setProfileForm(prev => ({ ...prev, phone: e.target.value }))}
                                                disabled={profileLoading}
                                            />
                                        </div>
                                        <div>
                                            <label className="label">Role</label>
                                            <input
                                                type="text"
                                                className="input capitalize"
                                                value={profileForm.role.replace(/_/g, " ") || "—"}
                                                disabled
                                            />
                                        </div>
                                    </div>
                                    {profileMessage && (
                                        <div className={`text-sm ${profileMessage.includes("Failed") ? "text-[var(--danger)]" : "text-[var(--success)]"}`}>
                                            {profileMessage}
                                        </div>
                                    )}
                                    <Button variant="primary" onClick={handleProfileSave} loading={profileSaving}>
                                        Save Changes
                                    </Button>
                                </div>
                            </div>
                        </CardWithHeader>
                    </div>

                    {/* Security Settings */}
                    <div id="security-section">
                        <CardWithHeader title="Security Settings">
                            <div className="space-y-4">
                                <div className="flex items-center justify-between p-4 rounded-lg bg-[var(--background)]">
                                    <div className="flex items-center gap-3">
                                        <LockClosedIcon className="w-5 h-5 text-[var(--primary)]" />
                                        <div>
                                            <div className="font-medium">Password</div>
                                            <div className="text-sm text-[var(--text-muted)]">Last changed 30 days ago</div>
                                        </div>
                                    </div>
                                    <Button variant="secondary" size="sm" onClick={() => setShowPasswordModal(true)}>
                                        Change Password
                                    </Button>
                                </div>

                                <div className="flex items-center justify-between p-4 rounded-lg bg-[var(--background)]">
                                    <div className="flex items-center gap-3">
                                        <ShieldCheckIcon className={`w-5 h-5 ${profileForm.is2faEnabled ? "text-[var(--success)]" : "text-[var(--text-muted)]"}`} />
                                        <div>
                                            <div className="font-medium">Two-Factor Authentication</div>
                                            <div className={`text-sm ${profileForm.is2faEnabled ? "text-[var(--success)]" : "text-[var(--text-muted)]"}`}>
                                                {profileForm.is2faEnabled ? "Enabled — TOTP via authenticator app" : "Disabled — add an extra layer of security"}
                                            </div>
                                        </div>
                                    </div>
                                    <Button
                                        variant={profileForm.is2faEnabled ? "danger" : "primary"}
                                        size="sm"
                                        onClick={handleConfigure2fa}
                                        disabled={profileLoading}
                                    >
                                        {profileForm.is2faEnabled ? "Disable 2FA" : "Enable 2FA"}
                                    </Button>
                                </div>

                                <div className="flex items-center justify-between p-4 rounded-lg bg-[var(--background)]">
                                    <div className="flex items-center gap-3">
                                        <GlobeAltIcon className="w-5 h-5 text-[var(--warning)]" />
                                        <div>
                                            <div className="font-medium">Active Sessions</div>
                                            <div className="text-sm text-[var(--text-muted)]">2 devices logged in</div>
                                        </div>
                                    </div>
                                    <Button variant="danger" size="sm">Logout All</Button>
                                </div>
                            </div>
                        </CardWithHeader>
                    </div>

                    {/* Notification Settings */}
                    <CardWithHeader title="Notification Preferences">
                        <div className="space-y-4">
                            {[
                                { key: "email", label: "Email Notifications", desc: "Receive updates via email" },
                                { key: "push", label: "Push Notifications", desc: "Browser push notifications" },
                                { key: "sms", label: "SMS Alerts", desc: "Critical alerts via SMS" },
                                { key: "fraudAlerts", label: "Fraud Alerts", desc: "Immediate fraud detection alerts" },
                            ].map((item) => (
                                <div key={item.key} className="flex items-center justify-between p-4 rounded-lg bg-[var(--background)]">
                                    <div>
                                        <div className="font-medium">{item.label}</div>
                                        <div className="text-sm text-[var(--text-muted)]">{item.desc}</div>
                                    </div>
                                    <label className="relative inline-flex items-center cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={notifications[item.key as keyof typeof notifications]}
                                            onChange={(e) => setNotifications(prev => ({ ...prev, [item.key]: e.target.checked }))}
                                            className="sr-only peer"
                                        />
                                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[var(--primary-soft)] rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--primary)]"></div>
                                    </label>
                                </div>
                            ))}
                        </div>
                    </CardWithHeader>
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    {/* Quick Actions */}
                    <div className="card card-body">
                        <h3 className="font-semibold mb-4">Quick Actions</h3>
                        <div className="space-y-2">
                            <Button variant="secondary" fullWidth className="justify-start" onClick={() => document.getElementById('profile-section')?.scrollIntoView({ behavior: 'smooth' })}>
                                <UserIcon className="w-4 h-4" />
                                View Profile
                            </Button>
                            <Button variant="secondary" fullWidth className="justify-start" onClick={() => setShowPasswordModal(true)}>
                                <LockClosedIcon className="w-4 h-4" />
                                Change Password
                            </Button>
                            <Button variant="danger" fullWidth className="justify-start" onClick={logout}>
                                Logout
                            </Button>
                        </div>
                    </div>

                    {/* System Info */}
                    <div className="card card-body">
                        <h3 className="font-semibold mb-4">System Information</h3>
                        <div className="space-y-3 text-sm">
                            <div className="flex justify-between">
                                <span className="text-[var(--text-muted)]">Version</span>
                                <span className="font-medium">2.1.0</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[var(--text-muted)]">Encryption</span>
                                <span className="font-medium text-[var(--success)]">AES-256</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[var(--text-muted)]">AI Model</span>
                                <span className="font-medium">v3.2</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[var(--text-muted)]">Last Updated</span>
                                <span className="font-medium">Jan 14, 2026</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Password Change Modal */}
            {showPasswordModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold">Change Password</h3>
                            <button onClick={() => setShowPasswordModal(false)} className="p-1 hover:bg-gray-100 rounded">
                                <XMarkIcon className="w-5 h-5" />
                            </button>
                        </div>

                        {passwordSuccess ? (
                            <div className="text-center py-8">
                                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--success-soft)] flex items-center justify-center">
                                    <ShieldCheckIcon className="w-8 h-8 text-[var(--success)]" />
                                </div>
                                <p className="text-[var(--success)] font-medium">Password changed successfully!</p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div>
                                    <label className="label">Current Password</label>
                                    <input
                                        type="password"
                                        className="input"
                                        value={passwordForm.currentPassword}
                                        onChange={(e) => setPasswordForm(prev => ({ ...prev, currentPassword: e.target.value }))}
                                    />
                                </div>
                                <div>
                                    <label className="label">New Password</label>
                                    <input
                                        type="password"
                                        className="input"
                                        value={passwordForm.newPassword}
                                        onChange={(e) => setPasswordForm(prev => ({ ...prev, newPassword: e.target.value }))}
                                    />
                                </div>
                                <div>
                                    <label className="label">Confirm New Password</label>
                                    <input
                                        type="password"
                                        className="input"
                                        value={passwordForm.confirmPassword}
                                        onChange={(e) => setPasswordForm(prev => ({ ...prev, confirmPassword: e.target.value }))}
                                    />
                                </div>

                                {passwordError && (
                                    <div className="text-sm text-[var(--danger)]">{passwordError}</div>
                                )}

                                <div className="flex gap-3 pt-2">
                                    <Button variant="secondary" fullWidth onClick={() => setShowPasswordModal(false)}>
                                        Cancel
                                    </Button>
                                    <Button variant="primary" fullWidth onClick={handlePasswordChange} loading={passwordLoading}>
                                        Change Password
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 2FA Setup / Disable Modal */}
            {show2faModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold flex items-center gap-2">
                                <ShieldCheckIcon className="w-5 h-5 text-[var(--primary)]" />
                                {twoFaMode === "setup" ? "Enable Two-Factor Authentication" : "Disable Two-Factor Authentication"}
                            </h3>
                            <button onClick={reset2faModal} className="p-1 hover:bg-gray-100 rounded">
                                <XMarkIcon className="w-5 h-5" />
                            </button>
                        </div>

                        {twoFaStep === "loading" && (
                            <div className="py-12 text-center text-sm text-[var(--text-muted)]">
                                Generating secret and QR code...
                            </div>
                        )}

                        {twoFaMode === "setup" && twoFaStep === "scan" && (
                            <div className="space-y-4">
                                <div className="text-sm text-[var(--text-muted)]">
                                    <div className="flex items-center gap-2 mb-2 text-[var(--text)] font-medium">
                                        <DevicePhoneMobileIcon className="w-4 h-4" />
                                        Step 1: Scan with authenticator app
                                    </div>
                                    Use Google Authenticator, Microsoft Authenticator, Authy, or 1Password to scan this QR code.
                                </div>

                                {twoFaQrUrl && (
                                    <div className="flex justify-center p-4 bg-white border border-gray-200 rounded-lg">
                                        <img src={twoFaQrUrl} alt="2FA QR Code" width={220} height={220} />
                                    </div>
                                )}

                                <div>
                                    <label className="label text-xs">Or enter this secret manually:</label>
                                    <div className="flex items-center gap-2 mt-1 p-2 bg-[var(--background)] rounded-lg">
                                        <code className="flex-1 text-xs font-mono break-all">{twoFaSecret}</code>
                                        <button
                                            type="button"
                                            onClick={copySecret}
                                            className="p-1.5 hover:bg-gray-200 rounded text-[var(--text-muted)]"
                                            title="Copy secret"
                                        >
                                            <ClipboardDocumentIcon className="w-4 h-4" />
                                        </button>
                                    </div>
                                    {twoFaSecretCopied && (
                                        <div className="text-xs text-[var(--success)] mt-1">Copied!</div>
                                    )}
                                </div>

                                <div className="border-t pt-4">
                                    <div className="text-[var(--text)] font-medium text-sm mb-2">
                                        Step 2: Enter the 6-digit code from your app
                                    </div>
                                    <input
                                        type="text"
                                        inputMode="numeric"
                                        maxLength={6}
                                        className="input text-center tracking-[0.5em] text-lg font-mono"
                                        placeholder="000000"
                                        value={twoFaOtp}
                                        onChange={(e) => setTwoFaOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                                        autoFocus
                                    />
                                </div>

                                {twoFaError && (
                                    <div className="text-sm text-[var(--danger)]">{twoFaError}</div>
                                )}

                                <div className="flex gap-3 pt-2">
                                    <Button variant="secondary" fullWidth onClick={reset2faModal}>
                                        Cancel
                                    </Button>
                                    <Button
                                        variant="primary"
                                        fullWidth
                                        onClick={handleVerify2fa}
                                        loading={twoFaLoading}
                                        disabled={twoFaOtp.length !== 6}
                                    >
                                        Verify & Enable
                                    </Button>
                                </div>
                            </div>
                        )}

                        {twoFaMode === "disable" && twoFaStep === "verify" && (
                            <div className="space-y-4">
                                <div className="text-sm text-[var(--text-muted)]">
                                    Enter the current 6-digit code from your authenticator app to disable 2FA.
                                </div>
                                <input
                                    type="text"
                                    inputMode="numeric"
                                    maxLength={6}
                                    className="input text-center tracking-[0.5em] text-lg font-mono"
                                    placeholder="000000"
                                    value={twoFaOtp}
                                    onChange={(e) => setTwoFaOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                                    autoFocus
                                />
                                {twoFaError && (
                                    <div className="text-sm text-[var(--danger)]">{twoFaError}</div>
                                )}
                                <div className="flex gap-3 pt-2">
                                    <Button variant="secondary" fullWidth onClick={reset2faModal}>
                                        Cancel
                                    </Button>
                                    <Button
                                        variant="danger"
                                        fullWidth
                                        onClick={handleDisable2fa}
                                        loading={twoFaLoading}
                                        disabled={twoFaOtp.length !== 6}
                                    >
                                        Disable 2FA
                                    </Button>
                                </div>
                            </div>
                        )}

                        {twoFaStep === "success" && (
                            <div className="text-center py-8">
                                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--success-soft)] flex items-center justify-center">
                                    <ShieldCheckIcon className="w-8 h-8 text-[var(--success)]" />
                                </div>
                                <p className="text-[var(--success)] font-medium">
                                    {twoFaMode === "setup" ? "2FA enabled successfully!" : "2FA disabled."}
                                </p>
                                <p className="text-sm text-[var(--text-muted)] mt-2">
                                    {twoFaMode === "setup"
                                        ? "You will need to enter a code from your authenticator app on next login."
                                        : "Your account is now protected by password only."}
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
