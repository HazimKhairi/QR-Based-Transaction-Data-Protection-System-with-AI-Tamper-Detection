import { ReactNode } from "react";

type StatCardVariant = "primary" | "danger" | "warning" | "success";

interface StatCardProps {
    title: string;
    value: string | number;
    icon?: ReactNode;
    variant?: StatCardVariant;
    trend?: {
        value: string;
        positive?: boolean;
    };
}

export default function StatCard({
    title,
    value,
    icon,
    variant = "primary",
    trend
}: StatCardProps) {
    return (
        <div className={`stat-card stat-card-${variant}`}>
            <div className="flex items-start justify-between relative z-10">
                <div>
                    <p className="text-sm opacity-90 font-medium">{title}</p>
                    <p className="text-2xl font-bold mt-1">{value}</p>
                    {trend && (
                        <p className={`text-xs mt-2 ${trend.positive ? 'text-white/90' : 'text-white/70'}`}>
                            {trend.positive ? "↑" : "↓"} {trend.value}
                        </p>
                    )}
                </div>
                {icon && (
                    <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center">
                        {icon}
                    </div>
                )}
            </div>
        </div>
    );
}
