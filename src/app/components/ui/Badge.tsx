type BadgeVariant = "success" | "warning" | "danger" | "primary" | "default";

interface BadgeProps {
    children: React.ReactNode;
    variant?: BadgeVariant;
    size?: "sm" | "md";
}

const variantClasses: Record<BadgeVariant, string> = {
    success: "badge-success",
    warning: "badge-warning",
    danger: "badge-danger",
    primary: "badge-primary",
    default: "bg-gray-100 text-gray-600",
};

export default function Badge({
    children,
    variant = "default",
    size = "md"
}: BadgeProps) {
    const sizeClasses = size === "sm" ? "text-[10px] px-2 py-0.5" : "text-xs px-3 py-1";

    return (
        <span className={`badge ${variantClasses[variant]} ${sizeClasses}`}>
            {children}
        </span>
    );
}

// Status-specific badge for transactions
export function StatusBadge({ status }: { status: string }) {
    const normalizedStatus = status.toLowerCase();

    let variant: BadgeVariant = "default";
    if (normalizedStatus === "successful" || normalizedStatus === "completed" || normalizedStatus === "success") {
        variant = "success";
    } else if (normalizedStatus === "pending" || normalizedStatus === "processing") {
        variant = "warning";
    } else if (normalizedStatus === "failed" || normalizedStatus === "rejected" || normalizedStatus === "cancelled") {
        variant = "danger";
    }

    return <Badge variant={variant}>{status}</Badge>;
}
