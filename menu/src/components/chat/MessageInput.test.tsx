import { fireEvent, render, screen } from "@testing-library/react";
import { MessageInput } from "./MessageInput";

describe("MessageInput", () => {
  it("envia mensagem com Enter sem Shift durante hitl-confirm", () => {
    const onSendMessage = vi.fn();

    render(<MessageInput phase="hitl-confirm" onSendMessage={onSendMessage} />);

    const input = screen.getByPlaceholderText("Ajuste os dados antes de confirmar...");
    fireEvent.change(input, { target: { value: "  Ajustar proteína  " } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    expect(onSendMessage).toHaveBeenCalledTimes(1);
    expect(onSendMessage).toHaveBeenCalledWith("Ajustar proteína");
    expect(input).toHaveValue("");
  });

  it("não envia mensagem durante generating", () => {
    const onSendMessage = vi.fn();

    render(<MessageInput phase="generating" onSendMessage={onSendMessage} />);

    const input = screen.getByPlaceholderText("Envie uma instrução ou refinamento...");
    expect(input).toBeDisabled();
    fireEvent.change(input, { target: { value: "Ajustar fibras" } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    expect(onSendMessage).not.toHaveBeenCalled();
    expect(input).toHaveValue("Ajustar fibras");
  });
});
