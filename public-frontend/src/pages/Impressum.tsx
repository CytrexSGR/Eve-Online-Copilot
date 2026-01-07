export function Impressum() {
  return (
    <div style={{
      maxWidth: '800px',
      margin: '40px auto',
      padding: '40px',
      backgroundColor: '#161b22',
      borderRadius: '12px',
      border: '1px solid #30363d'
    }}>
      <h1 style={{
        fontSize: '2rem',
        marginBottom: '30px',
        color: '#e6edf3'
      }}>
        Impressum
      </h1>

      <section style={{ marginBottom: '30px' }}>
        <h2 style={{
          fontSize: '1.25rem',
          marginBottom: '15px',
          color: '#58a6ff'
        }}>
          Angaben gemäß § 5 TMG
        </h2>
        <p style={{ color: '#e6edf3', lineHeight: '1.6' }}>
          <strong>Infinimind Creations</strong><br />
          Andreas Seeger<br />
          Andechser Straße 42<br />
          82319 Starnberg<br />
          Deutschland
        </p>
      </section>

      <section style={{ marginBottom: '30px' }}>
        <h2 style={{
          fontSize: '1.25rem',
          marginBottom: '15px',
          color: '#58a6ff'
        }}>
          Kontakt
        </h2>
        <p style={{ color: '#e6edf3', lineHeight: '1.6' }}>
          E-Mail: <a href="mailto:office@infinimind-creations.com" style={{ color: '#58a6ff' }}>
            office@infinimind-creations.com
          </a>
        </p>
      </section>

      <section style={{ marginBottom: '30px' }}>
        <h2 style={{
          fontSize: '1.25rem',
          marginBottom: '15px',
          color: '#58a6ff'
        }}>
          Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV
        </h2>
        <p style={{ color: '#e6edf3', lineHeight: '1.6' }}>
          Andreas Seeger<br />
          Andechser Straße 42<br />
          82319 Starnberg
        </p>
      </section>

      <section style={{ marginBottom: '30px' }}>
        <h2 style={{
          fontSize: '1.25rem',
          marginBottom: '15px',
          color: '#58a6ff'
        }}>
          EU-Streitschlichtung
        </h2>
        <p style={{ color: '#8b949e', lineHeight: '1.6', fontSize: '0.95rem' }}>
          Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:{' '}
          <a
            href="https://ec.europa.eu/consumers/odr/"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#58a6ff' }}
          >
            https://ec.europa.eu/consumers/odr/
          </a>
          <br />
          Unsere E-Mail-Adresse finden Sie oben im Impressum.
        </p>
      </section>

      <section style={{ marginBottom: '30px' }}>
        <h2 style={{
          fontSize: '1.25rem',
          marginBottom: '15px',
          color: '#58a6ff'
        }}>
          Verbraucherstreitbeilegung/Universalschlichtungsstelle
        </h2>
        <p style={{ color: '#8b949e', lineHeight: '1.6', fontSize: '0.95rem' }}>
          Wir sind nicht bereit oder verpflichtet, an Streitbeilegungsverfahren vor einer
          Verbraucherschlichtungsstelle teilzunehmen.
        </p>
      </section>

      <section>
        <h2 style={{
          fontSize: '1.25rem',
          marginBottom: '15px',
          color: '#58a6ff'
        }}>
          Haftungsausschluss
        </h2>

        <h3 style={{
          fontSize: '1rem',
          marginTop: '20px',
          marginBottom: '10px',
          color: '#e6edf3'
        }}>
          Haftung für Inhalte
        </h3>
        <p style={{ color: '#8b949e', lineHeight: '1.6', fontSize: '0.95rem', marginBottom: '15px' }}>
          Die Inhalte unserer Seiten wurden mit größter Sorgfalt erstellt. Für die Richtigkeit,
          Vollständigkeit und Aktualität der Inhalte können wir jedoch keine Gewähr übernehmen.
          Als Diensteanbieter sind wir gemäß § 7 Abs.1 TMG für eigene Inhalte auf diesen Seiten
          nach den allgemeinen Gesetzen verantwortlich. Nach §§ 8 bis 10 TMG sind wir als
          Diensteanbieter jedoch nicht verpflichtet, übermittelte oder gespeicherte fremde
          Informationen zu überwachen oder nach Umständen zu forschen, die auf eine rechtswidrige
          Tätigkeit hinweisen.
        </p>

        <h3 style={{
          fontSize: '1rem',
          marginTop: '20px',
          marginBottom: '10px',
          color: '#e6edf3'
        }}>
          Haftung für Links
        </h3>
        <p style={{ color: '#8b949e', lineHeight: '1.6', fontSize: '0.95rem', marginBottom: '15px' }}>
          Unser Angebot enthält Links zu externen Websites Dritter, auf deren Inhalte wir keinen
          Einfluss haben. Deshalb können wir für diese fremden Inhalte auch keine Gewähr übernehmen.
          Für die Inhalte der verlinkten Seiten ist stets der jeweilige Anbieter oder Betreiber der
          Seiten verantwortlich.
        </p>

        <h3 style={{
          fontSize: '1rem',
          marginTop: '20px',
          marginBottom: '10px',
          color: '#e6edf3'
        }}>
          Urheberrecht
        </h3>
        <p style={{ color: '#8b949e', lineHeight: '1.6', fontSize: '0.95rem' }}>
          Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen
          dem deutschen Urheberrecht. Die Vervielfältigung, Bearbeitung, Verbreitung und jede Art
          der Verwertung außerhalb der Grenzen des Urheberrechtes bedürfen der schriftlichen
          Zustimmung des jeweiligen Autors bzw. Erstellers.
        </p>
      </section>

      <div style={{
        marginTop: '40px',
        paddingTop: '20px',
        borderTop: '1px solid #30363d',
        color: '#6e7681',
        fontSize: '0.875rem'
      }}>
        <p>Stand: Januar 2026</p>
      </div>
    </div>
  );
}
