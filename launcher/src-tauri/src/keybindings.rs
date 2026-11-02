use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, HashMap, HashSet},
    fs,
    io::Write,
    path::Path,
};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct KeyConfig {
    version: u32,
    bindings: BTreeMap<String, [Option<String>; 2]>,
}

#[derive(Deserialize)]
struct Catalog {
    actions: Vec<Action>,
    keys: Vec<Key>,
}
#[derive(Deserialize)]
struct Action {
    id: String,
    label: String,
    defaults: [Option<String>; 2],
}
#[derive(Deserialize)]
struct Key {
    code: String,
}

fn catalog() -> Result<Catalog, String> {
    serde_json::from_str(include_str!(
        "../../../work/kofas/claude/keybindings_catalog.json"
    ))
    .map_err(|error| error.to_string())
}

fn validate(config: &KeyConfig) -> Result<(), String> {
    let catalog = catalog()?;
    if config.version != 1 || config.bindings.len() != catalog.actions.len() {
        return Err("Configuração de teclado inválida.".to_string());
    }
    let allowed: HashSet<_> = catalog.keys.iter().map(|key| key.code.as_str()).collect();
    let mut used = HashMap::new();
    for action in &catalog.actions {
        let pair = config
            .bindings
            .get(&action.id)
            .ok_or_else(|| format!("Ação ausente: {}.", action.label))?;
        for code in pair.iter().flatten() {
            if !allowed.contains(code.as_str()) {
                return Err(format!("Tecla não reconhecida: {}.", action.label));
            }
            if let Some(owner) = used.insert(code, &action.label) {
                return Err(format!(
                    "Tecla em conflito entre {owner} e {}. Remova o conflito antes de salvar.",
                    action.label
                ));
            }
        }
    }
    Ok(())
}

pub fn load(root: &Path) -> Result<KeyConfig, String> {
    let path = root.join("work/kofas/claude/kofas_keys.json");
    if !path.exists() {
        let config = KeyConfig {
            version: 1,
            bindings: catalog()?
                .actions
                .into_iter()
                .map(|action| (action.id, action.defaults))
                .collect(),
        };
        validate(&config)?;
        return Ok(config);
    }
    let bytes = fs::read(&path).map_err(|error| error.to_string())?;
    if bytes.len() > 65536 {
        return Err("O arquivo de teclas excedeu o tamanho permitido.".to_string());
    }
    let config: KeyConfig = serde_json::from_slice(&bytes)
        .map_err(|error| format!("Não foi possível ler kofas_keys.json: {error}"))?;
    validate(&config)?;
    Ok(config)
}

pub fn save(root: &Path, config: &KeyConfig) -> Result<(), String> {
    validate(config)?;
    let path = root.join("work/kofas/claude/kofas_keys.json");
    let pending = path.with_extension("pending");
    let mut file = fs::File::create(&pending).map_err(|error| error.to_string())?;
    file.write_all(&serde_json::to_vec_pretty(config).map_err(|error| error.to_string())?)
        .map_err(|error| error.to_string())?;
    file.sync_all().map_err(|error| error.to_string())?;
    drop(file);
    fs::rename(pending, path).map_err(|error| format!("Não foi possível salvar as teclas: {error}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        fs,
        time::{SystemTime, UNIX_EPOCH},
    };

    #[test]
    fn portable_mapping_roundtrip_and_invalid_save_preserves_prior_bytes() {
        let id = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!("kof keys ç {id}"));
        fs::create_dir_all(root.join("work/kofas/claude")).unwrap();
        let original = load(&root).unwrap();
        let mut edited = original.clone();
        edited
            .bindings
            .insert("Up".to_string(), [Some("KeyW".to_string()), None]);
        save(&root, &edited).unwrap();
        assert_eq!(load(&root).unwrap(), edited);
        let path = root.join("work/kofas/claude/kofas_keys.json");
        let bytes = fs::read(&path).unwrap();
        edited
            .bindings
            .insert("Down".to_string(), [Some("KeyW".to_string()), None]);
        assert!(save(&root, &edited).is_err());
        assert_eq!(fs::read(&path).unwrap(), bytes);
        fs::write(&path, b"broken json").unwrap();
        assert!(load(&root).is_err());
        assert_eq!(fs::read(&path).unwrap(), b"broken json");
        fs::remove_dir_all(root).unwrap();
    }
}
