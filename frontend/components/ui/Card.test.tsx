import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Card from "./Card";

describe("Card", () => {
  it("renders children correctly", () => {
    render(
      <Card>
        <div>Card Content</div>
      </Card>
    );
    expect(screen.getByText("Card Content")).toBeInTheDocument();
  });

  it("applies default padding and classes", () => {
    const { container } = render(<Card>Content</Card>);
    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass("bg-brand-elevated");
    expect(card).toHaveClass("border-brand-border");
    expect(card).toHaveClass("p-6"); // default md padding
  });

  it("applies custom padding", () => {
    const { container } = render(
      <Card padding="none">
        <div>No Padding</div>
      </Card>
    );
    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass("p-0");
  });

  it("applies custom className", () => {
    const { container } = render(
      <Card className="custom-class">
        <div>Custom Class</div>
      </Card>
    );
    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass("custom-class");
  });
});

