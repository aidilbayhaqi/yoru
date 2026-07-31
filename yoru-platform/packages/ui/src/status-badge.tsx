import type { CSSProperties } from "react";

export interface StatusBadgeProps {
  label: string;
  tone?: "ready" | "planned" | "blocked";
}

const styles: Record<NonNullable<StatusBadgeProps["tone"]>, CSSProperties> = {
  ready: {
    color: "#0f5132",
    background: "#d1fae5",
    borderColor: "#a7f3d0",
  },
  planned: {
    color: "#3730a3",
    background: "#eef2ff",
    borderColor: "#c7d2fe",
  },
  blocked: {
    color: "#9a3412",
    background: "#fff7ed",
    borderColor: "#fed7aa",
  },
};

export function StatusBadge({ label, tone = "planned" }: StatusBadgeProps) {
  return (
    <span
      style={{
        ...styles[tone],
        display: "inline-flex",
        alignItems: "center",
        border: "1px solid",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 700,
        letterSpacing: "0.02em",
        padding: "6px 10px",
      }}
    >
      {label}
    </span>
  );
}
