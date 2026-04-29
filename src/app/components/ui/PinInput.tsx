"use client";

import { useRef, useState, useEffect, KeyboardEvent, ChangeEvent } from "react";

interface PinInputProps {
    length?: number;
    onComplete?: (pin: string) => void;
    onChange?: (pin: string) => void;
    disabled?: boolean;
    error?: boolean;
}

export default function PinInput({
    length = 4,
    onComplete,
    onChange,
    disabled = false,
    error = false
}: PinInputProps) {
    const [values, setValues] = useState<string[]>(Array(length).fill(""));
    const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

    // Focus first input on mount
    useEffect(() => {
        if (!disabled && inputRefs.current[0]) {
            inputRefs.current[0].focus();
        }
    }, [disabled]);

    const handleChange = (index: number, e: ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value.replace(/\D/g, ""); // Only digits

        if (value.length > 1) {
            // Handle paste
            const pastedValues = value.slice(0, length - index).split("");
            const newValues = [...values];
            pastedValues.forEach((v, i) => {
                if (index + i < length) {
                    newValues[index + i] = v;
                }
            });
            setValues(newValues);

            const nextIndex = Math.min(index + pastedValues.length, length - 1);
            inputRefs.current[nextIndex]?.focus();

            const pin = newValues.join("");
            onChange?.(pin);
            if (pin.length === length) {
                onComplete?.(pin);
            }
            return;
        }

        const newValues = [...values];
        newValues[index] = value;
        setValues(newValues);

        const pin = newValues.join("");
        onChange?.(pin);

        // Move to next input
        if (value && index < length - 1) {
            inputRefs.current[index + 1]?.focus();
        }

        // Check if complete
        if (pin.length === length && !pin.includes("")) {
            onComplete?.(pin);
        }
    };

    const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Backspace" && !values[index] && index > 0) {
            inputRefs.current[index - 1]?.focus();
        }
        if (e.key === "ArrowLeft" && index > 0) {
            inputRefs.current[index - 1]?.focus();
        }
        if (e.key === "ArrowRight" && index < length - 1) {
            inputRefs.current[index + 1]?.focus();
        }
    };

    const handleFocus = (index: number) => {
        inputRefs.current[index]?.select();
    };

    return (
        <div className="flex items-center justify-center gap-3">
            {Array(length).fill(0).map((_, index) => (
                <div
                    key={index}
                    className={`
            relative w-14 h-14 
            ${error ? 'animate-shake' : ''}
          `}
                >
                    <input
                        ref={(el) => { inputRefs.current[index] = el; }}
                        type="password"
                        inputMode="numeric"
                        maxLength={1}
                        value={values[index]}
                        onChange={(e) => handleChange(index, e)}
                        onKeyDown={(e) => handleKeyDown(index, e)}
                        onFocus={() => handleFocus(index)}
                        disabled={disabled}
                        className={`
              w-full h-full text-center text-2xl font-bold
              rounded-xl border-2 transition-all duration-200
              focus:outline-none
              ${error
                                ? 'border-[var(--danger)] bg-[var(--danger-soft)]'
                                : values[index]
                                    ? 'border-[var(--primary)] bg-[var(--primary-soft)]'
                                    : 'border-[var(--border-soft)] bg-white hover:border-[var(--border-medium)]'
                            }
              ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
              focus:border-[var(--primary)] focus:ring-4 focus:ring-[var(--primary-soft)]
            `}
                    />
                    {/* Dot indicator when filled */}
                    {values[index] && (
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                            <div className={`w-3 h-3 rounded-full ${error ? 'bg-[var(--danger)]' : 'bg-[var(--primary)]'}`} />
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
