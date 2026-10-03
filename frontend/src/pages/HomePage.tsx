import { Link } from 'react-router-dom';
import './HomePage.css';

const insights = [
  {
    number: '01',
    title: 'Un catálogo legible',
    description: 'Consulta productos organizados por categoría, con sus datos principales en un solo lugar.',
    tone: 'cyan',
  },
  {
    number: '02',
    title: 'Contexto de precios',
    description: 'Explora rangos de precio y compara cómo se distribuye la oferta del catálogo.',
    tone: 'gold',
  },
  {
    number: '03',
    title: 'Señales de interés',
    description: 'Revisa puntuaciones y volumen de reseñas para encontrar los productos con más actividad.',
    tone: 'mint',
  },
];

export default function HomePage() {
  return (
    <div className="home-page">
      <section className="home-hero">
        <div className="home-hero__copy">
          <span className="home-kicker"><span /> INTELIGENCIA DE PRODUCTO</span>
          <h1>VortexAI</h1>
          <p className="home-hero__lead">
            Convierte un catálogo extenso en señales claras para entender productos, precios y atención del mercado.
          </p>
          <div className="home-hero__actions">
            <Link className="home-button home-button--primary" to="/catalogo">Explorar catálogo <span aria-hidden="true">↗</span></Link>
            <Link className="home-button home-button--secondary" to="/admin/dashboard">Ver métricas <span aria-hidden="true">→</span></Link>
          </div>
          <p className="home-hero__note">El panel de métricas requiere una cuenta.</p>
        </div>

        <div className="market-visual" aria-label="Señales analizadas: categoría, precio y reseñas">
          <div className="market-visual__topline">
            <span>LECTURA DE MERCADO</span>
            <span className="market-visual__live"><i /> DATOS DEL CATÁLOGO</span>
          </div>
          <div className="market-visual__chart">
            <div className="market-visual__axis"><span>RESEÑAS</span><span>PRECIO</span><span>CATEGORÍA</span></div>
            <div className="market-visual__bars" aria-hidden="true">
              <span style={{ height: '46%' }} />
              <span style={{ height: '72%' }} />
              <span style={{ height: '58%' }} />
              <span style={{ height: '88%' }} />
              <span style={{ height: '63%' }} />
              <span style={{ height: '96%' }} />
              <span style={{ height: '74%' }} />
              <span style={{ height: '51%' }} />
            </div>
            <div className="market-visual__baseline" />
          </div>
          <div className="market-visual__legend">
            <span><i className="market-visual__dot market-visual__dot--cyan" /> Precio</span>
            <span><i className="market-visual__dot market-visual__dot--gold" /> Puntuación</span>
            <span><i className="market-visual__dot market-visual__dot--coral" /> Reseñas</span>
          </div>
          <div className="market-visual__stamp">OBSERVAR <b>→</b> COMPARAR <b>→</b> ENTENDER</div>
        </div>
      </section>

      <section className="home-insights" aria-labelledby="home-insights-title">
        <div className="home-section-heading">
          <div>
            <span className="home-kicker">PROPÓSITO</span>
            <h2 id="home-insights-title">De datos dispersos a decisiones mejor informadas.</h2>
          </div>
          <p>VortexAI reúne atributos observables del catálogo para facilitar la exploración y la comparación.</p>
        </div>
        <div className="insight-list">
          {insights.map((insight) => (
            <article className={`insight-item insight-item--${insight.tone}`} key={insight.number}>
              <span className="insight-item__number">{insight.number}</span>
              <div>
                <h3>{insight.title}</h3>
                <p>{insight.description}</p>
              </div>
              <span className="insight-item__arrow" aria-hidden="true">↗</span>
            </article>
          ))}
        </div>
      </section>

      <section className="home-access">
        <div>
          <span className="home-kicker">PANEL ANALÍTICO</span>
          <h2>¿Listo para consultar las métricas?</h2>
          <p>Inicia sesión o crea una cuenta para acceder al análisis del catálogo.</p>
        </div>
        <Link className="home-button home-button--primary" to="/acceso">Acceder a mi cuenta <span aria-hidden="true">→</span></Link>
      </section>
    </div>
  );
}