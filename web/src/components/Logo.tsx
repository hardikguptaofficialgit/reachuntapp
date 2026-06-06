type Props = {
  size?: number;
  className?: string;
  "aria-label"?: string;
};

const LOGO_SRC = "/logo.png";

export function Logo({
  size = 32,
  className = "",
  "aria-label": ariaLabel = "Anyone Email",
}: Props) {
  return (
    <span
      className={`logo-mark${className ? ` ${className}` : ""}`}
      style={{ width: size, height: size }}
      role="img"
      aria-label={ariaLabel}
    >
      <img src={LOGO_SRC} alt="" className="logo-mark__img" decoding="async" />
    </span>
  );
}

export function LogoWordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`logo-wordmark${className ? ` ${className}` : ""}`}>
      <Logo size={28} aria-label="" />
      <span className="logo-wordmark__text">Anyone Email</span>
    </span>
  );
}
