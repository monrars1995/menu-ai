import { render, screen } from "@testing-library/react";
import { ContractUpload } from "./ContractUpload";

vi.mock("@/lib/api", () => ({
  __esModule: true,
  default: {
    contratos: {
      list: vi.fn().mockResolvedValue({ items: [] }),
    },
  },
}));

describe("ContractUpload", () => {
  it("shows upload CTA and saved contracts section", async () => {
    render(<ContractUpload onSelect={() => {}} onUpload={() => {}} />);

    expect(screen.getByText("Enviar contrato")).toBeInTheDocument();
    expect(screen.getByText("Contratos salvos")).toBeInTheDocument();
    expect(await screen.findByText("Nenhum contrato salvo.")).toBeInTheDocument();
  });
});
