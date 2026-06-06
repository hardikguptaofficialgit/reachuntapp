import { useState } from "react";

const POOL = [
  "stripe.com",
  "figma.com",
  "openai.com",
  "notion.so",
  "linear.app",
  "vercel.com",
  "anthropic.com",
  "ramp.com",
];

type Props = {
  onPick: (line: string) => void;
};

export function SpinExamples({ onPick }: Props) {
  const [spinning, setSpinning] = useState(false);
  const [label, setLabel] = useState("Spin target");

  const spin = () => {
    if (spinning) return;
    setSpinning(true);
    setLabel("Rolling...");

    let ticks = 0;
    const max = 14;
    const id = window.setInterval(() => {
      ticks += 1;
      const pick = POOL[Math.floor(Math.random() * POOL.length)];
      setLabel(`${pick}...`);
      if (ticks >= max) {
        clearInterval(id);
        const final = POOL[Math.floor(Math.random() * POOL.length)];
        setLabel("Spin target");
        setSpinning(false);
        onPick(final);
      }
    }, 80);
  };

  return (
    <button
      type="button"
      className={`spin-examples glass-btn glass-btn--sm${spinning ? " spin-examples--on" : ""}`}
      onClick={spin}
      disabled={spinning}
      title="Random company domain"
    >
      <span className="spin-examples__icon" aria-hidden>
        ◎
      </span>
      {label}
    </button>
  );
}

