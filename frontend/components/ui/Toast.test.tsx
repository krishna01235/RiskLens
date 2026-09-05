import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ToastProvider, useToast } from "./Toast";
import userEvent from "@testing-library/user-event";

const TestComponent = () => {
  const { toast } = useToast();
  return (
    <button onClick={() => toast("Test message", "info")}>
      Trigger Toast
    </button>
  );
};

describe("Toast", () => {
  it("shows a toast when triggered", async () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    expect(screen.queryByText("Test message")).not.toBeInTheDocument();
    
    await userEvent.click(screen.getByRole("button", { name: "Trigger Toast" }));
    
    expect(screen.getByText("Test message")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("removes toast after clicking close", async () => {
    render(
      <ToastProvider>
        <TestComponent />
      </ToastProvider>
    );

    await userEvent.click(screen.getByRole("button", { name: "Trigger Toast" }));
    expect(screen.getByText("Test message")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Dismiss notification" }));
    expect(screen.queryByText("Test message")).not.toBeInTheDocument();
  });
});

