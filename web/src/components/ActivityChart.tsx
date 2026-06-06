import { useMemo } from "react";
import type { ActivityDay } from "../api";

type Props = {
  days: ActivityDay[];
};

function normalizeLastDays(days: ActivityDay[], count = 7): ActivityDay[] {
  const map = new Map(days.map((d) => [d.day, d]));
  const out: ActivityDay[] = [];
  const today = new Date();
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    out.push(
      map.get(key) ?? {
        day: key,
        total: 0,
        verified: 0,
      },
    );
  }
  return out;
}

function dayLabel(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString(undefined, { weekday: "short" });
}

export function ActivityChart({ days }: Props) {
  const series = useMemo(() => normalizeLastDays(days, 7), [days]);
  const max = Math.max(...series.map((d) => d.total), 1);
  const weekTotal = series.reduce((n, d) => n + d.total, 0);
  const weekFound = series.reduce((n, d) => n + d.verified, 0);

  return (
    <section className="activity-chart" aria-label="Lookup activity, last 7 days">
      <div className="activity-chart__head">
        <div className="activity-chart__titles">
          <h2 className="activity-chart__title">Last 7 days</h2>
          <p className="activity-chart__sub">
            {weekTotal > 0
              ? `${weekTotal} runs · ${weekFound} found`
              : "No lookups yet this week"}
          </p>
        </div>
        <div className="activity-chart__legend" aria-hidden>
          <span className="activity-chart__key">
            <i className="activity-chart__swatch activity-chart__swatch--runs" />
            Runs
          </span>
          <span className="activity-chart__key">
            <i className="activity-chart__swatch activity-chart__swatch--found" />
            Found
          </span>
        </div>
      </div>

      <div className="activity-chart__plot">
        <div className="activity-chart__grid" aria-hidden>
          <span />
          <span />
          <span />
        </div>
        <div className="activity-chart__bars">
          {series.map((d, i) => {
            const total = d.total;
            const verified = Math.min(d.verified, total);
            const barPct = total > 0 ? (total / max) * 100 : 0;
            const foundPct = total > 0 ? (verified / total) * 100 : 0;
            const missPct = 100 - foundPct;
            const isToday = i === series.length - 1;

            return (
              <div
                key={d.day}
                className={`activity-chart__col${isToday ? " activity-chart__col--today" : ""}`}
                style={{ "--bar-i": i } as React.CSSProperties}
              >
                <div className="activity-chart__track">
                  {total > 0 ? (
                    <div
                      className="activity-chart__bar"
                      style={{ height: `${Math.max(barPct, 6)}%` }}
                      title={`${total} runs, ${verified} found`}
                    >
                      {missPct > 0 && (
                        <div
                          className="activity-chart__seg activity-chart__seg--runs"
                          style={{ flex: `${missPct} 1 0` }}
                        />
                      )}
                      {foundPct > 0 && (
                        <div
                          className="activity-chart__seg activity-chart__seg--found"
                          style={{ flex: `${foundPct} 1 0` }}
                        />
                      )}
                    </div>
                  ) : (
                    <div className="activity-chart__empty" title="No activity" />
                  )}
                </div>
                <span className="activity-chart__day">{dayLabel(d.day)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
