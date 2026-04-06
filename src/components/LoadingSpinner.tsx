interface LoadingSpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg';
  light?: boolean;
}

export default function LoadingSpinner({ size = 'md', light = false }: LoadingSpinnerProps) {
  const sizeClasses = {
    xs: 'w-4 h-4',
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };

  const colorClass = light ? 'text-white' : 'text-blue-600';

  return (
    <div className={`inline-block ${sizeClasses[size]} animate-spin`}>
      <svg className={`w-full h-full ${colorClass}`} fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    </div>
  );
}