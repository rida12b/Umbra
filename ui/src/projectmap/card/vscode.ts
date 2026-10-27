/** `vscode://file/<absolute path>:<line>`: VS Code opens the file at that line (ADR-0007: code opens in
 * VS Code only). A Windows root keeps its drive (`C:/…`); a POSIX root starts with its own slash. */
export function vscodeLink(root: string, file: string, line: number): string {
  const base = root.replaceAll("\\", "/").replace(/\/+$/, "");
  const full = `${base}/${file.replace(/^\/+/, "")}`;
  const path = full.startsWith("/") ? full : `/${full}`;
  return `vscode://file${encodeURI(path)}:${Math.max(1, line)}`;
}
