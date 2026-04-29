"use client";
import { useEffect, useState } from "react";
import { apiFetch, isAuthenticated } from "@/lib/api";
import QRCode from "qrcode";
import Link from "next/link";
import Button from "@/app/components/ui/Button";
import { CardWithHeader, Card } from "@/app/components/ui/Card";
import { StatusBadge } from "@/app/components/ui/Badge";
import {
  ShieldCheckIcon,
  LockClosedIcon,
  CpuChipIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
  QrCodeIcon,
} from "@heroicons/react/24/outline";

type GenerateQRResponse = {
  success: boolean;
  transaction_ref: string;
  qr_code_data: string;
  qr_code_hash?: string;
  expires_at?: string;
};

type VerifyQRResponse = {
  valid: boolean;
  tampered?: boolean;
  error?: string;
  payload?: any;
  transaction?: any;
};

type ProcessResponse = {
  success: boolean;
  message?: string;
  transaction_ref?: string;
  amount?: number;
  currency?: string;
  completed_at?: string;
  error?: string;
};

export default function DemoPage() {
  const [step, setStep] = useState<number>(1);
  const [amount, setAmount] = useState<number>(25.50);
  const [description, setDescription] = useState<string>("Water Bill Payment");
  const [qr, setQr] = useState<GenerateQRResponse | null>(null);
  const [verification, setVerification] = useState<VerifyQRResponse | null>(null);
  const [tamperedVerification, setTamperedVerification] = useState<VerifyQRResponse | null>(null);
  const [otp, setOtp] = useState<string>("123456");
  const [processRes, setProcessRes] = useState<ProcessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [qrImageUrl, setQrImageUrl] = useState<string | null>(null);
  const [tamperedString, setTamperedString] = useState<string | null>(null);
  const [tamperedQrImageUrl, setTamperedQrImageUrl] = useState<string | null>(null);

  // Demo page is publicly accessible - no authentication required

  const handleGenerateQR = async () => {
    setLoading(true);
    setError(null);
    setVerification(null);
    setTamperedVerification(null);
    setProcessRes(null);
    setQrImageUrl(null);
    setTamperedString(null);
    setTamperedQrImageUrl(null);
    try {
      const res = await apiFetch<GenerateQRResponse>("/api/transactions/demo/generate-qr", {
        method: "POST",
        body: {
          amount,
          description: description || "QR Payment",
          transaction_type: "maintenance_fee",
          expires_in_minutes: 30,
        },
      });
      setQr(res);
      if (res.qr_code_data) {
        try {
          const url = await QRCode.toDataURL(res.qr_code_data, { width: 200, margin: 2 });
          setQrImageUrl(url);
        } catch (e) { }
      }
      setStep(2);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyQR = async () => {
    if (!qr?.qr_code_data) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<VerifyQRResponse>("/api/transactions/demo/verify-qr", {
        method: "POST",
        body: { qr_code_data: qr.qr_code_data, qr_code_hash: qr.qr_code_hash },
      });
      setVerification(res);
      setStep(3);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const tamperString = (s: string) => {
    if (!s || s.length < 4) return s;
    const idx = Math.floor(s.length / 3);
    const flipped = s[idx] === "A" ? "B" : "A";
    return s.slice(0, idx) + flipped + s.slice(idx + 1);
  };

  const handleVerifyTampered = async () => {
    if (!qr?.qr_code_data) return;
    const tampered = tamperString(qr.qr_code_data);
    setTamperedString(tampered);
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<VerifyQRResponse>("/api/transactions/demo/verify-qr", {
        method: "POST",
        body: { qr_code_data: tampered, qr_code_hash: qr.qr_code_hash },
      });
      setTamperedVerification(res);
      try {
        const url = await QRCode.toDataURL(tampered, { width: 200, margin: 2 });
        setTamperedQrImageUrl(url);
      } catch (e) { }
      setStep(4);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleProcess = async () => {
    if (!qr?.qr_code_data) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<ProcessResponse>("/api/transactions/demo/process", {
        method: "POST",
        body: { qr_code_data: qr.qr_code_data, otp_code: otp },
      });
      setProcessRes(res);
      setStep(5);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const StepIndicator = ({ num, title, active, completed }: { num: number; title: string; active: boolean; completed: boolean }) => (
    <div className={`flex items-center gap-3 ${active ? 'text-[var(--primary)]' : completed ? 'text-[var(--success)]' : 'text-[var(--text-muted)]'}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${active ? 'bg-[var(--primary)] text-white' :
        completed ? 'bg-[var(--success)] text-white' :
          'bg-[var(--border-soft)] text-[var(--text-muted)]'
        }`}>
        {completed ? <CheckCircleIcon className="w-5 h-5" /> : num}
      </div>
      <span className="font-medium hidden md:inline">{title}</span>
    </div>
  );

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Header */}
      <header className="bg-white border-b border-[var(--border-soft)] sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
              <ShieldCheckIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="font-bold text-[var(--text-main)]">Transaction Demo</div>
              <div className="text-xs text-[var(--text-muted)]">QR Flow Demonstration</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/admin/dashboard" className="btn btn-secondary">
              Dashboard
            </Link>
            <Link href="/" className="btn btn-ghost">
              Home
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[var(--text-main)] mb-2">QR Transaction Flow Demo</h1>
          <p className="text-[var(--text-muted)]">
            Experience the complete secure QR payment process with AES encryption and AI fraud detection
          </p>
        </div>

        {/* Step Indicators */}
        <div className="flex justify-center gap-4 md:gap-8 mb-8 overflow-x-auto pb-4">
          <StepIndicator num={1} title="Generate QR" active={step === 1} completed={step > 1} />
          <ArrowRightIcon className="w-5 h-5 text-[var(--border-soft)] flex-shrink-0" />
          <StepIndicator num={2} title="Encrypt Data" active={step === 2} completed={step > 2} />
          <ArrowRightIcon className="w-5 h-5 text-[var(--border-soft)] flex-shrink-0" />
          <StepIndicator num={3} title="Detect Tampering" active={step === 3 || step === 4} completed={step > 4} />
          <ArrowRightIcon className="w-5 h-5 text-[var(--border-soft)] flex-shrink-0" />
          <StepIndicator num={4} title="Verify & Pay" active={step === 5} completed={processRes?.success || false} />
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-[var(--danger-soft)] border border-[var(--danger)] text-[var(--danger)] text-sm">
            <strong>Error:</strong> {error}
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Step 1: Generate QR */}
          <CardWithHeader
            title="Step 1: Scan QR Code"
            action={step >= 1 && <StatusBadge status={step > 1 ? "Completed" : "Active"} />}
          >
            <div className="space-y-4">
              <p className="text-sm text-[var(--text-muted)]">
                Generate a secure QR code for payment demonstration.
              </p>
              <div>
                <label className="label">Payment Description / Name</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g., Water Bill, Parking Fee, Maintenance"
                  className="input"
                />
              </div>
              <div>
                <label className="label">Amount (RM)</label>
                <input
                  type="number"
                  min={0.01}
                  step={0.01}
                  value={amount}
                  onChange={(e) => setAmount(parseFloat(e.target.value))}
                  className="input w-48"
                />
              </div>
              <Button onClick={handleGenerateQR} loading={loading && step === 1} disabled={loading}>
                <QrCodeIcon className="w-5 h-5" />
                Generate QR Code
              </Button>
              {qr && (
                <div className="p-3 rounded-lg bg-[var(--success-soft)] text-sm">
                  <strong>Transaction Ref:</strong> {qr.transaction_ref}<br />
                  <strong>Description:</strong> {description}
                </div>
              )}
            </div>
          </CardWithHeader>

          {/* Step 2: AES Encryption */}
          <CardWithHeader
            title="Step 2: AES Encryption"
            action={step >= 2 && <StatusBadge status={step > 2 ? "Completed" : step === 2 ? "Active" : "Pending"} />}
          >
            <div className="space-y-4">
              <p className="text-sm text-[var(--text-muted)]">
                Transaction data is encrypted with AES-256. The encrypted data cannot be read without the key.
              </p>
              {qr?.qr_code_data ? (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs font-medium text-[var(--text-muted)] mb-2">Encrypted Data</div>
                      <pre className="text-xs bg-[var(--background)] border rounded-lg p-3 overflow-x-auto max-h-32">
                        {qr.qr_code_data}
                      </pre>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-[var(--text-muted)] mb-2">QR Code</div>
                      {qrImageUrl ? (
                        <img src={qrImageUrl} alt="QR" className="border rounded-lg" />
                      ) : (
                        <div className="h-32 bg-[var(--background)] rounded-lg animate-pulse" />
                      )}
                    </div>
                  </div>
                  <Button variant="secondary" onClick={handleVerifyQR} loading={loading && step === 2} disabled={loading}>
                    <LockClosedIcon className="w-5 h-5" />
                    Verify & Decrypt QR
                  </Button>
                  {verification && (
                    <div className="p-3 rounded-lg bg-[var(--success-soft)] text-sm space-y-1">
                      <div><strong>Valid:</strong> {String(verification.valid)}</div>
                      {verification.payload && (
                        <>
                          <div><strong>Amount:</strong> RM {verification.payload.amount}</div>
                          <div><strong>Ref:</strong> {verification.payload.transaction_ref}</div>
                        </>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-[var(--text-muted)]">Generate QR code first.</p>
              )}
            </div>
          </CardWithHeader>

          {/* Step 3: Tamper Detection */}
          <CardWithHeader
            title="Step 3: AI Tamper Detection"
            action={step >= 3 && <StatusBadge status={step > 4 ? "Completed" : (step === 3 || step === 4) ? "Active" : "Pending"} />}
          >
            <div className="space-y-4">
              <p className="text-sm text-[var(--text-muted)]">
                Simulate QR tampering to demonstrate how the AI detects modifications.
              </p>
              <Button variant="danger" onClick={handleVerifyTampered} loading={loading && (step === 3 || step === 4)} disabled={!qr?.qr_code_data || loading}>
                <ExclamationTriangleIcon className="w-5 h-5" />
                Test Tampered QR
              </Button>
              {tamperedVerification && (
                <div className={`p-3 rounded-lg ${tamperedVerification.valid ? 'bg-[var(--success-soft)]' : 'bg-[var(--warning-soft)] border border-[var(--warning)]'} text-sm space-y-1`}>
                  {!tamperedVerification.valid ? (
                    <>
                      <div className="flex items-center gap-2 text-[var(--warning)] font-semibold">
                        <ExclamationTriangleIcon className="w-5 h-5" />
                        Tampering Detected - QR Rejected!
                      </div>
                      <div className="text-[var(--text-muted)] text-xs mt-2">
                        ✅ <strong>Security Working:</strong> The AI successfully detected the modified QR code and blocked it.
                        This is how the system protects against fraudulent QR codes.
                      </div>
                    </>
                  ) : (
                    <div><strong>Valid:</strong> {String(tamperedVerification.valid)}</div>
                  )}
                </div>
              )}
              {tamperedQrImageUrl && (
                <div>
                  <div className="text-xs font-medium text-[var(--warning)] mb-2">⚠️ Simulated Tampered QR (Blocked)</div>
                  <img src={tamperedQrImageUrl} alt="Tampered QR" className="border-2 border-[var(--warning)] rounded-lg w-32 opacity-60" />
                </div>
              )}
            </div>
          </CardWithHeader>

          {/* Step 4: 2FA Verification */}
          <CardWithHeader
            title="Step 4: 2FA Verification"
            action={step >= 5 && <StatusBadge status={processRes?.success ? "Completed" : "Active"} />}
          >
            <div className="space-y-4">
              <p className="text-sm text-[var(--text-muted)]">
                Enter 2FA PIN to authorize the transaction.
              </p>
              <div>
                <label className="label">PIN / OTP Code</label>
                <input
                  type="text"
                  value={otp}
                  maxLength={6}
                  onChange={(e) => setOtp(e.target.value)}
                  className="input w-48"
                  placeholder="Enter 6-digit code"
                />
              </div>
              <Button variant="success" onClick={handleProcess} loading={loading && step >= 4} disabled={!qr?.qr_code_data || loading}>
                <CheckCircleIcon className="w-5 h-5" />
                Verify & Process Payment
              </Button>
              {processRes && (
                <div className={`p-4 rounded-lg ${processRes.success ? 'bg-[var(--success-soft)] border border-[var(--success)]' : 'bg-[var(--danger-soft)]'}`}>
                  {processRes.success ? (
                    <div className="space-y-2">
                      <div className="font-semibold text-[var(--success)] flex items-center gap-2">
                        <CheckCircleIcon className="w-5 h-5" />
                        Payment Successful!
                      </div>
                      <div className="text-sm">
                        <div>Transaction: {processRes.transaction_ref}</div>
                        <div>Amount: RM {processRes.amount}</div>
                        <div>Completed: {processRes.completed_at}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-[var(--danger)]">Error: {processRes.error || processRes.message}</div>
                  )}
                </div>
              )}
            </div>
          </CardWithHeader>
        </div>

        {/* Quick Links */}
        <div className="mt-8 flex justify-center gap-4">
          <Link href="/admin/dashboard" className="btn btn-primary">
            View Dashboard
          </Link>
          <Link href="/admin/transactions" className="btn btn-secondary">
            View Transactions
          </Link>
        </div>
      </main>
    </div>
  );
}