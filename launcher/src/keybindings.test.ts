import assert from "node:assert/strict";
import test from "node:test";
import { defaults, validateBindings, keyFromEvent, groups, actionsForGroup } from "./keybindings.ts";

test("control categories contain every native action exactly once", () => {
  const actions = groups.flatMap(group => actionsForGroup(group.id));
  assert.equal(actions.length, 26);
  assert.equal(new Set(actions.map(action => action.id)).size, 26);
  assert.equal(actionsForGroup("movement").length, 4);
  assert.ok(actionsForGroup("combat").some(action => action.id === "ExSkill"));
});

test("native defaults preserve both slots and every action", () => {
  const config = defaults();
  assert.deepEqual(validateBindings(config), config);
  assert.equal(Object.keys(config.bindings).length, 26);
  assert.deepEqual(config.bindings.Up, ["ArrowUp", null]);
  assert.deepEqual(config.bindings.SkillA, ["Digit1", "Numpad1"]);
});

test("conflicting keys and incomplete external configuration are rejected", () => {
  const config = defaults();
  config.bindings.Up = ["KeyQ", null];
  assert.throws(() => validateBindings(config), /Ataque|usada|conflito/i);
  for (const value of [null, {}, {version: 2, bindings: {}}, {...defaults(),bindings:{Up:["KeyW", null]}}]) {
    assert.throws(() => validateBindings(value));
  }
  const unknown = defaults();
  unknown.bindings.Up = ["Unidentified", null];
  assert.throws(() => validateBindings(unknown));
});

test("keyboard capture uses physical keys, supports clearing and refuses chords", () => {
  assert.equal(keyFromEvent({code:"KeyW",ctrlKey:false,altKey:false,metaKey:false,shiftKey:false}), "KeyW");
  assert.equal(keyFromEvent({code:"ShiftRight",ctrlKey:false,altKey:false,metaKey:false,shiftKey:true}), "ShiftRight");
  assert.equal(keyFromEvent({code:"Backspace",ctrlKey:false,altKey:false,metaKey:false,shiftKey:false}), null);
  assert.throws(() => keyFromEvent({code:"KeyW",ctrlKey:true,altKey:false,metaKey:false,shiftKey:false}), /combina/i);
  assert.throws(() => keyFromEvent({code:"Unidentified",ctrlKey:false,altKey:false,metaKey:false,shiftKey:false}));
});

test("accessible Unicode input without a scan code can still assign a recognized letter", () => {
  assert.equal(keyFromEvent({code:"",key:"w",location:0,ctrlKey:false,altKey:false,metaKey:false,shiftKey:false}), "KeyW");
  assert.throws(() => keyFromEvent({code:"",key:"ç",location:0,ctrlKey:false,altKey:false,metaKey:false,shiftKey:false}));
  assert.equal(keyFromEvent({code:"",key:"F8",location:0,ctrlKey:false,altKey:false,metaKey:false,shiftKey:false}), "F8");
  assert.equal(keyFromEvent({code:"",key:"Backspace",location:0,ctrlKey:false,altKey:false,metaKey:false,shiftKey:false}), null);
});

test("default restore does not mutate a previously edited configuration", () => {
  const edited = defaults();
  edited.bindings.Up[0] = "KeyW";
  assert.equal(defaults().bindings.Up[0], "ArrowUp");
  assert.equal(edited.bindings.Up[0], "KeyW");
});
