import { dicebearUrl } from "../lib/dicebear";

type Props = {
  style: string;
  seed: string;
  size?: number;
  className?: string;
  title?: string;
};

export function UserAvatar({ style, seed, size = 36, className = "", title }: Props) {
  const url = dicebearUrl(style, seed, size * 2);
  const cls = `user-avatar${className ? ` ${className}` : ""}`;
  return (
    <img
      src={url}
      alt=""
      className={cls}
      width={size}
      height={size}
      title={title}
      loading="lazy"
      decoding="async"
    />
  );
}
