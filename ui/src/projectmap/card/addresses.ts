// Route addresses on a card (#106): the part they share is said once, in « Reçoit ».

/** « /api/v1/ » for several routes under it; "" for one route or none. */
export function commonAddress(paths: string[]): string {
  if (paths.length < 2) return "";
  let common = paths.reduce((a, b) => {
    let i = 0;
    while (i < a.length && a[i] === b[i]) i++;
    return a.slice(0, i);
  });
  common = common.slice(0, common.lastIndexOf("/") + 1);
  return common.length > 1 ? common : "";
}

/** « /api/v1/login/access-token » under « /api/v1/ » → « …/login/access-token ». */
export function shortAddress(path: string, under: string): string {
  return under && path.startsWith(under) && path.length > under.length ? `…/${path.slice(under.length)}` : path;
}
