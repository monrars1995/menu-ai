import { render, screen } from "@testing-library/react";
import { GerarTopBar } from "./GerarTopBar";

describe("GerarTopBar", () => {
  it("renders compact model selector and selected model label", () => {
    render(
      <GerarTopBar
        llmModel="openai-gpt-5.5"
        generationModels={[{ id: "openai-gpt-5.5", label: "GPT-5.5", provider: "openai" }]}
        reviewLlmModel="queen-3.6"
        reviewModels={[{ id: "queen-3.6", label: "Queen 3.6", provider: "openrouter" }]}
        loadingModels={false}
        onChangeModel={() => {}}
        onChangeReviewModel={() => {}}
      />,
    );

    expect(screen.getAllByRole("combobox")).toHaveLength(2);
    const selectedOption = screen.getByRole("option", { name: "GPT-5.5 (openai)" }) as HTMLOptionElement;
    expect(selectedOption.selected).toBe(true);
    const reviewOption = screen.getByRole("option", { name: "Queen 3.6 (openrouter)" }) as HTMLOptionElement;
    expect(reviewOption.selected).toBe(true);
  });
});
