import { useState, useEffect } from "react";
import "./LandingPage.css";
import { WebGisMock } from "./WebGisMock";

type StatusBadgeProps = {
  status: "disponivel" | "em-desenvolvimento" | "planejado";
  label: string;
};

function StatusBadge({ status, label }: StatusBadgeProps) {
  const styles = {
    disponivel: {
      backgroundColor: "#15803d",
      color: "#f8fafc",
    },
    "em-desenvolvimento": {
      backgroundColor: "#0ea5e9",
      color: "#f8fafc",
    },
    planejado: {
      backgroundColor: "#6b7280",
      color: "#f8fafc",
    },
  };

  return (
    <span style={styles[status]} className="status-badge">
      {label}
    </span>
  );
}

type IconProps = {
  name: string;
  className?: string;
};

function Icon({ name, className = "" }: IconProps) {
  const icons: Record<string, React.ReactNode> = {
    connectivity: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v2" />
        <path d="M12 20v2" />
        <path d="M2 12h2" />
        <path d="M20 12h2" />
        <path d="M4.93 4.93l1.41 1.41" />
        <path d="M17.66 17.66l1.41 1.41" />
        <path d="M4.93 19.07l1.41-1.41" />
        <path d="M17.66 6.34l1.41-1.41" />
      </svg>
    ),
    intelligence: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
        <line x1="12" y1="22.08" x2="12" y2="12" />
      </svg>
    ),
    satellite: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    ),
    flood: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
      </svg>
    ),
    map: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
        <line x1="8" y1="2" x2="8" y2="18" />
        <line x1="16" y1="6" x2="16" y2="22" />
      </svg>
    ),
    erp: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      </svg>
    ),
    service: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
      </svg>
    ),
    geospatial: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <circle cx="12" cy="12" r="10" />
        <path d="M2 12h20" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
    ),
    banana: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <path d="M19.5 7.5c-1-2-2.5-3.5-5.5-3.5-3 0-5.5 1.5-7 3-2 2-3 4.5-3 7.5 0 3 2.5 5.5 6 5.5 4.5 0 7-3.5 9-7 1-1.5 1-2.5 1-3.5 0-1-1-1.5-1-2z" />
        <path d="M14 14c-1 1-2.5 1.5-4 1.5-2.5 0-4-1-5-2" />
      </svg>
    ),
    menu: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <line x1="3" y1="12" x2="21" y2="12" />
        <line x1="3" y1="6" x2="21" y2="6" />
        <line x1="3" y1="18" x2="21" y2="18" />
      </svg>
    ),
    close: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
      </svg>
    ),
  };

  return <div className={`icon icon-${name} ${className}`}>{icons[name] || null}</div>;
}

