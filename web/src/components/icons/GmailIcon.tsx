type Props = { size?: number; className?: string };

/** Monochrome Gmail mark for glass UI */
export function GmailIcon({ size = 18, className }: Props) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden
      fill="currentColor"
    >
      <path d="M4 5.5v13L12 13l8 5.5v-13L12 11 4 5.5zm0-1.8 8 5.5 8-5.5c1.1 0 2 .9 2 2v13c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2v-13c0-1.1.9-2 2-2z" />
      <path d="M4 6.2 12 12l8-5.8V6.2L12 11 4 6.2z" opacity="0.35" />
    </svg>
  );
}
