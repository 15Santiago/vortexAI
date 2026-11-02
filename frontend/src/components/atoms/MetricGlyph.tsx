type MetricGlyphProps = {
  symbol: string;
  tone: 'cyan' | 'gold' | 'mint' | 'coral';
};

export function MetricGlyph({ symbol, tone }: MetricGlyphProps) {
  return (
    <span className={`metric-glyph metric-glyph--${tone}`} aria-hidden="true">
      {symbol}
    </span>
  );
}