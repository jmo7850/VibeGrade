import { HTMLAttributes, forwardRef } from 'react';
import { cn } from '../utils/helpers';

interface ProgressBarProps extends HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  showLabel?: boolean;
  color?: 'green' | 'brand' | 'yellow' | 'orange' | 'red';
  size?: 'sm' | 'md' | 'lg';
}

const sizeClasses = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
};

const colorClasses = {
  green: 'bg-green-500',
  brand: 'bg-brand-500',
  yellow: 'bg-yellow-500',
  orange: 'bg-orange-500',
  red: 'bg-red-500',
};

export const ProgressBar = forwardRef<HTMLDivElement, ProgressBarProps>(
  ({ className, value, max = 100, showLabel = false, color = 'brand', size = 'md', ...props }, _ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

    return (
      <div className={cn('w-full', className)} {...props}>
        <div className={cn('progress-bar', sizeClasses[size])} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
          <div
            className={cn('progress-fill transition-all duration-500', colorClasses[color])}
            style={{ width: `${percentage}%` }}
          />
        </div>
        {showLabel && (
          <div className="flex justify-between text-xs text-dark-500 mt-1">
            <span>{value}/{max}</span>
            <span>{percentage.toFixed(0)}%</span>
          </div>
        )}
      </div>
    );
  }
);

ProgressBar.displayName = 'ProgressBar';