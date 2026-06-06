export const AVATAR_STYLE_OPTIONS: { id: string; label: string }[] = [
  { id: "notionists", label: "Notionists" },
  { id: "lorelei", label: "Lorelei" },
  { id: "avataaars", label: "Avataaars" },
  { id: "bottts", label: "Bottts" },
  { id: "pixel-art", label: "Pixel" },
  { id: "thumbs", label: "Thumbs" },
  { id: "fun-emoji", label: "Emoji" },
  { id: "adventurer", label: "Adventurer" },
  { id: "micah", label: "Micah" },
  { id: "croodles", label: "Croodles" },
];

export function avatarStyleLabel(id: string): string {
  return AVATAR_STYLE_OPTIONS.find((s) => s.id === id)?.label ?? id;
}
