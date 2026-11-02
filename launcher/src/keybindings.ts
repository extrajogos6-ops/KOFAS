import catalog from "../../work/kofas/claude/keybindings_catalog.json" with { type: "json" };

export { catalog };
export const groups = [
  {id:"movement", label:"Movimento", description:"Configure as quatro direções.", types:[1,2,3,4]},
  {id:"combat", label:"Combate", description:"Ataques, habilidades e defesa.", types:[5,6,7,8,9,10,11,12,13,22,23]},
  {id:"team", label:"Equipe", description:"Trocas de personagem e apoio.", types:[14,15,25,26,16,17]},
  {id:"shortcuts", label:"Atalhos", description:"Pausa, tela e outros comandos.", types:[18,19,20,21,24]},
];
export function actionsForGroup(id: string): typeof catalog.actions {
  const group = groups.find(group => group.id === id);
  if (!group) throw new Error("Categoria de controles inválida.");
  return group.types.map(type => {
    const action = catalog.actions.find(action => action.type === type);
    if (!action) throw new Error("Ação de teclado ausente.");
    return action;
  });
}
export type KeyPair = [string | null, string | null];
export interface KeyConfig { version: number; bindings: Record<string, KeyPair> }
const supported = new Set(catalog.keys.map(key => key.code));

export function defaults(): KeyConfig {
  const bindings: Record<string, KeyPair> = {};
  for (const action of catalog.actions) bindings[action.id] = [action.defaults[0], action.defaults[1]];
  return { version: 1, bindings };
}

export function validateBindings(value: unknown): KeyConfig {
  if (typeof value !== "object" || value === null || !("version" in value) || value.version !== 1 ||
      !("bindings" in value) || typeof value.bindings !== "object" || value.bindings === null ||
      Object.keys(value).some(key => key !== "version" && key !== "bindings") ||
      Object.keys(value.bindings).length !== catalog.actions.length) throw new Error("Configuração de teclado inválida.");
  const bindings: Record<string, KeyPair> = {};
  const used = new Map<string, string>();
  for (const action of catalog.actions) {
    if (!(action.id in value.bindings)) throw new Error(`Ação ausente: ${action.label}.`);
    const pair: unknown = Object.getOwnPropertyDescriptor(value.bindings, action.id)?.value;
    if (!Array.isArray(pair) || pair.length !== 2) throw new Error(`Teclas inválidas: ${action.label}.`);
    const checked: KeyPair = [null, null];
    for (const slot of [0, 1] as const) {
      const code: unknown = pair[slot];
      if (code !== null && (typeof code !== "string" || !supported.has(code))) throw new Error(`Tecla não reconhecida: ${action.label}.`);
      if (code !== null) {
        const owner = used.get(code);
        if (owner) throw new Error(`Tecla em conflito entre ${owner} e ${action.label}. Remova o conflito antes de salvar.`);
        used.set(code, action.label);
      }
      checked[slot] = code;
    }
    bindings[action.id] = checked;
  }
  return { version: 1, bindings };
}

export function keyFromEvent(event: Pick<KeyboardEvent, "code" | "ctrlKey" | "altKey" | "metaKey" | "shiftKey"> & Partial<Pick<KeyboardEvent, "key" | "location">>): string | null {
  let code = event.code;
  if (!code || code === "Unidentified") {
    if (event.key === "Backspace") code = "Backspace";
    else if (event.key === " ") code = "Space";
    else if (event.key && supported.has(event.key)) code = event.key;
    else if (event.key && /^[a-z]$/i.test(event.key)) code = `Key${event.key.toUpperCase()}`;
    else if (event.key && /^[0-9]$/.test(event.key)) code = `${event.location === 3 ? "Numpad" : "Digit"}${event.key}`;
  }
  if (event.metaKey || (event.ctrlKey && !code.startsWith("Control")) ||
      (event.altKey && !code.startsWith("Alt")) || (event.shiftKey && !code.startsWith("Shift"))) {
    throw new Error("Use uma tecla por atalho, sem combinações.");
  }
  if (code === "Backspace") return null;
  if (!supported.has(code)) throw new Error("Essa tecla não é suportada.");
  return code;
}
