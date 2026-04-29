"use client";
import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { apiFetch } from "@/lib/api";
import { ChartBarIcon, ExclamationTriangleIcon, LockClosedIcon, ShieldCheckIcon } from "@heroicons/react/24/outline";

type DashboardStats = {
  total_transactions?: number;
  fraud_alerts?: number;
  secured_qr?: number;
  encryption_enabled?: boolean;
};

type Tx = {
  resident?: string;
  name?: string;
  date?: string;
  amount?: number | string;
  status?: string;
};

type TamperItem = {
  resident?: string;
  reason?: string;
  created_at?: string;
};

export default function UiMockupPage() {
  const [qrUrl, setQrUrl] = useState<string>("");
  const [stats, setStats] = useState<DashboardStats>({});
  const [txs, setTxs] = useState<Tx[]>([]);
  const [alerts, setAlerts] = useState<TamperItem[]>([]);

  useEffect(() => {
    const payload = JSON.stringify({
      type: "secure_demo",
      resident: "Demo User",
      amount: 25.5,
      currency: "MYR",
      ts: new Date().toISOString(),
    });
    QRCode.toDataURL(payload, { width: 220 })
      .then(setQrUrl)
      .catch(() => setQrUrl(""));
  }, []);

  useEffect(() => {
    // Fetch real dashboard stats and transactions for a dynamic mock
    (async () => {
      try {
        const ds = await apiFetch<any>("/api/admin/dashboard", { method: "GET" });
        const dash = ds?.dashboard || ds;
        setStats({
          total_transactions: dash?.transactions?.total,
          fraud_alerts: dash?.transactions?.flagged ?? dash?.security?.anomalies_month,
          secured_qr: dash?.transactions?.completed,
          encryption_enabled: true,
        });
      } catch {}
      try {
        const tr = await apiFetch<any>("/api/admin/transactions", { method: "GET" });
        const items: any[] = tr?.items ?? tr?.transactions ?? [];
        setTxs(
          items.slice(0, 4).map((it: any) => ({
            resident: it?.resident_name ?? it?.user ?? "Resident",
            name: it?.name ?? it?.description ?? "Payment",
            date: it?.date ?? it?.created_at?.slice(11,16) ?? "--:--",
            amount: typeof it?.amount === "number" ? `RM ${it.amount.toFixed(2)}` : it?.amount ?? "RM --",
            status: it?.status ?? (it?.flagged ? "Failed" : "Successful"),
          }))
        );
      } catch {}
      try {
        const al = await apiFetch<any>("/api/admin/tamper-detections", { method: "GET" });
        const items: any[] = al?.items ?? al?.detections ?? [];
        setAlerts(items.slice(0, 3).map((x: any) => ({
          resident: x?.resident ?? x?.user ?? "Resident",
          reason: x?.reason ?? "QR Code Tampering Detected",
          created_at: x?.created_at ?? "",
        })));
      } catch {}
    })();
  }, []);

  return (
    <div className="min-h-[calc(100vh-6rem)] py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Secure QR-Based Transaction System – UI Mockup</h1>
        <p className="text-sm text-gray-600">Minimalist fintech dashboard with resident payment screen</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* Admin Dashboard (Web UI – Left Side) */}
        <div className="rounded-2xl overflow-hidden border bg-white shadow-sm">
          <div className="flex">
            {/* Sidebar */}
            <aside className="w-56 bg-[#132a9a] text-white p-4 flex flex-col">
              <div className="flex items-center gap-2 mb-6">
                <div className="h-8 w-8 rounded-full bg-white/20" />
                <div>
                  <div className="text-sm">Admin</div>
                  <div className="text-xs opacity-80">Encryption Transfer</div>
                </div>
              </div>
              <nav className="flex-1 space-y-2">
                {[
                  { label: "Admin Dashboard", active: true },
                  { label: "Transactions" },
                  { label: "Analytics" },
                  { label: "Residents" },
                  { label: "Reports" },
                  { label: "Settings" },
                ].map((item) => (
                  <div
                    key={item.label}
                    className={`px-3 py-2 rounded-md text-sm cursor-default ${
                      item.active ? "bg-white/20" : "hover:bg-white/10"
                    }`}
                  >
                    {item.label}
                  </div>
                ))}
              </nav>
              <div className="mt-6 flex items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-white/20" />
                <div className="text-xs">
                  <div className="font-medium">System Admin</div>
                  <div className="opacity-80">Nuraisha Saiful</div>
                </div>
              </div>
            </aside>

            {/* Main */}
            <main className="flex-1 p-6">
              {/* Top Header */}
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Admin Dashboard</h2>
                  <div className="text-sm text-gray-600">Secure QR-Based Transaction System</div>
                  <div className="text-xs text-gray-500">Using AES Encryption & AI-Based Fraud Detection</div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-xs text-gray-600">AES</div>
                  <button className="h-9 w-9 rounded-full bg-gray-100" aria-label="notifications" />
                  <div className="h-9 w-9 rounded-full bg-gray-200" />
                </div>
              </div>

              {/* Summary Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
                <SummaryCard title="Total Transactions" value={String(stats.total_transactions ?? "1,230")} color="bg-[#1F4FD8]" icon={<ChartBarIcon className="h-6 w-6" />} />
                <SummaryCard title="Fraud Alerts" value={String(stats.fraud_alerts ?? "8")} color="bg-red-500" icon={<ExclamationTriangleIcon className="h-6 w-6" />} />
                <SummaryCard title="Secured QR" value={String(stats.secured_qr ?? "476")} color="bg-yellow-400" icon={<LockClosedIcon className="h-6 w-6" />} />
                <SummaryCard title="System Encryption" value={(stats.encryption_enabled ?? true) ? "AES Enabled" : "AES Disabled"} color="bg-green-500" icon={<ShieldCheckIcon className="h-6 w-6" />} />
              </div>

              {/* Middle Panels */}
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-6">
                {/* Transactions Table */}
                <div className="xl:col-span-2 rounded-xl border bg-white shadow-sm">
                  <div className="p-4 border-b">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">Transactions</div>
                      <button className="text-sm text-[#1F4FD8]">View All</button>
                    </div>
                  </div>
                  <div className="p-4">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-gray-500">
                          <th className="text-left pb-2">Resident</th>
                          <th className="text-left pb-2">Name</th>
                          <th className="text-left pb-2">Date</th>
                          <th className="text-left pb-2">Amount</th>
                          <th className="text-left pb-2">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {(txs.length ? txs : [
                          { resident: "Nuraisha Saiful", name: "Water Bill", date: "09:24", amount: "RM 0.25", status: "Successful" },
                          { resident: "Acfir in Sertani", name: "Maintenance", date: "08:45", amount: "RM 0.25", status: "Pending" },
                          { resident: "Ali W. Mohen", name: "Parking", date: "10:05", amount: "RM 0.27", status: "Failed" },
                          { resident: "Rohaya Saiful", name: "Security Fee", date: "10:22", amount: "RM 1.20", status: "Failed" },
                        ]).map((t: any, i: number) => (
                          <tr key={i} className="h-10">
                            <td>{t.resident}</td>
                            <td>{t.name}</td>
                            <td>{t.date}</td>
                            <td>{t.amount}</td>
                            <td>
                              <StatusBadge status={t.status} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Fraud Alerts Panel */}
                <div className="rounded-xl border bg-white shadow-sm">
                  <div className="p-4 border-b font-medium">Fraud Alerts</div>
                  <div className="p-4 space-y-3">
                    {(alerts.length ? alerts : [
                      { resident: "Lnessa, Kalisa", reason: "QR Code Tampering Detected", created_at: "" },
                      { resident: "Althda, Fathri", reason: "QR Code Tampering Detected", created_at: "" },
                      { resident: "Tawi, Atika", reason: "QR Code Tampering Detected", created_at: "" },
                    ]).map((a, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium">{a.resident}</div>
                          <div className="text-xs text-red-600">{a.reason}</div>
                        </div>
                        <button className="px-3 py-1.5 text-xs bg-red-500 text-white rounded">Review</button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Analytics */}
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-6">
                <div className="xl:col-span-2 rounded-xl border bg-white shadow-sm p-4">
                  <div className="flex items-center justify-between">
                    <div className="font-medium">Transaction Overview</div>
                    <div className="text-xs text-green-600">85% Growth</div>
                  </div>
                  <LineChart />
                </div>
                <div className="rounded-xl border bg-white shadow-sm p-4">
                  <div className="font-medium mb-2">Encryption Activity</div>
                  <DonutChart percentage={85} />
                  <div className="mt-2 text-xs text-gray-600">AES Encryption</div>
                </div>
              </div>
            </main>
          </div>
        </div>

        {/* Resident QR Payment (Mobile UI – Right Side) */}
        <div className="flex items-center justify-center">
          <div className="w-[360px] rounded-[28px] border bg-white shadow-xl overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-[#1F4FD8] to-[#3a6df3] text-white p-4">
              <div className="text-sm opacity-90">Resident QR Payment</div>
              <div className="text-lg font-semibold">Secure QR Payment</div>
              <div className="text-xs opacity-80">Protected with AES Encryption & AI Fraud Detection</div>
            </div>

            {/* Content */}
            <div className="p-5 space-y-3">
              <div className="text-xs text-gray-600 text-center">Scan the QR Code to make a secure payment</div>
              <div className="flex items-center justify-center">
                {qrUrl ? (
                  <img src={qrUrl} alt="QR" className="h-220 w-220 rounded-lg border shadow-sm" />
                ) : (
                  <div className="h-[220px] w-[220px] rounded-lg bg-gray-100" />
                )}
              </div>
              <div className="flex items-center justify-center gap-2 mt-2">
                <Badge color="bg-green-100 text-green-700" label="AES Encryption Enabled" />
                <Badge color="bg-yellow-100 text-yellow-700" label="AI Fraud Detection Active" />
              </div>

              {/* PIN Input */}
              <div className="mt-4">
                <div className="text-sm text-gray-700 text-center">Enter PIN Code</div>
                <div className="flex items-center justify-center gap-3 mt-2">
                  {[0, 1, 2, 3].map((i) => (
                    <div key={i} className="h-10 w-10 rounded-full bg-gray-100 shadow-inner" />
                  ))}
                </div>
              </div>

              {/* Action */}
              <button className="w-full mt-4 py-3 rounded-xl bg-green-600 text-white font-medium shadow-md">
                CONFIRM PAYMENT
              </button>

              {/* Footer */}
              <div className="text-[11px] text-gray-500 text-center mt-2">
                AES-256 Bit Encryption Enabled • AI Detection Active
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ title, value, color, icon }: { title: string; value: string; color: string; icon: React.ReactNode }) {
  return (
    <div className={`rounded-xl ${color} text-white p-4 shadow-sm`}
      style={{ boxShadow: "0 8px 20px rgba(31,79,216,0.12)" }}>
      <div className="text-sm opacity-90">{title}</div>
      <div className="mt-1 flex items-center gap-2">
        <div className="text-2xl font-semibold">{value}</div>
        <span className="text-xl" aria-hidden>{icon}</span>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: "Successful" | "Pending" | "Failed" | string }) {
  const map: Record<string, string> = {
    Successful: "bg-green-100 text-green-700",
    Pending: "bg-yellow-100 text-yellow-700",
    Failed: "bg-red-100 text-red-700",
  };
  const cls = map[status] || "bg-gray-100 text-gray-600";
  return <span className={`px-2 py-1 rounded text-xs ${cls}`}>{status}</span>;
}

function LineChart() {
  return (
    <svg viewBox="0 0 300 120" className="mt-3 w-full h-32">
      <rect x="0" y="0" width="300" height="120" fill="#f8fafc" />
      <polyline
        fill="none"
        stroke="#1F4FD8"
        strokeWidth="3"
        points="10,90 50,70 90,75 130,60 170,65 210,55 250,40 290,45"
      />
    </svg>
  );
}

function DonutChart({ percentage }: { percentage: number }) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const progress = (percentage / 100) * circumference;
  return (
    <div className="flex items-center justify-center">
      <svg width="140" height="140">
        <circle cx="70" cy="70" r={radius} stroke="#e5e7eb" strokeWidth="14" fill="none" />
        <circle
          cx="70"
          cy="70"
          r={radius}
          stroke="#1F4FD8"
          strokeWidth="14"
          fill="none"
          strokeDasharray={`${progress} ${circumference - progress}`}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
        />
        <text x="70" y="78" textAnchor="middle" className="fill-gray-800" fontSize="18" fontWeight="600">
          {percentage}%
        </text>
      </svg>
    </div>
  );
}

function Badge({ color, label }: { color: string; label: string }) {
  return <span className={`px-2 py-1 rounded text-[11px] ${color}`}>{label}</span>;
}