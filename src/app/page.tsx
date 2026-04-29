import Link from "next/link";
import {
  ShieldCheckIcon,
  LockClosedIcon,
  CpuChipIcon,
  QrCodeIcon,
  ArrowRightIcon,
  CheckCircleIcon,
} from "@heroicons/react/24/outline";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Navigation */}
      <nav className="bg-white border-b border-[var(--border-soft)] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
              <ShieldCheckIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="font-bold text-[var(--text-main)]">QR Transaction</div>
              <div className="text-xs text-[var(--text-muted)]">Secure Payment System</div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/demo" className="text-sm text-[var(--text-muted)] hover:text-[var(--primary)] transition-colors">
              Demo
            </Link>
            <Link href="/resident/payment" className="text-sm text-[var(--text-muted)] hover:text-[var(--primary)] transition-colors">
              Resident Portal
            </Link>
            <Link href="/login" className="btn btn-primary">
              Admin Login
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 gradient-primary opacity-5" />
        <div className="max-w-7xl mx-auto px-6 py-24">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--primary-soft)] text-[var(--primary)] text-sm font-medium">
                <ShieldCheckIcon className="w-4 h-4" />
                AES-256 Encryption Protected
              </div>

              <h1 className="text-5xl font-bold text-[var(--text-main)] leading-tight">
                Secure QR-Based
                <span className="text-[var(--primary)]"> Transaction</span>
                <br />Data Protection
              </h1>

              <p className="text-lg text-[var(--text-muted)] max-w-lg">
                Protect your QR code payment transactions from fraud and tampering using
                advanced AES encryption, AI-based fraud detection, and secure 2FA verification.
              </p>

              <div className="flex flex-wrap gap-4">
                <Link href="/admin/dashboard" className="btn btn-primary btn-lg">
                  <span>Go to Dashboard</span>
                  <ArrowRightIcon className="w-5 h-5" />
                </Link>
                <Link href="/demo" className="btn btn-secondary btn-lg">
                  View Demo
                </Link>
              </div>

              {/* Trust Indicators */}
              <div className="flex items-center gap-6 pt-4">
                <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                  <CheckCircleIcon className="w-5 h-5 text-[var(--success)]" />
                  256-bit Encryption
                </div>
                <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                  <CheckCircleIcon className="w-5 h-5 text-[var(--success)]" />
                  AI Fraud Detection
                </div>
                <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                  <CheckCircleIcon className="w-5 h-5 text-[var(--success)]" />
                  2FA Enabled
                </div>
              </div>
            </div>

            {/* Hero Visual */}
            <div className="relative">
              <div className="absolute -top-10 -right-10 w-72 h-72 bg-[var(--primary)] rounded-full opacity-10 blur-3xl" />
              <div className="absolute -bottom-10 -left-10 w-72 h-72 bg-[var(--success)] rounded-full opacity-10 blur-3xl" />

              <div className="relative bg-white rounded-3xl p-8 shadow-2xl border border-[var(--border-soft)]">
                <div className="text-center mb-6">
                  <h3 className="font-semibold text-lg">Secure Payment Portal</h3>
                  <p className="text-sm text-[var(--text-muted)]">Scan to pay securely</p>
                </div>

                <div className="flex justify-center mb-6">
                  <div className="w-48 h-48 rounded-2xl bg-[var(--background)] border-2 border-dashed border-[var(--border-soft)] flex items-center justify-center">
                    <QrCodeIcon className="w-24 h-24 text-[var(--primary)]" />
                  </div>
                </div>

                <div className="flex justify-center gap-2">
                  <span className="badge badge-success">AES Encrypted</span>
                  <span className="badge badge-warning">AI Protected</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-[var(--text-main)] mb-4">
              Enterprise-Grade Security Features
            </h2>
            <p className="text-[var(--text-muted)] max-w-2xl mx-auto">
              Our system implements multiple layers of security to ensure your transactions are protected at every step.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: LockClosedIcon,
                title: "AES-256 Encryption",
                description: "Military-grade encryption protects all QR code data and transaction information in transit and at rest.",
                color: "primary",
              },
              {
                icon: CpuChipIcon,
                title: "AI Fraud Detection",
                description: "Machine learning algorithms analyze transaction patterns in real-time to detect and prevent fraudulent activities.",
                color: "success",
              },
              {
                icon: ShieldCheckIcon,
                title: "2FA Verification",
                description: "Two-factor authentication ensures only authorized users can complete sensitive transactions.",
                color: "warning",
              },
            ].map((feature, i) => (
              <div key={i} className="card hover:shadow-lg transition-shadow">
                <div className="p-8">
                  <div className={`w-14 h-14 rounded-2xl bg-[var(--${feature.color}-soft)] flex items-center justify-center mb-6`}>
                    <feature.icon className={`w-7 h-7 text-[var(--${feature.color})]`} />
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                  <p className="text-[var(--text-muted)]">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 gradient-primary">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-white mb-6">
            Ready to Secure Your Transactions?
          </h2>
          <p className="text-white/80 text-lg mb-8 max-w-2xl mx-auto">
            Get started with our secure QR-based transaction system today.
            Experience enterprise-grade security with easy implementation.
          </p>
          <div className="flex justify-center gap-4">
            <Link href="/admin/dashboard" className="btn bg-white text-[var(--primary)] hover:bg-gray-100">
              Access Dashboard
            </Link>
            <Link href="/demo" className="btn bg-white/20 text-white border border-white/30 hover:bg-white/30">
              Try Demo
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[var(--text-main)] text-white py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center">
                <ShieldCheckIcon className="w-6 h-6" />
              </div>
              <div>
                <div className="font-bold">QR Transaction Protection</div>
                <div className="text-xs text-white/60">Secure Payment System</div>
              </div>
            </div>
            <div className="text-sm text-white/60">
              © 2026 Secure QR-Based Transaction System. Final Year Project.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
