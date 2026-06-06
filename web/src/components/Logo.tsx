type Props = {
  size?: number;
  className?: string;
  "aria-label"?: string;
};

const DARK_LOGO_SRC = "/logo.png";
const LIGHT_LOGO_SRC = "/lightmodelogo.png";

export function Logo({
  size = 32,
  className = "",
  "aria-label": ariaLabel = "Reachunt",
}: Props) {
  return (
    <span
      className={`logo-mark${className ? ` ${className}` : ""}`}
      style={{ width: size, height: size }}
      role="img"
      aria-label={ariaLabel}
    >
      <img
        src={DARK_LOGO_SRC}
        alt=""
        className="logo-mark__img logo-mark__img--dark"
        decoding="async"
      />
      <img
        src={LIGHT_LOGO_SRC}
        alt=""
        className="logo-mark__img logo-mark__img--light"
        decoding="async"
      />
    </span>
  );
}

export function LogoWordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`logo-wordmark${className ? ` ${className}` : ""}`}>
      <Logo size={28} aria-label="" />
      <span className="logo-wordmark__text">Reachunt</span>
    </span>
  );
}
