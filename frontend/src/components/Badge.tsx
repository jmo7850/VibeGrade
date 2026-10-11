import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '../utils/helpers';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'critical' | 'high' | 'medium' | 'low' | 'info' | 'verified' | 'likely' | 'heuristic' | 'grade';
  size?: 'sm' | 'md' | 'lg';
}

const variantClasses = {
  default: 'bg-dark-700 text-dark-300 border border-dark-600',
  critical: 'bg-red-900/50 text-red-300 border border-red-800',
  high: 'bg-orange-900/50 text-orange-300 border border-orange-800',
  medium: 'bg-yellow-900/50 text-yellow-300 border border-yellow-800',
  low: 'bg-blue-900/50 text-blue-300 border border-blue-800',
  info: 'bg-dark-700 text-dark-400 border border-dark-600',
  verified: 'bg-green-900/50 text-green-300 border border-green-800',
  likely: 'bg-blue-900/50 text-blue-300 border border-blue-800',
  heuristic: 'bg-yellow-900/50 text-yellow-300 border border-yellow-800',
  grade: '', // Handled separately
};

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-0.5 text-xs',
  lg: 'px-3 py-1 text-sm',
};

const gradeClasses = {
  A: 'bg-green-900/50 text-green-300 border border-green-800',
  B: 'bg-brand-900/50 text-brand-300 border border-brand-800',
  C: 'bg-yellow-900/50 text-yellow-300 border border-yellow-800',
  D: 'bg-orange-900/50 text-orange-300 border border-orange-800',
  F: 'bg-red-900/50 text-red-300 border border-red-800',
};

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', size = 'md', children, ...props }, ref) => {
    const isGrade = variant === 'grade';
    const grade = children as string;

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center font-medium rounded-full border',
          sizeClasses[size],
          isGrade ? gradeClasses[grade as keyof typeof gradeClasses] || variantClasses.default : variantClasses[variant],
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';