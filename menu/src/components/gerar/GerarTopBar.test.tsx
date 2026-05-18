import { render, screen } from "@testing-library/react";
import { GerarTopBar } from "./GerarTopBar";

describe("GerarTopBar", () => {
  it("renders compact model selector and selected model label", () => {
    render(
      <GerarTopBar
        llmModel="openai-gpt-5.5"
        llmModels={[{ id: "openai-gpt-5.5", label: "GPT-5.5", provider: "openai" }]}
        loadingModels={false}
        onChangeModel={() => {}}
      />,
    );

    expect(screen.getByText("Modelo")).toBeInTheDocument();
    const selectedOption = screen.getByRole("option", { name: "GPT-5.5 (openai)" }) as HTMLOptionElement;
    expect(selectedOption.selected).toBe(true);
  });
});
