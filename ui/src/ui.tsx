import type { ButtonHTMLAttributes, ReactNode } from "react";

// The few building blocks every view shares, so a heading or a button looks the same everywhere.

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "quiet" | "link" };

export function Button({ variant = "quiet", className = "", ...props }: ButtonProps) {
  const variants = {
    primary: "rounded-md bg-ink px-3 py-1.5 font-medium text-bg hover:opacity-90 disabled:opacity-50",
    quiet: "rounded-md border border-line px-3 py-1.5 text-ink hover:bg-raised disabled:opacity-50",
    link: "text-left text-ink underline decoration-line underline-offset-[3px] hover:decoration-ink",
  };
  return <button type="button" className={`${variants[variant]} ${className}`} {...props} />;
}

/** A whole-area message: loading, empty, error. It always says what to do next when there is something. */
export function StateMessage({ title, children }: { title?: string; children?: ReactNode }) {
  return (
    <div className="flex h-full min-h-60 items-center justify-center p-8">
      <div className="max-w-md text-center text-muted">
        {title && <h1 className="mb-2 text-[17px] font-semibold text-ink">{title}</h1>}
        {children}
      </div>
    </div>
  );
}

export function Command({ children }: { children: ReactNode }) {
  return (
    <pre className="my-3 overflow-x-auto rounded-md border border-line bg-code px-3 py-2 text-left font-mono text-[12.5px] text-ink">
      {children}
    </pre>
  );
}
