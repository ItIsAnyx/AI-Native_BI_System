export function getAuthDestination(from) {
  const pathname = from?.pathname;
  const validDestination =
    typeof pathname === "string" &&
    pathname.startsWith("/") &&
    !pathname.startsWith("//") &&
    !pathname.includes("\\") &&
    !/^\/(login|register)\/?$/.test(pathname);
  return validDestination
    ? {
        pathname,
        search: typeof from.search === "string" ? from.search : "",
        hash: typeof from.hash === "string" ? from.hash : "",
      }
    : "/";
}
