import { ReactNode } from "react";

interface CardProps {
    children: ReactNode;
    className?: string;
    padding?: boolean;
}

interface CardHeaderProps {
    children: ReactNode;
    action?: ReactNode;
}

export function Card({ children, className = "", padding = true }: CardProps) {
    return (
        <div className={`card ${padding ? "card-body" : ""} ${className}`}>
            {children}
        </div>
    );
}

export function CardHeader({ children, action }: CardHeaderProps) {
    return (
        <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-[var(--text-main)]">{children}</h3>
            {action}
        </div>
    );
}

export function CardWithHeader({
    title,
    action,
    children,
    className = ""
}: {
    title: string;
    action?: ReactNode;
    children: ReactNode;
    className?: string;
}) {
    return (
        <div className={`card ${className}`}>
            <div className="card-header flex items-center justify-between">
                <span>{title}</span>
                {action}
            </div>
            <div className="card-body">
                {children}
            </div>
        </div>
    );
}

export default Card;
