import { useEffect, useState } from "react";

export type Theme = "light" | "dark";
const KEY = "umbra-theme";

function stored(): Theme | null {
  try {
    const value = window.localStorage.getItem(KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null; // storage blocked: follow the system
  }
}

function system(): Theme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** The system theme until the user picks one; the choice is remembered in this browser only. */
export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => stored() ?? system());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const follow = () => {
      if (!stored()) setTheme(system());
    };
    media.addEventListener("change", follow);
    return () => media.removeEventListener("change", follow);
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    try {
      window.localStorage.setItem(KEY, next);
    } catch {
      // not remembered: still applied for this page
    }
    setTheme(next);
  };
  return [theme, toggle];
}
