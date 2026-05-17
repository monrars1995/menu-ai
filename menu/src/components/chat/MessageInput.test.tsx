import { fireEvent, render, screen } from "@testing-library/react";
import { MessageInput } from "./MessageInput";

describe("MessageInput", () => {
  it("envia mensagem com Enter sem Shift durante generating", () => {
    const onSendMessage = vi.fn();

    render(<MessageInput phase="generating" onSendMessage={onSendMessage} />);

    const input = screen.getByPlaceholderText("Envie uma instrução ou refinamento...");
    fireEvent.change(input, { target: { value: "  Ajustar proteína  " } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    expect(onSendMessage).toHaveBeenCalledTimes(1);
    expect(onSendMessage).toHaveBeenCalledWith("Ajustar proteína");
    expect(input).toHaveValue("");
  });

  it("não envia mensagem com Shift+Enter durante generating", () => {
    const onSendMessage = vi.fn();

    render(<MessageInput phase="generating" onSendMessage={onSendMessage} />);

    const input = screen.getByPlaceholderText("Envie uma instrução ou refinamento...");
    fireEvent.change(input, { target: { value: "Ajustar fibras" } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter", shiftKey: true });

    expect(onSendMessage).not.toHaveBeenCalled();
    expect(input).toHaveValue("Ajustar fibras");
  });
});
