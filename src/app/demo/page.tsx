"use client";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import QRCode from "qrcode";
import Link from "next/link";
import Button from "@/app/components/ui/Button";
import { CardWithHeader } from "@/app/components/ui/Card";
import { StatusBadge } from "@/app/components/ui/Badge";
import {
  ShieldCheckIcon,
  LockClosedIcon,
  CpuChipIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowRightIcon,
  QrCodeIcon,
  BoltIcon,
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

type TamperDetectionInfo = {
  analyzed: boolean;
  anomaly_score: number;
  is_anomaly: boolean;
};

type ProcessResponse = {
  success: boolean;
  message?: string;
  transaction_ref?: string;
  amount?: number;
  currency?: string;
  completed_at?: string;
  error?: string;
  tamper_detection?: TamperDetectionInfo;
};

type ScenarioKind = "normal" | "tampered" | "suspicious";

type ScenarioResult = {
  kind: ScenarioKind;
  status: "running" | "success" | "blocked" | "flagged" | "error";
  title: string;
  detail: string;
  amount?: number;
  transactionRef?: string;
  anomalyScore?: number;
  hashOriginal?: string;
  hashTampered?: string;
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

  // Scenario quick-test state
  const [scenarioResult, setScenarioResult] = useState<ScenarioResult | null>(null);
  const [scenarioRunning, setScenarioRunning] = useState<ScenarioKind | null>(null);

  // Demo page is publicly accessible - no authentication required

  const runScenario = async (kind: ScenarioKind) => {
    setScenarioRunning(kind);
    setError(null);

    const config = {
      normal: { amount: 150.0, description: "Maintenance Fee", title: "Normal Payment" },
      tampered: { amount: 75.0, description: "Pasar Malam Booking", title: "Tampered QR" },
      suspicious: { amount: 9999.99, description: "Unusual Bulk Payment", title: "AI Anomaly Detection" },
    }[kind];

    setScenarioResult({
      kind,
      status: "running",
      title: config.title,
      detail: "Generating encrypted QR code...",
    });

    try {
      // Step 1: generate QR
      const gen = await apiFetch<GenerateQRResponse>("/api/transactions/demo/generate-qr", {
        method: "POST",
        body: {
          amount: config.amount,
          description: config.description,
          transaction_type: kind === "suspicious" ? "other" : "maintenance_fee",
          expires_in_minutes: 30,
        },
      });

      if (kind === "tampered") {
        // Mutate one byte in the encrypted payload, then verify
        const tampered = tamperString(gen.qr_code_data);
        const verifyRes = await apiFetch<VerifyQRResponse>("/api/transactions/demo/verify-qr", {
          method: "POST",
          body: { qr_code_data: tampered, qr_code_hash: gen.qr_code_hash },
        });

        if (verifyRes.tampered || !verifyRes.valid) {
          setScenarioResult({
            kind,
            status: "blocked",
            title: config.title,
            detail: verifyRes.error || "QR integrity check failed — modification detected by SHA-256 hash comparison. Transaction blocked.",
            amount: config.amount,
            transactionRef: gen.transaction_ref,
            hashOriginal: gen.qr_code_hash,
            hashTampered: tampered.slice(0, 32) + "...",
          });
        } else {
          setScenarioResult({
            kind,
            status: "error",
            title: config.title,
            detail: "Unexpected: tampered QR was accepted. Hash check may be misconfigured.",
            amount: config.amount,
            transactionRef: gen.transaction_ref,
          });
        }
        return;
      }

      // Normal + suspicious: process the QR end-to-end
      const proc = await apiFetch<ProcessResponse>("/api/transactions/demo/process", {
        method: "POST",
        body: { qr_code_data: gen.qr_code_data, otp_code: "123456" },
      });

      if (!proc.success) {
        setScenarioResult({
          kind,
          status: "error",
          title: config.title,
          detail: proc.error || proc.message || "Transaction failed",
          amount: config.amount,
          transactionRef: gen.transaction_ref,
        });
        return;
      }

      const isAnomaly = proc.tamper_detection?.is_anomaly === true;

      setScenarioResult({
        kind,
        status: isAnomaly ? "flagged" : "success",
        title: config.title,
        detail: isAnomaly
          ? `AI Isolation Forest flagged this transaction. Amount RM ${config.amount.toLocaleString()} sits outside the trained normal distribution. Anomaly score: ${proc.tamper_detection?.anomaly_score?.toFixed(4)}.`
          : `Payment processed successfully. AES-256 decrypt + SHA-256 integrity OK, AI anomaly score within normal bounds.`,
        amount: proc.amount ?? config.amount,
        transactionRef: proc.transaction_ref ?? gen.transaction_ref,
        anomalyScore: proc.tamper_detection?.anomaly_score,
      });
    } catch (err: any) {
      setScenarioResult({
        kind,
        status: "error",
        title: config.title,
        detail: err.message || "Scenario failed. Is the backend running?",
      });
    } finally {
      setScenarioRunning(null);
    }
  };

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

        {/* Quick Scenarios Panel */}
        <div className="card mb-10 overflow-hidden border-2 border-[var(--primary-soft)]">
          <div className="p-6 border-b border-[var(--border-soft)] flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                <BoltIcon className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-bold">Quick Demo Scenarios</h2>
                <p className="text-xs text-[var(--text-muted)]">One-click end-to-end scenarios for live demonstration</p>
              </div>
            </div>
            {scenarioResult && (
              <Button variant="ghost" size="sm" onClick={() => setScenarioResult(null)}>
                Reset
              </Button>
            )}
          </div>

          <div className="grid md:grid-cols-3 gap-3 p-6">
            <button
              onClick={() => runScenario("normal")}
              disabled={scenarioRunning !== null}
              className="text-left p-4 rounded-xl border-2 border-[var(--success-soft)] hover:border-[var(--success)] hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-white"
            >
              <div className="flex items-center gap-2 mb-2">
                <CheckCircleIcon className="w-6 h-6 text-[var(--success)]" />
                <span className="font-semibold">Normal Payment</span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">RM 150 maintenance fee. Standard amount, valid OTP. Expected: Completed.</p>
              {scenarioRunning === "normal" && (
                <div className="mt-2 text-xs text-[var(--success)]">Running...</div>
              )}
            </button>

            <button
              onClick={() => runScenario("tampered")}
              disabled={scenarioRunning !== null}
              className="text-left p-4 rounded-xl border-2 border-[var(--danger-soft)] hover:border-[var(--danger)] hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-white"
            >
              <div className="flex items-center gap-2 mb-2">
                <ExclamationTriangleIcon className="w-6 h-6 text-[var(--danger)]" />
                <span className="font-semibold">Tampered QR</span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">QR payload mutated after generation. Expected: Hash mismatch, blocked.</p>
              {scenarioRunning === "tampered" && (
                <div className="mt-2 text-xs text-[var(--danger)]">Running...</div>
              )}
            </button>

            <button
              onClick={() => runScenario("suspicious")}
              disabled={scenarioRunning !== null}
              className="text-left p-4 rounded-xl border-2 border-[var(--warning-soft)] hover:border-[var(--warning)] hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-white"
            >
              <div className="flex items-center gap-2 mb-2">
                <CpuChipIcon className="w-6 h-6 text-[var(--warning)]" />
                <span className="font-semibold">Suspicious Activity</span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">RM 9,999.99 unusual amount. Expected: AI Isolation Forest flags it.</p>
              {scenarioRunning === "suspicious" && (
                <div className="mt-2 text-xs text-[var(--warning)]">Running...</div>
              )}
            </button>
          </div>

          {/* Scenario Result */}
          {scenarioResult && (
            <div className={`p-6 border-t border-[var(--border-soft)] ${
              scenarioResult.status === "success" ? "bg-[var(--success-soft)]" :
              scenarioResult.status === "blocked" ? "bg-[var(--danger-soft)]" :
              scenarioResult.status === "flagged" ? "bg-[var(--warning-soft)]" :
              scenarioResult.status === "error" ? "bg-[var(--danger-soft)]" :
              "bg-[var(--background)]"
            }`}>
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0">
                  {scenarioResult.status === "success" && <CheckCircleIcon className="w-10 h-10 text-[var(--success)]" />}
                  {scenarioResult.status === "blocked" && <ExclamationTriangleIcon className="w-10 h-10 text-[var(--danger)]" />}
                  {scenarioResult.status === "flagged" && <CpuChipIcon className="w-10 h-10 text-[var(--warning)]" />}
                  {scenarioResult.status === "error" && <ExclamationTriangleIcon className="w-10 h-10 text-[var(--danger)]" />}
                  {scenarioResult.status === "running" && (
                    <div className="w-10 h-10 rounded-full border-4 border-[var(--primary)] border-t-transparent animate-spin" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h3 className="font-bold text-lg">{scenarioResult.title}</h3>
                    {scenarioResult.status === "success" && <span className="badge badge-success">Completed</span>}
                    {scenarioResult.status === "blocked" && <span className="badge badge-danger">Blocked</span>}
                    {scenarioResult.status === "flagged" && <span className="badge badge-warning">Flagged for Review</span>}
                    {scenarioResult.status === "error" && <span className="badge badge-danger">Error</span>}
                    {scenarioResult.status === "running" && <span className="badge badge-primary">Running</span>}
                  </div>
                  <p className="text-sm text-[var(--text-main)] mb-3">{scenarioResult.detail}</p>

                  <div className="grid sm:grid-cols-2 gap-3 text-xs">
                    {scenarioResult.amount !== undefined && (
                      <div className="flex justify-between p-2 bg-white rounded">
                        <span className="text-[var(--text-muted)]">Amount</span>
                        <span className="font-mono font-semibold">RM {scenarioResult.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                      </div>
                    )}
                    {scenarioResult.transactionRef && (
                      <div className="flex justify-between p-2 bg-white rounded">
                        <span className="text-[var(--text-muted)]">Reference</span>
                        <span className="font-mono">{scenarioResult.transactionRef}</span>
                      </div>
                    )}
                    {scenarioResult.anomalyScore !== undefined && (
                      <div className="flex justify-between p-2 bg-white rounded">
                        <span className="text-[var(--text-muted)]">AI Anomaly Score</span>
                        <span className="font-mono font-semibold">{scenarioResult.anomalyScore.toFixed(4)}</span>
                      </div>
                    )}
                    {scenarioResult.hashOriginal && (
                      <div className="sm:col-span-2 p-2 bg-white rounded space-y-1">
                        <div className="flex justify-between gap-2">
                          <span className="text-[var(--text-muted)]">Original SHA-256</span>
                          <span className="font-mono text-[var(--success)] truncate">{scenarioResult.hashOriginal?.slice(0, 24)}...</span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span className="text-[var(--text-muted)]">After Tamper</span>
                          <span className="font-mono text-[var(--danger)] truncate">{scenarioResult.hashTampered}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Walkthrough header */}
        <div className="text-center mb-6">
          <h2 className="text-xl font-bold text-[var(--text-main)]">Step-by-Step Walkthrough</h2>
          <p className="text-sm text-[var(--text-muted)]">Manual flow for technical inspection of each layer</p>
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
                      <div className="text-[var(--text-muted)] text-xs mt-2 flex items-start gap-2">
                        <CheckCircleIcon className="w-4 h-4 text-[var(--success)] flex-shrink-0 mt-0.5" />
                        <span>
                          <strong>Security Working:</strong> The AI successfully detected the modified QR code and blocked it.
                          This is how the system protects against fraudulent QR codes.
                        </span>
                      </div>
                    </>
                  ) : (
                    <div><strong>Valid:</strong> {String(tamperedVerification.valid)}</div>
                  )}
                </div>
              )}
              {tamperedQrImageUrl && (
                <div>
                  <div className="text-xs font-medium text-[var(--warning)] mb-2 flex items-center gap-1.5">
                    <ExclamationTriangleIcon className="w-3.5 h-3.5" />
                    Simulated Tampered QR (Blocked)
                  </div>
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
                <div className={`p-4 rounded-lg ${processRes.success ? (processRes.tamper_detection?.is_anomaly ? 'bg-[var(--warning-soft)] border border-[var(--warning)]' : 'bg-[var(--success-soft)] border border-[var(--success)]') : 'bg-[var(--danger-soft)]'}`}>
                  {processRes.success ? (
                    <div className="space-y-2">
                      {processRes.tamper_detection?.is_anomaly ? (
                        <div className="font-semibold text-[var(--warning)] flex items-center gap-2">
                          <CpuChipIcon className="w-5 h-5" />
                          Payment Flagged by AI — Admin review required
                        </div>
                      ) : (
                        <div className="font-semibold text-[var(--success)] flex items-center gap-2">
                          <CheckCircleIcon className="w-5 h-5" />
                          Payment Successful!
                        </div>
                      )}
                      <div className="text-sm space-y-1">
                        <div>Transaction: {processRes.transaction_ref}</div>
                        <div>Amount: RM {processRes.amount}</div>
                        {processRes.completed_at && <div>Completed: {processRes.completed_at}</div>}
                        {processRes.tamper_detection && (
                          <div className="pt-2 mt-2 border-t border-[var(--border-soft)] font-mono text-xs">
                            <div>AI anomaly score: {processRes.tamper_detection.anomaly_score?.toFixed(4)}</div>
                            <div>Anomaly: {processRes.tamper_detection.is_anomaly ? "YES" : "no"}</div>
                          </div>
                        )}
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