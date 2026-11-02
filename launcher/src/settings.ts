import { catalog, defaults, groups, actionsForGroup, keyFromEvent, validateBindings, type KeyConfig } from "./keybindings";

interface Transport { load(): Promise<unknown>; save(config: KeyConfig): Promise<unknown> }

export function mountSettings(transport: Transport): void {
  function find<T extends HTMLElement>(id: string, type: { new(): T }): T {
    const element = document.getElementById(id);
    if (!(element instanceof type)) throw new Error(`Controle ausente: ${id}`);
    return element;
  }
  const dialog = find("settings-dialog", HTMLDialogElement);
  const rows = find("key-rows", HTMLTableSectionElement);
  const error = find("keys-error", HTMLParagraphElement);
  const status = find("keys-status", HTMLParagraphElement);
  const save = find("keys-save", HTMLButtonElement);
  const restore = find("keys-defaults", HTMLButtonElement);
  const cancel = find("keys-cancel", HTMLButtonElement);
  const close = find("settings-close", HTMLButtonElement);
  const navigation = find("key-groups", HTMLElement);
  const panel = find("keys-panel", HTMLElement);
  const category = find("keys-category", HTMLHeadingElement);
  const description = find("keys-description", HTMLParagraphElement);
  const labels = new Map(catalog.keys.map(key => [key.code, key.label]));
  let draft: KeyConfig | null = null;
  let busy = false;
  let selected = groups[0];
  let capture: { id: string; slot: 0 | 1; button: HTMLButtonElement } | null = null;

  function labelKey(button: HTMLButtonElement, id: string, slot: 0 | 1): void {
    const action = catalog.actions.find(action => action.id === id);
    if (!action || !draft) return;
    const label = labels.get(draft.bindings[id][slot] ?? "");
    button.textContent = label ?? "Adicionar";
    button.classList.toggle("unassigned", !label);
    button.setAttribute("aria-label", `${action.label}, tecla ${slot + 1}: ${label ?? "sem atribuição"}`);
  }

  function report(value: unknown): void {
    error.textContent = value instanceof Error ? value.message : String(value);
    error.hidden = false;
  }
  function controls(): void {
    save.disabled = busy || draft === null || capture !== null;
    restore.disabled = busy;
    cancel.disabled = busy;
    close.disabled = busy;
    for (const button of navigation.querySelectorAll("button")) button.disabled = busy;
    for (const button of rows.querySelectorAll("button")) button.disabled = busy;
  }
  function clearCapture(): void {
    if (capture && draft) {
      labelKey(capture.button, capture.id, capture.slot);
      capture.button.classList.remove("capturing");
      capture.button.setAttribute("aria-pressed", "false");
    }
    capture = null;
    controls();
  }
  function render(): void {
    clearCapture();
    rows.replaceChildren();
    if (!draft) { controls(); return; }
    for (const action of actionsForGroup(selected.id)) {
      const row = document.createElement("tr");
      const label = document.createElement("th");
      label.scope = "row";
      label.textContent = action.label;
      row.append(label);
      for (const slot of [0, 1] as const) {
        const cell = document.createElement("td");
        const button = document.createElement("button");
        button.className = "key-button";
        button.type = "button";
        labelKey(button, action.id, slot);
        button.setAttribute("aria-pressed", "false");
        button.addEventListener("click", () => {
          clearCapture();
          error.hidden = true;
          status.textContent = "Pressione a tecla que deseja usar.";
          capture = { id: action.id, slot, button };
          button.textContent = "Pressione…";
          button.setAttribute("aria-label", `${action.label}, tecla ${slot + 1}: pressione uma nova tecla`);
          button.classList.add("capturing");
          button.setAttribute("aria-pressed", "true");
          controls();
        });
        cell.append(button);
        row.append(cell);
      }
      rows.append(row);
    }
    controls();
  }
  for (const [index, group] of groups.entries()) {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `key-group-${group.id}`;
    button.textContent = group.label;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", "keys-panel");
    button.setAttribute("aria-selected", String(group.id === selected.id));
    button.tabIndex = group.id === selected.id ? 0 : -1;
    button.addEventListener("click", () => {
      selected = group;
      for (const tab of navigation.querySelectorAll("button")) {
        const active = tab === button;
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
      }
      panel.setAttribute("aria-labelledby", button.id);
      category.textContent = group.label;
      description.textContent = group.description;
      error.hidden = true;
      render();
      const scroll = panel.querySelector(".keys-scroll");
      if (scroll instanceof HTMLElement) scroll.scrollTop = 0;
    });
    button.addEventListener("keydown", event => {
      const direction = ["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : ["ArrowUp", "ArrowLeft"].includes(event.key) ? -1 : 0;
      if (!direction && event.key !== "Home" && event.key !== "End") return;
      event.preventDefault();
      const next = event.key === "Home" ? 0 : event.key === "End" ? groups.length - 1 : (index + direction + groups.length) % groups.length;
      const target = navigation.querySelectorAll("button")[next];
      target.focus();
      target.click();
    });
    navigation.append(button);
  }
  dialog.addEventListener("keydown", event => {
    if (!capture || busy || !draft) return;
    event.preventDefault();
    event.stopPropagation();
    if (event.repeat) return;
    if (event.code === "Escape" || event.key === "Escape") {
      clearCapture();
      status.textContent = "Seleção cancelada.";
      return;
    }
    try {
      const next = structuredClone(draft);
      next.bindings[capture.id][capture.slot] = keyFromEvent(event);
      draft = validateBindings(next);
      error.hidden = true;
      clearCapture();
      status.textContent = "Alterações não salvas.";
    } catch (value) { report(value); }
  }, true);
  dialog.addEventListener("cancel", event => { if (busy) event.preventDefault(); });
  dialog.addEventListener("close", () => { clearCapture(); draft = null; });
  function dismiss(): void { if (!busy) dialog.close(); }
  close.addEventListener("click", dismiss);
  cancel.addEventListener("click", dismiss);
  restore.addEventListener("click", () => {
    draft = defaults();
    error.hidden = true;
    render();
    status.textContent = "Padrão restaurado. Salve para aplicar.";
  });
  save.addEventListener("click", () => {
    if (busy || !draft) return;
    const config = validateBindings(draft);
    busy = true;
    controls();
    error.hidden = true;
    status.textContent = "Salvando…";
    void transport.save(config).then(value => {
      draft = validateBindings(value);
      status.textContent = "Alterações salvas.";
    }).catch(value => { status.textContent = ""; report(value); }).finally(() => {
      busy = false;
      controls();
    });
  });
  find("settings", HTMLButtonElement).addEventListener("click", () => {
    if (dialog.open) return;
    busy = true;
    draft = null;
    error.hidden = true;
    rows.replaceChildren();
    status.textContent = "Carregando controles…";
    dialog.showModal();
    controls();
    void transport.load().then(value => {
      draft = validateBindings(value);
      status.textContent = "";
      render();
    }).catch(value => { status.textContent = ""; report(value); }).finally(() => {
      busy = false;
      controls();
    });
  });
}
