export function permanentPlaybackFailure(error: unknown): boolean {
  return !(typeof error === "object" && error !== null && "name" in error && error.name === "AbortError");
}