export function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) element.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="landing-page">
      <header className={`landing-header ${scrolled ? "scrolled" : ""}`}>
        <div className="container">
          <div className="logo" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
            Ribeira Conecta
          </div>
          <nav className={`nav ${mobileMenuOpen ? "open" : ""}`}>
            <a onClick={() => scrollToSection("hero")}>Início</a>
            <a onClick={() => scrollToSection("problema")}>Problema</a>
            <a onClick={() => scrollToSection("ecossistema")}>Ecossistema</a>
            <a onClick={() => scrollToSection("geoespacial")}>Geoespacial</a>
            <a onClick={() => scrollToSection("hydrology")}>Hidrologia</a>
            <a onClick={() => scrollToSection("erp")}>ERP Bananicultura</a>
            <a onClick={() => scrollToSection("servicos")}>Serviços</a>
            <a onClick={() => scrollToSection("sobre")}>Sobre</a>
            <a onClick={() => scrollToSection("contato")}>Contato</a>
          </nav>
          <button
            className="mobile-menu-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Menu"
          >
            <Icon name={mobileMenuOpen ? "close" : "menu"} />
          </button>
          <a href="mailto:contato@ribeiraconecta.com.br" className="btn-primary">
            Fale conosco
          </a>
        </div>
      </header>

      <section id="hero" className="hero">
        <div className="container">
          <p className="eyebrow">Conectividade, Inteligência e Gestão</p>
          <h1>do cacho à mesa</h1>
          <p className="subtitle">
            Plataforma de inteligência territorial para bananicultores do Vale do Ribeira.
            Monitoramento satelital, risco de inundação e gestão operacional em um só lugar.
          </p>
          <div className="hero-actions">
            <a href="mailto:contato@ribeiraconecta.com.br" className="btn-primary">
              Agendar demonstração
            </a>
            <a href="#ecossistema" className="btn-secondary">
              Conhecer a plataforma
            </a>
          </div>
          <WebGisMock />
        </div>
      </section>

      <section id="problema" className="problem">
        <div className="container">
          <h2>O desafio do bananicultor</h2>
          <div className="problem-cards">
            <div className="problem-card">
              <div className="problem-icon">
                <Icon name="flood" className="icon-32" />
              </div>
              <h3>Risco de Inundação</h3>
              <p>O Vale do Ribeira é suscetível a eventos de enchente que podem destruir plantações e infraestrutura.</p>
            </div>
            <div className="problem-card">
              <div className="problem-icon">
                <Icon name="satellite" className="icon-32" />
              </div>
              <h3>Falta de Monitoramento</h3>
              <p>Monitoramento manual de áreas extensas é inviável e não permite antecipação de problemas.</p>
            </div>
            <div className="problem-card">
              <div className="problem-icon">
                <Icon name="connectivity" className="icon-32" />
              </div>
              <h3>Conectividade Rural</h3>
              <p>Áreas remotas enfrentam limitações de conectividade que dificultam o acesso a informações em tempo real.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="ecossistema" className="ecosystem">
        <div className="container">
          <h2>Ecossistema de valor</h2>
          <p className="subtitle">
            Soluções integradas para transformar sua propriedade em uma operação inteligente.
            Cada item classificado conforme estado de desenvolvimento comprovado.
          </p>
          <div className="ecosystem-grid">
            <div className="ecosystem-item">
              <div className="ecosystem-icon">
                <Icon name="connectivity" className="icon-48" />
              </div>
              <h3>Conectividade Rural</h3>
              <p>Soluções de conectividade para áreas remotas do Vale do Ribeira.</p>
              <StatusBadge status="disponivel" label="Disponível" />
            </div>
            <div className="ecosystem-item">
              <div className="ecosystem-icon">
                <Icon name="satellite" className="icon-48" />
              </div>
              <h3>Monitoramento Satelital</h3>
              <p>Observação contínua da vegetação, solo e condições ambientais.</p>
              <StatusBadge status="disponivel" label="Disponível" />
            </div>
            <div className="ecosystem-item">
              <div className="ecosystem-icon">
                <Icon name="intelligence" className="icon-48" />
              </div>
              <h3>Inteligência Territorial</h3>
              <p>Análise de dados geoespaciais para tomada de decisão operacional.</p>
              <StatusBadge status="disponivel" label="Disponível" />
            </div>
            <div className="ecosystem-item">
              <div className="ecosystem-icon">
                <Icon name="flood" className="icon-48" />
              </div>
              <h3>Risco de Inundação</h3>
              <p>Monitoramento hidrológico e avaliação de exposição a inundações.</p>
              <StatusBadge status="disponivel" label="Disponível" />
            </div>
            <div className="ecosystem-item">
              <div className="ecosystem-icon">
                <Icon name="geospatial" className="icon-48" />
              </div>
              <h3>Gestão de Talhões</h3>
              <p>Boundary management, digitalização e análise espacial de áreas.</p>
              <StatusBadge status="disponivel" label="Disponível" />
            </div>
            <div className="ecosystem-item">
              <div className="ecosystem-icon">
                <Icon name="erp" className="icon-48" />
              </div>
              <h3>ERP Bananicultura</h3>
              <p>Sistema especializado para gestão da cadeia bananeira, em construção.</p>
              <StatusBadge status="em-desenvolvimento" label="Em desenvolvimento" />
            </div>
            <div className="ecosystem-item">
              <div className="ecosystem-icon">
                <Icon name="service" className="icon-48" />
              </div>
              <h3>Serviços Profissionais</h3>
              <p>Consultoria especializada em inteligência territorial agrícola.</p>
              <StatusBadge status="disponivel" label="Disponível" />
            </div>
          </div>
        </div>
      </section>

      <section id="geoespacial" className="geospatial">
        <div className="container">
          <h2>Geoespacial de classe Google Earth</h2>
          <p className="subtitle">
            Plataforma geoespacial com capacidades avançadas para visualização e análise territorial.
            Não uma cópia, mas uma solução focada em operação agrícola.
          </p>
          <div className="geospatial-grid">
            <div className="geospatial-feature">
              <Icon name="map" className="icon-32" />
              <h3>Mapa 2D e 3D</h3>
              <p>Visualização interativa do território com camadas geoespaciais.</p>
              <StatusBadge status="disponivel" label="Disponível" />
            </div>
            <div className="geospatial-feature">
              <Icon name="satellite" className="icon-32" />
              <h3>Camadas Satelitais</h3>
              <p>Acesso a imagens de satélite para monitoramento da vegetação.</p>
              <StatusBadge status="disponivel" label="Disponível" />
            </div>
            <div className="geospatial-feature">
              <Icon name="connectivity" className="icon-32" />
              <h3>Geoprocessamento</h3>
              <p>Cálculos de distância, área e análise espacial de propriedades.</p>
              <StatusBadge status="disponivel" label="Disponível" />
            </div>
          </div>
          <div className="geospatial-demo">
            <div className="demo-overlay">
              <span className="demo-label">Ilustração</span>
              <p>
                A imagem no topo da página é uma ilustração com dados fictícios, no estilo da tela de mapa do app.
                Os dados reais de cada propriedade aparecem só depois do login, a partir do limite cadastrado
                e das fontes de satélite disponíveis.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="hydrology" className="hydrology">
        <div className="container">
          <h2>Hidrologia e monitoramento de rios</h2>
          <p className="subtitle">
            Integração com fontes oficiais para monitoramento contínuo de nível de rios,
            pluviometria e vazão.
          </p>
          <div className="hydrology-info">
            <div className="hydrology-item">
              <div className="hydrology-header">
                <Icon name="flood" className="icon-32" />
                <h3>Monitoramento de Nível de Rios</h3>
              </div>
              <p>
                Integração com SP Águas SIBH e ANA HidroWebService para dados oficiais.
                <StatusBadge status="disponivel" label="Disponível" />
              </p>
            </div>
            <div className="hydrology-item">
              <div className="hydrology-header">
                <Icon name="satellite" className="icon-32" />
                <h3>Pluviometria</h3>
              </div>
              <p>
                Dados de chuva em tempo real de estações automatizadas da região.
                <StatusBadge status="disponivel" label="Disponível" />
              </p>
            </div>
            <div className="hydrology-item">
              <div className="hydrology-header">
                <Icon name="connectivity" className="icon-32" />
                <h3>Vazão e Cota</h3>
              </div>
              <p>
                Monitoramento de vazão e cota de rios para avaliação de risco.
                <StatusBadge status="disponivel" label="Disponível" />
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="erp" className="erp">
        <div className="container">
          <h2>ERP Especializado em Bananicultura</h2>
          <p className="subtitle">
            Sistema de gestão em desenvolvimento para a cadeia produtiva bananeira, desenhado a partir
            de entrevistas com produtores. Os módulos abaixo estão em construção, sem data de entrega assumida.
          </p>
          <div className="erp-preview">
            {[
              ["Colheita por talhão", "Cachos, caixas, peso e descarte por talhão."],
              ["Adubação e insumos", "O que foi aplicado, onde e quando."],
              ["Estoque de insumos", "Entradas, saídas e saldo por produto."],
              ["Custos por talhão e por kg", "Custo registrado; sem dado, mostra “sem registro”."],
              ["Vendas e recebimentos", "Comprador, valor a receber e prazo de pagamento."],
              ["Relatório para o contador", "Vendas e custos do período em planilha."],
            ].map(([title, text]) => (
              <div className="erp-module" key={title}>
                <Icon name="erp" className="icon-48" />
                <h3>{title}</h3>
                <p>{text}</p>
                <StatusBadge status="em-desenvolvimento" label="Em desenvolvimento" />
              </div>
            ))}
          </div>
          <div className="erp-note">
            <strong>Nota:</strong> o ERP Bananicultura ainda não está disponível para contratação.
            Dado que o produtor não anotou aparece como “sem registro”; o sistema não inventa valores.
          </div>
        </div>
      </section>

      <section id="servicos" className="services">
        <div className="container">
          <h2>Serviços Profissionais</h2>
          <p className="subtitle">
           Consultoria especializada em inteligência territorial aplicada à agricultura.
            Transformamos dados em decisão operacional.
          </p>
          <div className="services-list">
            <div className="service-item">
              <h3>Análise Territorial</h3>
              <p>Diagnóstico geoespacial de propriedades rurais com foco em riscos ambientais e oportunidades operacionais.</p>
            </div>
            <div className="service-item">
              <h3>Implementação de Monitoring</h3>
              <p>Configuração de sensores, câmeras e sistemas de coleta de dados para monitoramento contínuo.</p>
            </div>
            <div className="service-item">
              <h3>Capacitação e Treinamento</h3>
              <p>Workshops e treinamentos para equipes operacionais utilizarem a plataforma de forma eficaz.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="sobre" className="about">
        <div className="container">
          <h2>Sobre a Ribeira Conecta</h2>
          <div className="about-content">
            <div className="about-text">
              <p>
                A Ribeira Conecta é uma startup de inteligência territorial focada no Vale do Ribeira,
                região produtora de banana reconhecida nacionalmente. Nossa missão é levar tecnologia
                de ponta às propriedades rurais, transformando dados em decisão operacional.
              </p>
              <p>
                Especialistas em geoespacial, sensoriamento remoto e inteligência de dados,
                trabalhamos para construir a próxima geração de ferramentas para agricultura
                de precisão e sustentabilidade.
              </p>
            </div>
            <div className="about-map">
              <div className="map-placeholder">
                <Icon name="map" className="icon-64" />
                <p>Vale do Ribeira</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="contato" className="contact">
        <div className="container">
          <h2>Converse com nossa equipe</h2>
          <p className="subtitle">
            Quer saber como a Ribeira Conecta pode transformar sua operação?
            Entre em contato para agendar uma demonstração personalizada.
          </p>
          <div className="contact-info">
            <a href="mailto:contato@ribeiraconecta.com.br" className="contact-btn">
              contato@ribeiraconecta.com.br
            </a>
          </div>
          <form className="contact-form">
            <div className="form-group">
              <label htmlFor="name">Nome</label>
              <input type="text" id="name" name="name" required />
            </div>
            <div className="form-group">
              <label htmlFor="email">E-mail</label>
              <input type="email" id="email" name="email" required />
            </div>
            <div className="form-group">
              <label htmlFor="phone">Telefone</label>
              <input type="tel" id="phone" name="phone" />
            </div>
            <div className="form-group">
              <label htmlFor="message">Mensagem</label>
              <textarea id="message" name="message" rows={5} required />
            </div>
            <button type="submit" className="btn-primary">
              Enviar mensagem
            </button>
          </form>
        </div>
      </section>

      <footer className="footer">
        <div className="container">
          <div className="footer-content">
            <div className="footer-logo">
              <h3>Ribeira Conecta</h3>
              <p>Inteligência territorial para bananicultura</p>
            </div>
            <div className="footer-links">
              <div className="footer-section">
                <h4>Plataforma</h4>
                <a href="#geoespacial">Geoespacial</a>
                <a href="#hydrology">Hidrologia</a>
                <a href="#erp">ERP Bananicultura</a>
              </div>
              <div className="footer-section">
                <h4>Empresa</h4>
                <a href="#sobre">Sobre</a>
                <a href="#servicos">Serviços</a>
                <a href="#contato">Contato</a>
              </div>
              <div className="footer-section">
                <h4>Contato</h4>
                <a href="mailto:contato@ribeiraconecta.com.br">contato@ribeiraconecta.com.br</a>
              </div>
            </div>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2026 Ribeira Conecta. Todos os direitos reservados.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
