interface DonutChartProps {
    percentage: number;
    size?: number;
    strokeWidth?: number;
    label?: string;
    sublabel?: string;
}

export default function DonutChart({
    percentage,
    size = 140,
    strokeWidth = 14,
    label,
    sublabel
}: DonutChartProps) {
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const progress = (percentage / 100) * circumference;
    const center = size / 2;

    return (
        <div className="flex flex-col items-center">
            <div className="relative">
                <svg width={size} height={size}>
                    {/* Background circle */}
                    <circle
                        cx={center}
                        cy={center}
                        r={radius}
                        stroke="var(--border-soft)"
                        strokeWidth={strokeWidth}
                        fill="none"
                    />
                    {/* Progress circle */}
                    <circle
                        cx={center}
                        cy={center}
                        r={radius}
                        stroke="var(--primary)"
                        strokeWidth={strokeWidth}
                        fill="none"
                        strokeDasharray={`${progress} ${circumference - progress}`}
                        strokeLinecap="round"
                        transform={`rotate(-90 ${center} ${center})`}
                        className="transition-all duration-500 ease-out"
                    />
                </svg>

                {/* Center text */}
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-2xl font-bold text-[var(--text-main)]">{percentage}%</span>
                    {sublabel && (
                        <span className="text-xs text-[var(--text-muted)]">{sublabel}</span>
                    )}
                </div>
            </div>

            {label && (
                <div className="mt-3 text-center">
                    <p className="text-sm font-medium text-[var(--text-main)]">{label}</p>
                </div>
            )}

            {/* Legend */}
            <div className="mt-3 flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-[var(--primary)]" />
                    <span className="text-[var(--text-muted)]">AES Encryption</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-[var(--border-soft)]" />
                    <span className="text-[var(--text-muted)]">Other</span>
                </div>
            </div>
        </div>
    );
}
