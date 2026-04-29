interface LineChartProps {
    data?: number[];
    height?: number;
    showGrowth?: boolean;
    growthValue?: string;
}

export default function LineChart({
    data = [90, 70, 75, 60, 65, 55, 40, 45],
    height = 150,
    showGrowth = true,
    growthValue = "85% Growth"
}: LineChartProps) {
    // Generate SVG path from data
    const width = 300;
    const padding = 10;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const maxValue = Math.max(...data);
    const minValue = Math.min(...data);
    const range = maxValue - minValue || 1;

    const points = data.map((value, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth;
        const y = padding + chartHeight - ((value - minValue) / range) * chartHeight;
        return `${x},${y}`;
    }).join(" ");

    // Generate area path for gradient fill
    const areaPath = `M ${padding},${padding + chartHeight} L ${points.split(" ").map(p => p).join(" L ")} L ${padding + chartWidth},${padding + chartHeight} Z`;
    const linePath = `M ${points.split(" ").join(" L ")}`;

    // X-axis labels
    const labels = ["Thu", "Thu", "Fri", "Sat", "Sun", "Mon", "Wed"];

    return (
        <div className="relative">
            {showGrowth && (
                <div className="absolute top-0 right-0 text-xs font-medium text-[var(--success)] flex items-center gap-1">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clipRule="evenodd" />
                    </svg>
                    {growthValue}
                </div>
            )}

            <svg viewBox={`0 0 ${width} ${height + 20}`} className="w-full" style={{ height: height + 40 }}>
                <defs>
                    <linearGradient id="lineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.02" />
                    </linearGradient>
                </defs>

                {/* Grid lines */}
                {[0, 1, 2, 3, 4].map((i) => (
                    <line
                        key={i}
                        x1={padding}
                        y1={padding + (chartHeight / 4) * i}
                        x2={width - padding}
                        y2={padding + (chartHeight / 4) * i}
                        stroke="var(--border-soft)"
                        strokeWidth="1"
                        strokeDasharray="4,4"
                    />
                ))}

                {/* Area fill */}
                <path d={areaPath} fill="url(#lineGradient)" />

                {/* Line */}
                <path
                    d={linePath}
                    fill="none"
                    stroke="var(--primary)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />

                {/* Data points */}
                {data.map((value, index) => {
                    const x = padding + (index / (data.length - 1)) * chartWidth;
                    const y = padding + chartHeight - ((value - minValue) / range) * chartHeight;
                    return (
                        <circle
                            key={index}
                            cx={x}
                            cy={y}
                            r="4"
                            fill="white"
                            stroke="var(--primary)"
                            strokeWidth="2"
                        />
                    );
                })}

                {/* X-axis labels */}
                {labels.map((label, index) => (
                    <text
                        key={index}
                        x={padding + (index / (labels.length - 1)) * chartWidth}
                        y={height + 15}
                        textAnchor="middle"
                        className="fill-[var(--text-muted)]"
                        fontSize="10"
                    >
                        {label}
                    </text>
                ))}
            </svg>
        </div>
    );
}
