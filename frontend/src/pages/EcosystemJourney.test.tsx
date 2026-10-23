import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EcosystemJourney } from "./EcosystemJourney";

afterEach(cleanup);

describe("EcosystemJourney", () => {
  it("covers the whole ecosystem, with connectivity and cameras marked as planned", () => {
    render(<EcosystemJourney hero={<h1>Título</h1>} />);
    expect(screen.getByRole("heading", { name: "Título" })).toBeInTheDocument();
    for (const title of [/Rede onde a roça precisa/, /Olho na propriedade/, /Do cacho ao caixa/, /O mapa que junta tudo/]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getAllByText("Em planejamento")).toHaveLength(2);
    expect(screen.getByText(/onde o trabalho acontece/)).toBeInTheDocument();
    expect(screen.queryByText(/provedor/)).not.toBeInTheDocument();
    for (const step of ["Projeto", "Instalação", "Rede e Wi-Fi", "Gestão e suporte"]) {
      expect(screen.getByText(step)).toBeInTheDocument();
    }
  });

  it("says on screen that the scene is an illustration", () => {
    render(<EcosystemJourney hero={null} />);
    expect(screen.getByText(/não representa uma propriedade real/)).toBeInTheDocument();
  });

  it("lights up the matching scene element when a rail item is hovered", () => {
    render(<EcosystemJourney hero={null} />);
    const camera = screen.getByRole("button", { name: /Câmeras de segurança, ver capítulo/ });
    const grid = screen.getByRole("button", { name: /Conectividade rural, ver capítulo/ });
    expect(camera.getAttribute("class")).toBe("spot");

    fireEvent.pointerEnter(screen.getByRole("button", { name: "Câmeras" }));
    expect(camera.getAttribute("class")).toContain("is-on");
    expect(grid.getAttribute("class")).toContain("is-dim");

    fireEvent.pointerLeave(screen.getByRole("button", { name: "Câmeras" }));
    expect(camera.getAttribute("class")).toBe("spot");
  });

  it("scrolls to the chapter when a scene element or rail item is activated", () => {
    const scrollIntoView = vi.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollIntoView;
    render(<EcosystemJourney hero={null} />);

    fireEvent.click(screen.getByRole("button", { name: "Gestão" }));
    fireEvent.keyDown(screen.getByRole("button", { name: /Câmeras de segurança, ver capítulo/ }), { key: "Enter" });
    expect(scrollIntoView).toHaveBeenCalledTimes(2);
  });
});
