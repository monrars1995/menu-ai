"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "outline" | "ghost" | "danger" | "dark";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variantStyles: Record<Variant, string> = {
  primary: "bg-primary text-white hover:bg-primary-active disabled:opacity-50",
  dark: "bg-surface-dark text-white hover:bg-black disabled:opacity-50",
  secondary: "bg-white text-ink border border-hairline hover:bg-surface-soft",
  outline: "border border-hairline text-ink hover:bg-surface-soft",
  ghost: "text-ink-muted-48 hover:text-ink hover:bg-surface-soft",
  danger: "bg-danger text-white hover:bg-red-700 disabled:opacity-50",
};

const sizeStyles: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-4 text-base",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info-border disabled:pointer-events-none",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    />
  )
);

Button.displayName = "Button";
