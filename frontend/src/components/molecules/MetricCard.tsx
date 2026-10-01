import MetricGlyph from '../atoms/MetricGlyph';

type MetricCardProps = {
  label: string;
  value: string;
  detail: string;
  symbol: string;
  tone: 'cyan' | 'gold' | 'mint' | 'coral';
};

export default function MetricCard({ label, value, detail, symbol, tone }: MetricCardProps) {
  return (
    <article className="metric-card">
      <div className="metric-card__topline">
        <span className="metric-card__label">{label}</span>
        <MetricGlyph symbol={symbol} tone={tone} />
      </div>
      <strong className="metric-card__value">{value}</strong>
      <span className="metric-card__detail">{detail}</span>
    </article>
  );
}