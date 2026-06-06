/** Background mountain + soft orbs (no interaction) */
export function AmbientLayer() {
  return (
    <div className="ambient" aria-hidden>
      <div className="ambient__scene">
        <div className="ambient__veil" />
        <img
          className="ambient__mountain"
          src="/bg.png"
          onError={(e) => {
            const img = e.currentTarget;
            if (!img.dataset.fallback) {
              img.dataset.fallback = "1";
              img.src = "/bgmountain.webp";
            }
          }}
          alt=""
          decoding="async"
        />
      </div>
      <span className="ambient__orb ambient__orb--a" />
      <span className="ambient__orb ambient__orb--b" />
      <span className="ambient__orb ambient__orb--c" />
    </div>
  );
}
