type Props = {
  lookups: number;
  verified: number;
  hitRate: number;
  today?: number;
};

export function InsightsStrip({ lookups, verified, hitRate, today = 0 }: Props) {
  return (
    <div className="insights" aria-label="Workspace stats">
      {today > 0 && (
        <>
          <div className="insights__item insights__item--today">
            <span className="insights__n">{today}</span>
            <span className="insights__l">today</span>
          </div>
          <div className="insights__sep" />
        </>
      )}
      <div className="insights__item">
        <span className="insights__n">{lookups}</span>
        <span className="insights__l">runs</span>
      </div>
      <div className="insights__sep" />
      <div className="insights__item">
        <span className="insights__n">{verified}</span>
        <span className="insights__l">found</span>
      </div>
      <div className="insights__sep" />
      <div className="insights__item">
        <span className="insights__n">{hitRate}%</span>
        <span className="insights__l">rate</span>
      </div>
    </div>
  );
}
