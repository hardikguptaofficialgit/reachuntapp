import { useState } from "react";

const POOL = [
  "Hardik Gupta — linkitapp.in",
  "Sarah Chen — stripe.com",
  "Alex Rivera — notion.so",
  "Priya Nair — figma.com",
  "Jordan Lee — linear.app",
  "Maya Okonkwo — vercel.com",
  "Chris Park — anthropic.com",
  "Sam Torres — ramp.com",
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
    setLabel("Rolling…");

    let ticks = 0;
    const max = 14;
    const id = window.setInterval(() => {
      ticks += 1;
      const pick = POOL[Math.floor(Math.random() * POOL.length)];
      setLabel(pick.split(" — ")[0] + "…");
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
      title="Random example query"
    >
      <span className="spin-examples__icon" aria-hidden>
        ◎
      </span>
      {label}
    </button>
  );
}
