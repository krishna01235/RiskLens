import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Skeleton, { MetricCardSkeleton } from "./Skeleton";

describe("Skeleton", () => {
  it("renders with correct width and height", () => {
    const { container } = render(<Skeleton width="200px" height="50px" />);
    const skeleton = container.firstChild as HTMLElement;
    
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveStyle({ width: "200px", height: "50px" });
    expect(skeleton).toHaveClass("skeleton-shimmer");
  });

  it("renders MetricCardSkeleton correctly", () => {
    const { container } = render(<MetricCardSkeleton />);
    const skeleton = container.firstChild as HTMLElement;
    
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveClass("bg-brand-elevated");
  });
});
