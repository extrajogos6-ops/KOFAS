import { invoke } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { listen } from "@tauri-apps/api/event";
import { actionPresentation, createGameAction, createStatusReceiver, type GameStatus } from "./session";
import { permanentPlaybackFailure } from "./media";
import "./style.css";
import { mountSettings } from "./settings";
import { defaults } from "./keybindings";

function element<T extends HTMLElement>(id: string, type: { new(): T }): T {
  const value = document.getElementById(id);
  if (!(value instanceof type)) throw new Error(`Controle ausente: ${id}`);
  return value;
}

const root = element("launcher", HTMLElement);
const video = element("background", HTMLVideoElement);
const poster = element("poster", HTMLImageElement);
const play = element("play", HTMLButtonElement);
const status = element("status", HTMLParagraphElement);
const error = element("error", HTMLParagraphElement);
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const native = "__TAURI_INTERNALS__" in window;
let videoFailed = false;
let current: GameStatus = { phase: "ready", detail: null };
const receive = createStatusReceiver();

function render(value: GameStatus): void {
  current = value;
  const presentation = actionPresentation(value);
  play.disabled = presentation.disabled;
  play.textContent = presentation.label;
  play.setAttribute("aria-label", value.phase === "running" ? "Fechar KOF ALLSTAR" : value.phase === "stopping" ? "Encerrando KOF ALLSTAR" : "Iniciar KOF ALLSTAR");
  status.hidden = !error.hidden;
  status.textContent = value.detail ?? (value.phase === "running" ? "Jogo em execução" : value.phase === "starting" ? "Preparando o jogo…" : value.phase === "stopping" ? "Encerrando o jogo…" : "");
}

function showError(message: string): void {
  error.textContent = message;
  error.hidden = false;
  status.hidden = true;
}

async function connect(): Promise<void> {
  if (!native) return;
  try {
    await listen<unknown>("game-state-changed", event => {
      try { render(receive(event.payload)); }
      catch (value) { showError(value instanceof Error ? value.message : String(value)); }
    });
    await listen<string>("launcher-error", event => { showError(event.payload); });
    render(receive(await invoke<unknown>("game_status")));
  }
  catch (value) { showError(value instanceof Error ? value.message : String(value)); }
}

const action = createGameAction(() => current, async command => {
  if (!native) throw new Error("Abra o executável do launcher para iniciar o jogo.");
  return receive(await invoke<unknown>(command === "stop" ? "stop_game" : "play_game"));
}, render, showError);
play.addEventListener("click", () => { error.hidden = true; status.hidden = false; void action(); });

function fallback(): void {
  videoFailed = true;
  video.pause();
  root.classList.remove("video-ready");
  root.classList.add("fallback");
  poster.src = "./media/fallback.webp";
}

function updatePlayback(): void {
  if (videoFailed) return;
  if (reducedMotion.matches || document.hidden) {
    video.pause();
  } else {
    if (!video.getAttribute("src")) video.src = "./media/background.mp4";
    void video.play().catch(value => { if (permanentPlaybackFailure(value)) fallback(); });
  }
}

video.muted = true;
video.addEventListener("canplay", () => { root.classList.add("video-ready"); });
video.addEventListener("error", fallback);
reducedMotion.addEventListener("change", updatePlayback);
document.addEventListener("visibilitychange", updatePlayback);
element("close", HTMLButtonElement).addEventListener("click", () => {
  if (native) void getCurrentWindow().close();
});
element("minimize", HTMLButtonElement).addEventListener("click", () => {
  if (native) void getCurrentWindow().minimize();
});
document.addEventListener("contextmenu", event => { event.preventDefault(); });
updatePlayback();
void connect();
mountSettings({
  load: async () => native ? invoke<unknown>("get_keybindings") : defaults(),
  save: async config => {
    if (!native) throw new Error("Abra o executável do launcher para salvar os controles.");
    return invoke<unknown>("save_keybindings", { config });
  },
});
