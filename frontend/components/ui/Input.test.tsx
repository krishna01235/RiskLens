import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import Input from "./Input";

describe("Input", () => {
  it("renders with a label and hint", () => {
    render(<Input id="test-input" label="Email" hint="Enter your email" />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByText("Enter your email")).toBeInTheDocument();
  });

  it("handles user input", async () => {
    const handleChange = vi.fn();
    render(<Input id="test-input" onChange={handleChange} />);
    
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "hello");
    
    expect(handleChange).toHaveBeenCalled();
    expect(input).toHaveValue("hello");
  });

  it("displays error message and applies error styles", () => {
    render(<Input id="test-input" error="Invalid input" />);
    
    expect(screen.getByText("Invalid input")).toBeInTheDocument();
    expect(screen.getByRole("textbox")).toHaveClass("border-brand-breach");
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "true");
  });
});
