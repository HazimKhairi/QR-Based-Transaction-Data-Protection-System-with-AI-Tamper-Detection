"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import QRCode from "qrcode";
import { apiFetch } from "@/lib/api";
import PinInput from "@/app/components/ui/PinInput";
import Button from "@/app/components/ui/Button";
import {
    ShieldCheckIcon,
    ExclamationTriangleIcon,
    CheckCircleIcon,
    ArrowLeftIcon,
    LockClosedIcon,
    ArrowPathIcon,
} from "@heroicons/react/24/outline";

type PaymentState = "loading" | "idle" | "processing" | "success" | "flagged" | "error";

type GenerateQrResponse = {
    success: boolean;
    transaction_id?: number;
    transaction_ref?: string;
    qr_code_data: string;
    qr_code_hash?: string;
    expires_at?: string;
    amount?: number;
    error?: string;
};

type ProcessResponse = {
    success: boolean;
    transaction_ref?: string;
    amount?: number;
    completed_at?: string;
    error?: string;
    tamper_detection?: {
        analyzed: boolean;
        anomaly_score: number;
        is_anomaly: boolean;
    };
};

const DEMO_AMOUNT = 25.50;

export default function ResidentPaymentPage() {
    const router = useRouter();
    const [qrUrl, setQrUrl] = useState<string>("");
    const [qrData, setQrData] = useState<string>("");
    const [transactionRef, setTransactionRef] = useState<string>("");
    const [otp, setOtp] = useState<string>("");
    const [paymentState, setPaymentState] = useState<PaymentState>("loading");
    const [errorMessage, setErrorMessage] = useState<string>("");
    const [resultDetails, setResultDetails] = useState<ProcessResponse | null>(null);

    const generateQr = useCallback(async () => {
        setPaymentState("loading");
        setErrorMessage("");
        setOtp("");
        setResultDetails(null);
        try {
            const res = await apiFetch<GenerateQrResponse>("/api/transactions/demo/generate-qr", {
                method: "POST",
                body: {
                    amount: DEMO_AMOUNT,
                    description: "Resident demo payment",
                    transaction_type: "maintenance_fee",
                    expires_in_minutes: 30,
                },
            });

            if (!res.success || !res.qr_code_data) {
                throw new Error(res.error || "Failed to generate QR");
            }

            const dataUrl = await QRCode.toDataURL(res.qr_code_data, {
                width: 220,
                margin: 2,
                color: { dark: "#1E293B", light: "#FFFFFF" },
            });

            setQrUrl(dataUrl);
            setQrData(res.qr_code_data);
            setTransactionRef(res.transaction_ref || "");
            setPaymentState("idle");
        } catch (err: any) {
            setPaymentState("error");
            setErrorMessage(err.message || "Failed to generate QR code. Is the backend running?");
        }
    }, []);

    useEffect(() => {
        generateQr();
    }, [generateQr]);

    const handleConfirmPayment = async () => {
        if (otp.length !== 6) {
            setErrorMessage("Please enter the 6-digit OTP code");
            return;
        }
        if (!qrData) {
            setErrorMessage("QR code not ready. Refresh and try again.");
            return;
        }

        setPaymentState("processing");
        setErrorMessage("");

        try {
            const res = await apiFetch<ProcessResponse>("/api/transactions/demo/process", {
                method: "POST",
                body: {
                    qr_code_data: qrData,
                    otp_code: otp,
                },
            });

            setResultDetails(res);

            if (!res.success) {
                setPaymentState("error");
                setErrorMessage(res.error || "Transaction failed");
                return;
            }

            if (res.tamper_detection?.is_anomaly) {
                setPaymentState("flagged");
            } else {
                setPaymentState("success");
            }
        } catch (err: any) {
            setPaymentState("error");
            setErrorMessage(err.message || "Transaction processing failed");
        }
    };

    const handleReset = () => {
        generateQr();
    };

    if (paymentState === "loading") {
        return (
            <div className="card rounded-[28px] overflow-hidden animate-fadeIn">
                <div className="gradient-header text-white p-6 text-center">
                    <h1 className="text-xl font-bold">Generating Secure QR</h1>
                    <p className="text-white/80 text-sm mt-2">Encrypting payload with AES-256...</p>
                </div>
                <div className="p-12 flex items-center justify-center">
                    <ArrowPathIcon className="w-12 h-12 text-[var(--primary)] animate-spin" />
                </div>
            </div>
        );
    }

    if (paymentState === "success" || paymentState === "flagged") {
        const flagged = paymentState === "flagged";
        return (
            <div className="card rounded-[28px] overflow-hidden animate-fadeIn">
                <div className={`${flagged ? "bg-[var(--warning)]" : "gradient-header"} text-white p-6 text-center`}>
                    <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-white/20 flex items-center justify-center">
                        {flagged ? (
                            <ExclamationTriangleIcon className="w-12 h-12 text-white" />
                        ) : (
                            <CheckCircleIcon className="w-12 h-12 text-white" />
                        )}
                    </div>
                    <h1 className="text-2xl font-bold">
                        {flagged ? "Transaction Flagged" : "Payment Successful!"}
                    </h1>
                    <p className="text-white/80 mt-2">
                        {flagged
                            ? "AI detected anomaly — admin review required"
                            : "Your transaction has been processed securely"}
                    </p>
                </div>

                <div className="p-6 space-y-4">
                    <div className={`p-4 rounded-xl ${flagged ? "bg-[var(--warning-soft)] border border-[var(--warning)]" : "bg-[var(--success-soft)] border border-[var(--success)]"}`}>
                        <div className="flex items-center gap-3">
                            <ShieldCheckIcon className={`w-6 h-6 ${flagged ? "text-[var(--warning)]" : "text-[var(--success)]"}`} />
                            <div>
                                <div className={`font-semibold ${flagged ? "text-[var(--warning)]" : "text-[var(--success)]"}`}>
                                    {flagged ? "Anomaly Detected" : "Transaction Verified"}
                                </div>
                                <div className="text-sm text-[var(--text-muted)]">
                                    AES-256 + Isolation Forest AI
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="text-center py-4">
                        <div className="text-sm text-[var(--text-muted)]">Amount Paid</div>
                        <div className="text-3xl font-bold text-[var(--text-main)]">
                            RM {(resultDetails?.amount ?? DEMO_AMOUNT).toFixed(2)}
                        </div>
                    </div>

                    <div className="space-y-2 text-sm">
                        <div className="flex justify-between py-2 border-b border-[var(--border-soft)]">
                            <span className="text-[var(--text-muted)]">Transaction Ref</span>
                            <span className="font-mono text-xs">{resultDetails?.transaction_ref || transactionRef}</span>
                        </div>
                        <div className="flex justify-between py-2 border-b border-[var(--border-soft)]">
                            <span className="text-[var(--text-muted)]">Date & Time</span>
                            <span>
                                {resultDetails?.completed_at
                                    ? new Date(resultDetails.completed_at).toLocaleString()
                                    : new Date().toLocaleString()}
                            </span>
                        </div>
                        {resultDetails?.tamper_detection && (
                            <div className="flex justify-between py-2 border-b border-[var(--border-soft)]">
                                <span className="text-[var(--text-muted)]">AI Anomaly Score</span>
                                <span className="font-mono">
                                    {Number(resultDetails.tamper_detection.anomaly_score).toFixed(3)}
                                </span>
                            </div>
                        )}
                        <div className="flex justify-between py-2">
                            <span className="text-[var(--text-muted)]">Status</span>
                            <span className={`badge ${flagged ? "badge-warning" : "badge-success"}`}>
                                {flagged ? "Flagged for review" : "Completed"}
                            </span>
                        </div>
                    </div>

                    <Button variant="primary" fullWidth onClick={handleReset}>
                        Make Another Payment
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="card rounded-[28px] overflow-hidden animate-fadeIn">
            <div className="gradient-header text-white p-4">
                <div className="flex items-center justify-between mb-2">
                    <button
                        onClick={() => router.back()}
                        className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center hover:bg-white/30 transition-colors"
                    >
                        <ArrowLeftIcon className="w-4 h-4" />
                    </button>
                    <span className="text-sm font-medium">Resident QR Payment</span>
                    <div className="w-8 h-8" />
                </div>
                <div className="text-center mt-4">
                    <h1 className="text-xl font-bold">Secure QR Payment</h1>
                    <p className="text-sm text-white/80 mt-1">
                        Protected with AES Encryption & AI Fraud Detection
                    </p>
                </div>
            </div>

            <div className="p-5 space-y-5">
                <p className="text-center text-sm text-[var(--text-muted)]">
                    Scan the QR Code to make a secure payment
                </p>

                <div className="flex justify-center">
                    <div className="p-4 rounded-2xl bg-white shadow-lg border border-[var(--border-soft)]">
                        {qrUrl ? (
                            <img src={qrUrl} alt="Payment QR Code" className="w-[200px] h-[200px]" />
                        ) : (
                            <div className="w-[200px] h-[200px] bg-[var(--background)] rounded-lg animate-pulse" />
                        )}
                    </div>
                </div>

                {transactionRef && (
                    <p className="text-center text-xs font-mono text-[var(--text-muted)]">
                        Ref: {transactionRef}
                    </p>
                )}

                <div className="flex items-center justify-center gap-2">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--success-soft)] text-[var(--success)] text-xs font-medium">
                        <LockClosedIcon className="w-3.5 h-3.5" />
                        AES Encryption Enabled
                    </span>
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--warning-soft)] text-[#CA8A04] text-xs font-medium">
                        <ExclamationTriangleIcon className="w-3.5 h-3.5" />
                        AI Fraud Detection Active
                    </span>
                </div>

                <div className="space-y-3">
                    <label className="block text-center text-sm font-medium text-[var(--text-main)]">
                        Enter 6-digit OTP Code
                    </label>
                    <PinInput
                        length={6}
                        onComplete={setOtp}
                        onChange={setOtp}
                        disabled={paymentState === "processing"}
                        error={paymentState === "error"}
                    />
                    {errorMessage && (
                        <p className="text-center text-sm text-[var(--danger)]">{errorMessage}</p>
                    )}
                </div>

                <Button
                    variant="success"
                    fullWidth
                    size="lg"
                    disabled={otp.length !== 6 || paymentState === "processing"}
                    loading={paymentState === "processing"}
                    onClick={handleConfirmPayment}
                    className="rounded-xl py-4 text-base font-semibold uppercase tracking-wide"
                >
                    {paymentState === "processing" ? "Processing..." : "Confirm Payment"}
                </Button>

                <div className="text-center space-y-1">
                    <div className="flex items-center justify-center gap-2 text-xs text-[var(--text-muted)]">
                        <ShieldCheckIcon className="w-4 h-4 text-[var(--success)]" />
                        AES-256 Bit Encryption Enabled
                    </div>
                    <div className="flex items-center justify-center gap-2 text-xs text-[var(--text-muted)]">
                        <ExclamationTriangleIcon className="w-4 h-4 text-[var(--warning)]" />
                        AI Detection Active
                    </div>
                </div>
            </div>
        </div>
    );
}
