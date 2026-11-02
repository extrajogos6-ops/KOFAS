export interface GameStatus {
  phase: "ready" | "starting" | "running" | "stopping";
  detail: string | null;
}

export function createStatusReceiver(): (value: unknown) => GameStatus {
  let revision = -1;
  let current: GameStatus = { phase: "ready", detail: null };
  return value => {
    const status = parseStatus(value);
    if (typeof value !== "object" || value === null || !("revision" in value) ||
        typeof value.revision !== "number" || !Number.isSafeInteger(value.revision) || value.revision < 0) {
      throw new Error("Revisão do estado inválida.");
    }
    if (value.revision >= revision) {
      revision = value.revision;
      current = status;
    }
    return current;
  };
}

export function actionPresentation(status: GameStatus): { label: string; disabled: boolean } {
  const labels = { ready: "PLAY", running: "STOP", starting: "ABRINDO…", stopping: "FECHANDO…" };
  return { label: labels[status.phase], disabled: status.phase === "starting" || status.phase === "stopping" };
}

export function createGameAction(
  current: () => GameStatus,
  request: (action: "play" | "stop") => Promise<unknown>,
  publish: (status: GameStatus) => void,
  report: (message: string) => void,
): () => Promise<void> {
  let pending = false;
  return async () => {
    const before = { ...current() };
    if (pending || actionPresentation(before).disabled) return;
    pending = true;
    const action = before.phase === "running" ? "stop" : "play";
    const transition: GameStatus = { phase: action === "stop" ? "stopping" : "starting", detail: null };
    publish(transition);
    try {
      publish(parseStatus(await request(action)));
    } catch (error) {
      if (current() === transition) publish(before);
      report(error instanceof Error ? error.message : String(error));
    } finally {
      pending = false;
    }
  };
}

export function parseStatus(value: unknown): GameStatus {
  if (typeof value !== "object" || value === null || !("phase" in value) || !("detail" in value)) {
    throw new Error("Não foi possível ler o estado do jogo.");
  }
  if ((value.phase !== "ready" && value.phase !== "starting" && value.phase !== "running" && value.phase !== "stopping") ||
      (value.detail !== null && typeof value.detail !== "string")) {
    throw new Error("Estado de inicialização inválido.");
  }
  return { phase: value.phase, detail: value.detail };
}

