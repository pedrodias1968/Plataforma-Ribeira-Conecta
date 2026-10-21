# Referências de Design e Decisões de UX

## 1. SpectraX (https://spectrax.com.br/br)

**URL**: https://spectrax.com.br/br  
**Acesso**: HTML fetch (JavaScript-driven, screenshots não capturadas automaticamente)

### O que observei (baseado no HTML/estrutura)
- Página single-page com Next.js
- Linguagem em português brasileiro
- Foco em "Inteligência Territorial" (mesmo positioning da Ribeira Conecta)
- Presença de Meta Pixel (analytics)

### Decisão de UX que justifica
- **Positioning claro**: "Soluções em Inteligência Territorial" → Ribeira Conecta usa "Inteligência Territorial para Bananicultura"
- **Prova de valor antes de contato**: Landing page explica problema/solução antes de pedir dados do usuário
- **Status transparente**: Se tiver "em desenvolvimento", mostrar explicitamente (não esconder)

### Como adaptar à Ribeira Conecta
- Manter estrutura single-page
- Hero com problema + solução (não apenas apresentação da empresa)
- Mostrar status de funcionalidades: DISPONÍVEL / EM DESENVOLVIMENTO / PLANEJADO

---

## 2. MapBiomas (https://mapbiomas.org/)

**URL**: https://mapbiomas.org/  
**Acesso**: HTML fetch com sucesso

### O que observei
- Hero com estatísticas impactantes (países, km², dados em petabytes)
- Estrutura clara: Quem somos → Rede → Plataforma → Perguntas frequentes
- Uso de imagens de satélite no hero (ex: mapa do Brasil com cobertura)
- Foco em **infraestrutura de dados abertos** (não apenas produto)

### Decisão de UX que justifica
- **Prova social com dados**: "10 anos", "países", "petabytes" criam credibilidade
- **Estrutura de FAQ antes de contato**: Reduz fricção de dúvidas antes do formulário
- **Mapa como elemento central**: Usar mapa não como decoração, mas como prova de valor

### Como adaptar à Ribeira Conecta
- Adicionar estatísticas de impacto (ex: "X propriedades monitoradas", "X milhões de ha")
- FAQ antes do formulário de contato
- Mapa de demonstração no hero (não apenas ilustração)

---

## 3. NASA Landsat (https://landsat.gsfc.nasa.gov/)

**URL**: https://landsat.gsfc.nasa.gov/  
**Acesso**: HTML fetch

### O que observei
- Foco em **educação e科普** (STEM, learning resources)
- Uso de imagens de satélite de alta qualidade
- Seções temáticas: Missão, Dados, Ferramentas, Comunidade

### Decisão de UX que justifica
- **Transparência sobre fontes**: Explicar de onde vem os dados (Landsat, resolução 30m)
- **Educação do usuário**: "Como usar os dados" antes de "comprar"
- **Visualização de qualidade**: Imagens de satélite como ativos principais

### Como adaptar à Ribeira Conecta
- Explicar claramente: "Sentinel-2 (10m)", "SP Águas SIBH", "ANA HidroWebService"
- Seção "Como funciona" (não apenas "nossos recursos")
- Imagens de satélite reais como elementos visuais principais

---

## 4. Limitações de Referências

### Blocados por automação
- Awwwards (403)
- Cagartner (transport error)
- Esri Brasil (transport error)

### Como proceder
- Usar material público (documentação, whitepapers,Case studies)
- Anotar limitação: "Não foi possível analisar visualmente"
- Focar em princípios universais (WCAG, Nielsen) em vez de cópia

---

## 5. Princípios Extraídos (para aplicar)

| Princípio | Como aplicar à Ribeira Conecta |
|-----------|--------------------------------|
| **Prova de valor primeiro** | Hero com problema + solução, não apresentação da empresa |
| **Status honesto** | DISPONÍVEL / EM DESENVOLVIMENTO / PLANEJADO em todas as funcionalidades |
| **Mapa como prova** | Mapa interativo no hero, não decoração |
| **Transparência de fontes** | Identificar cada dado: "SP Águas SIBH", "Sentinel-2", "ANA" |
| **Educação do usuário** | "Como funciona" antes de "entrar" |
| **Estatísticas de impacto** | "X propriedades", "Y milhões de ha", "Z estações hidrológicas" |

---

## 6. Não copiar (antipadrões)

|-site|Por que não copiar|
|------|----------------|
| Awwwards| Design focado em "wow", não em operacionalidade rural|
| Cagartner| Transport error (bloqueio) - não podemos automatizar|
| Esri Brasil| Transport error - bloqueio|

---

**Última atualização**: 2026-10-16  
**Próxima revisão**: Após first prototype e testes com 5 usuários
