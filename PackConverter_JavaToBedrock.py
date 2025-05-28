import os
import shutil
import json
import uuid
from collections import defaultdict

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

try:
    import yaml
except ImportError:
    print("Module 'yaml' non trouvé. Installe-le avec : pip install pyyaml")
    raise

# Charger les chemins depuis les variables d'environnement
JAVA_RP_DIR = os.environ.get("JAVA_RP_DIR", r"Put the path to your Java Resource Pack here")
if not JAVA_RP_DIR.endswith(os.sep):
    JAVA_RP_DIR += os.sep
BEDROCK_RP_DIR = os.environ.get("BEDROCK_RP_DIR", r"Put the path to your Bedrock Resource Pack here")
if not BEDROCK_RP_DIR.endswith(os.sep):
    BEDROCK_RP_DIR += os.sep
CUSTOM_ITEMS_FILE = "custom_items.json"

if not JAVA_RP_DIR or not BEDROCK_RP_DIR:
    raise EnvironmentError("❌ JAVA_RP_DIR ou BEDROCK_RP_DIR n'est pas défini. Vérifie que les variables d'environnement sont bien passées.")

# Structure minimale
bedrock_structure = [
    "textures",
    "textures/item",
    "sounds",
    "sounds/custom",
    "texts",
    "models",
    "models/entity",
    "render_controllers"
]


def clean_bedrock_directory():
    for sub in ['bedrock', 'behavior', 'geyser_mappings']:
        target = JAVA_RP_DIR.replace('java', sub)
        if os.path.exists(target):
            shutil.rmtree(target)
            print(t("deleted_folder", target=target))

def create_bedrock_structure():
    os.makedirs(BEDROCK_RP_DIR, exist_ok=True)
    for folder in bedrock_structure:
        os.makedirs(os.path.join(BEDROCK_RP_DIR, folder), exist_ok=True)

def process_model_entry(entry, item_base_name, texture_root, items, cmd_map, source_file):
    model_ref = entry.get('model', {}).get('model') or entry.get('model')
    if not model_ref:
        return
    threshold = entry.get('threshold', 0)

    rel = model_ref.split(':', 1)[-1] if ':' in model_ref else model_ref
    # Recherche tous les dossiers de namespace dans assets pour trouver le modèle
    assets_root = os.path.join(JAVA_RP_DIR, 'assets')
    possible_paths = [
        os.path.join(assets_root, *rel.split('/')) + '.json'
    ]
    # Ajoute tous les namespaces trouvés dans assets
    if os.path.isdir(assets_root):
        for ns in os.listdir(assets_root):
            ns_model = os.path.join(assets_root, ns, 'models', *rel.split('/')) + '.json'
            possible_paths.append(ns_model)
    possible_paths.append(os.path.join(assets_root, 'minecraft', 'models', *rel.split('/')) + '.json')

    model_path = next((p for p in possible_paths if os.path.isfile(p)), None)

    if not model_path:
        print(f"❌ Modèle non trouvé pour {rel}")
        return

    texture_list = []
    try:
        with open(model_path, encoding='utf-8') as f:
            bb_model = json.load(f)
        texture_list = list(bb_model.get('textures', {}).values())
    except Exception as e:
        print(f"⚠️ Texture introuvable dans {model_path}: {e}")

    geo_name = f"{item_base_name.lower().replace(' ', '_')}_cmd{threshold}"
    tex_entry = texture_list[0].split(":", 1)[-1] if texture_list else rel
    if tex_entry.startswith("item/"):
        tex_entry = tex_entry[len("item/"):]

    item_name = f"{item_base_name}_cmd{threshold}"
    items.append({
        "name": f"custom:{item_name}",
        "id": item_base_name,
        "custom_model_data": threshold,
        "display_name": f"§f{item_base_name.replace('_', ' ').title()} (CMD:{threshold})",
        "texture": tex_entry
    })

    convert_java_model_to_geo(model_path, item_name, tex_entry)

def copy_all_item_textures():
    assets_path = os.path.join(JAVA_RP_DIR, 'assets')
    if os.path.isdir(assets_path):
        for namespace in os.listdir(assets_path):
            namespace_path = os.path.join(assets_path, namespace)
            textures_root = os.path.join(namespace_path, 'textures')
            if os.path.isdir(textures_root):
                dst_root = os.path.join(BEDROCK_RP_DIR, 'textures')
                shutil.copytree(textures_root, dst_root, dirs_exist_ok=True)
    print(t("all_textures_copied"))

def convert_java_model_to_geo(model_path, output_name, texture_key):
    try:
        print("🔄 Lecture du modèle Java")
        with open(model_path, encoding='utf-8') as f:
            model = json.load(f)

        print("📌 Lecture des paramètres de base")
        identifier = f"geometry.{output_name}"
        tex_w, tex_h = model.get('texture_size', [32, 32])
        bounds_width = model.get('visible_bounds_width', 2)
        bounds_height = model.get('visible_bounds_height', 2.5)
        bounds_offset = model.get('visible_bounds_offset', [0, 0.75, 0])

        elements = model.get('elements', [])
        groups = model.get('groups', [])
        print(f"➡️  {len(elements)} éléments, {len(groups)} groupes")

        def calculate_pivot_from_origin(origin):
            # Correction: X-8, Y inchangé, Z-8
            return [
                round(origin[0] - 8, 5),
                round(origin[1], 5),
                round(origin[2] - 8, 5)
            ]

        def correct_uv_mapping(face, uv_data):
            if "uv" not in uv_data or len(uv_data['uv']) != 4:
                return {"uv": [0, 0], "uv_size": [1, 1]}
            u0, v0, u1, v1 = uv_data['uv']
            # Ajout de compensation de bordure (0.016) comme dans le script sh
            x_sign = 1 if (u1 - u0) > 0 else -1
            y_sign = 1 if (v1 - v0) > 0 else -1
            
            if face in ["up", "down"]:
                return {
                    "uv": [round(u1 - (0.016 * x_sign), 5), round(v1 - (0.016 * y_sign), 5)],
                    "uv_size": [round((u0 - u1) + (0.016 * x_sign), 5), round((v0 - v1) + (0.016 * y_sign), 5)]
                }
            else:
                return {
                    "uv": [round(u0 + (0.016 * x_sign), 5), round(v0 + (0.016 * y_sign), 5)],
                    "uv_size": [round((u1 - u0) - (0.016 * x_sign), 5), round((v1 - v0) - (0.016 * y_sign), 5)]
                }

        def build_bone(group, parent_name=None):
            try:
                name = group.get('name', 'unnamed').replace(' ', '').lower()
                
                # Structure de base comme dans le script sh
                bones = [{
                    "name": "geyser_custom",
                    "binding": "c.item_slot == 'head' ? 'head' : q.item_slot_to_bone_name(c.item_slot)",
                    "pivot": [0, 8, 0]
                }, {
                    "name": "geyser_custom_x",
                    "parent": "geyser_custom",
                    "pivot": [0, 8, 0]
                }, {
                    "name": "geyser_custom_y",
                    "parent": "geyser_custom_x",
                    "pivot": [0, 8, 0]
                }, {
                    "name": "geyser_custom_z",
                    "parent": "geyser_custom_y",
                    "pivot": [0, 8, 0]
                }]

                cubes = []
                children_names = []
                sub_bones = []

                # Traitement des enfants
                for child in group.get('children', []):
                    if isinstance(child, int) and child < len(elements):
                        # Élément géométrique
                        e = elements[child]
                        
                        # Gestion de la rotation
                        rotation = [0, 0, 0]
                        if 'rotation' in e:
                            if isinstance(e['rotation'], dict):
                                rotation = e['rotation'].get('angle', 0)
                                # Conversion angle unique vers [x, y, z]
                                if isinstance(rotation, (int, float)):
                                    axis = e['rotation'].get('axis', 'y')
                                    rotation = [
                                        rotation if axis == 'x' else 0,
                                        rotation if axis == 'y' else 0,
                                        rotation if axis == 'z' else 0
                                    ]
                            elif isinstance(e['rotation'], (list, tuple)):
                                rotation = e['rotation']

                        # Conversion des coordonnées avec gestion de la rotation
                        from_pos = e.get('from', [0, 0, 0])
                        to_pos = e.get('to', [0, 0, 0])
                        
                        cube_origin = [
                            round(from_pos[0] - 8, 5),
                            round(from_pos[1], 5),
                            round(from_pos[2] - 8, 5)
                        ]
                        
                        size = [
                            round(to_pos[i] - from_pos[i], 5) 
                            for i in range(3)
                        ]

                        cube = {
                            "origin": cube_origin,
                            "size": size,
                            "uv": {}
                        }

                        # Ajout de la rotation si présente
                        if any(r != 0 for r in rotation):
                            cube["rotation"] = rotation

                        # UV mapping avec gestion des faces manquantes
                        for face, data in e.get('faces', {}).items():
                            if data:  # Vérifie que les données UV existent
                                cube['uv'][face] = correct_uv_mapping(face, data)

                        cubes.append(cube)

                    elif isinstance(child, dict):
                        # Sous-groupe
                        nested_bones = build_bone(child, name)
                        if nested_bones:
                            sub_bones.extend(nested_bones)
                            children_names.append(nested_bones[0]['name'])

                # Définir le pivot du bone à partir de l'origine du groupe ou par défaut [0, 8, 0]
                bone_pivot = calculate_pivot_from_origin(group.get('origin', [8, 8, 8])) if 'origin' in group else [0, 8, 0]
                # Construction du bone
                bone = {
                    "name": name,
                    "pivot": bone_pivot
                }
                
                # Ajout des propriétés si présentes
                if cubes:
                    bone["cubes"] = cubes
                if parent_name:
                    bone["parent"] = parent_name
                if children_names:
                    bone["children"] = children_names

                return [bone] + sub_bones

            except Exception as e:
                print(f"⚠️ Erreur dans build_bone pour {group.get('name', 'unnamed')}: {e}")
                return []

        # Construction de tous les os à partir des groupes
        bones = []
        for group in groups:
            if not isinstance(group, dict):
                print(f"⚠️ Groupe invalide ignoré : {group} (type {type(group).__name__})")
                continue
            try:
                built = build_bone(group)
                if built:
                    bones.extend(built)
            except Exception as e:
                print(f"❌ Erreur lors du traitement du groupe '{group.get('name', 'inconnu')}': {e}")

        # Construction des transformations d'affichage
        # Display transforms building (EN)
        item_display_transforms = {}
        if "display" in model:
            for key, data in model["display"].items():
                entry = {
                    "rotation": [round(v, 2) for v in data.get("rotation", [0, 0, 0])],
                    "translation": [round(v, 2) for v in data.get("translation", [0, 0, 0])],
                    "scale": [round(v, 2) for v in data.get("scale", [1, 1, 1])],
                    "rotation_pivot": [0, 0, 0],
                    "scale_pivot": [0, 0, 0]
                }
                if key.lower() == "gui":
                    entry["fit_to_frame"] = False
                item_display_transforms[key.lower()] = entry

        # Assemblage final du fichier géométrique
        # Final geometry file assembly (EN)
        geo = {
            "format_version": "1.12.0",
            "minecraft:geometry": [
                {
                    "description": {
                        "identifier": identifier,
                        "texture_width": tex_w,
                        "texture_height": tex_h,
                        "visible_bounds_width": bounds_width,
                        "visible_bounds_height": bounds_height,
                        "visible_bounds_offset": bounds_offset
                    },
                    "bones": bones,
                    "item_display_transforms": item_display_transforms
                }
            ]
        }

        # Écriture du fichier .geo.json
        # Writing .geo.json file (EN)
        out_geo = os.path.join(BEDROCK_RP_DIR, 'models', 'entity', f'{output_name}.geo.json')
        print(f"💾 Écriture du fichier GEO : {out_geo}")
        with open(out_geo, 'w', encoding='utf-8') as f:
            json.dump(geo, f, indent='\t', separators=(',', ': '))

        # Génération du render controller
        # Render controller generation (EN)
        fixed_tex_key = texture_key.replace('\\', '/').split('.')[0]
        rc = {
            "format_version": "1.8.0",
            "render_controllers": {
                f"controller.render.{output_name}": {
                    "geometry": identifier,
                    "materials": [{"*": "material.default"}],
                    "textures": f"Array.textures.{output_name}"
                }
            },
            "arrays": {
                "textures": {
                    f"Array.textures.{output_name}": [f"textures/item/{fixed_tex_key}"]
                }
            }
        }
        out_rc = os.path.join(BEDROCK_RP_DIR, 'render_controllers', f'{output_name}.render_controller.json')
        print(f"💾 Écriture du fichier RenderController : {out_rc}")
        with open(out_rc, 'w', encoding='utf-8') as f:
            json.dump(rc, f, indent='\t', separators=(',', ': '))

        print(f"✅ Conversion réussie: {output_name}")

    except Exception as e:
        print(f"❌ Conversion modèle {model_path}: {e}")
        raise










def copy_sounds():
    assets_path = os.path.join(JAVA_RP_DIR, 'assets')
    sounds_dst = os.path.join(BEDROCK_RP_DIR, 'sounds', 'custom')
    sound_definitions = {}
    found = False

    if os.path.isdir(assets_path):
        for namespace in os.listdir(assets_path):
            src = os.path.join(assets_path, namespace, 'sounds')
            if os.path.isdir(src):
                for root, _, files in os.walk(src):
                    for file in files:
                        if file.endswith('.ogg'):
                            rel_path = os.path.relpath(os.path.join(root, file), src).replace('\\', '/')
                            sound_id = f"{namespace}:{os.path.splitext(rel_path)[0]}"
                            dest_path = os.path.join(sounds_dst, rel_path)
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            shutil.copy2(os.path.join(root, file), dest_path)

                            # Détection automatique de "stream" pour les musiques longues
                            stream = "records" in rel_path or "special" in rel_path

                            sound_definitions[sound_id] = {
                                "category": "player",
                                "sounds": [
                                    {
                                        "name": f"sounds/custom/{rel_path.split('.')[0]}",
                                        "stream": stream
                                    }
                                ]
                            }
                            found = True

    if found:
        sound_def_file = os.path.join(BEDROCK_RP_DIR, 'sound_definitions.json')
        with open(sound_def_file, 'w', encoding='utf-8') as f:
            json.dump({
                "format_version": "1.14.0",
                "sound_definitions": sound_definitions
            }, f, indent=4)
        print(t("sounds_copied"))
    else:
        print(t("no_sounds"))

def generate_manifest():
    description = "Converted Resource Pack"
    packmeta_path = os.path.join(JAVA_RP_DIR, "pack.mcmeta")
    if os.path.isfile(packmeta_path):
        try:
            with open(packmeta_path, encoding="utf-8") as f:
                meta = json.load(f)
                description = meta.get("pack", {}).get("description", description)
        except Exception as e:
            print(f"⚠️ Impossible de lire la description depuis pack.mcmeta: {e}")

    header_uuid = str(uuid.uuid4())
    module_uuid = str(uuid.uuid4())
    manifest = {
        "format_version": 2,
        "header": {
            "name": "Converted Resource Pack",
            "description": description,
            "uuid": header_uuid,
            "version": [1, 0, 0],
            "min_engine_version": [1, 16, 0]
        },
        "modules": [
            {
                "type": "resources",
                "uuid": module_uuid,
                "version": [1, 0, 0]
            }
        ]
    }
    with open(os.path.join(BEDROCK_RP_DIR, "manifest.json"), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=4)
    print(t("manifest_generated"))

def validate_geo_json_files(directory):
    print(t("geo_validation"))
    count = 0
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith('.geo.json'):
                try:
                    with open(os.path.join(root, f), encoding='utf-8') as j:
                        json.load(j)
                    count += 1
                except Exception as e:
                    print(f"❌ Erreur fichier invalide : {f} => {e}")
    print(t("geo_validation_done", count=count))

# --- Custom Items extraction ---
def normalize_item_name(name):
    return name.replace(' ','_').replace('-','_').lower()

def generate_custom_items_json(items):
    custom_items = []

    for item in items:
        base_name = item['id']
        cmd = item['custom_model_data']
        texture = f"{base_name}_cmd{cmd}"

        clean_texture = item['texture'].replace('\\', '/').split('.')[0]
        if clean_texture.startswith('custom_stuff_v1:'):
            clean_texture = clean_texture[len('custom_stuff_v1:'):]

        custom_entry = {
            "name": texture,
            "id": texture,
            "components": {
                "minecraft:icon": texture,
                "minecraft:render_offsets": "tools",
                "minecraft:custom_components": {
                    "custom_model_data": float(cmd)
                },
                "minecraft:display_name": {
                    "value": f"§f{base_name.replace('_', ' ').title()} (CMD:{cmd})"
                },
                "minecraft:material_instances": {
                    "*": {
                        "texture": texture,
                        "render_method": "alpha_test",
                        "face_dimming": False,
                        "ambient_occlusion": False
                    }
                },
                "minecraft:geometry": f"geometry.{texture}",
                "minecraft:wearable": {
                    "slot": "slot.weapon.mainhand"
                },
                "minecraft:attachable": {
                    "description": {
                        "identifier": f"custom:{texture}",
                        "materials": {
                            "default": "material.default"
                        },
                        "textures": {
                            "default": f"textures/item/{clean_texture}"
                        },
                        "geometry": f"geometry.{texture}",
                        "render_controllers": [
                            f"controller.render.{texture}"
                        ]
                    }
                }
            },
            "client": {
                "minecraft:display_name": {
                    "value": f"§f{base_name.replace('_', ' ').title()} (CMD:{cmd})"
                },
                "minecraft:icon": {
                    "texture": texture
                }
            }
        }

        custom_items.append(custom_entry)

    output_path = os.path.join(BEDROCK_RP_DIR, "custom_items.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(custom_items, f, indent=4)
    print(t("custom_items_generated"))

def extract_custom_model_data():
    items, cmd_map = [], {}
    # Correction du chemin pour être compatible avec tous les OS et éviter les slashs/doubles-slashs
    items_dir = os.path.join(JAVA_RP_DIR, 'assets', 'minecraft', 'items')
    items_dir = os.path.normpath(items_dir)
    tex_root = os.path.join(BEDROCK_RP_DIR, 'textures', 'item')
    if not os.path.isdir(items_dir):
        print(f"❌ Introuvable: {items_dir}")
        return items
    for r,_,fs in os.walk(items_dir):
        for f in fs:
            if not f.lower().endswith(('.json','.yml','.yaml')): continue
            path=os.path.join(r,f)
            try:
                with open(path,encoding='utf-8') as pf:
                    data=yaml.safe_load(pf) if f.lower().endswith(('.yml','.yaml')) else json.load(pf)
                base=os.path.splitext(f)[0]
                for e in data.get('model',{}).get('entries',[]): process_model_entry(e,base,tex_root,items,cmd_map,path)
                fb=data.get('model',{}).get('fallback',{}).get('model')
                if fb: process_model_entry({'threshold':-1,'model':{'model':fb}},base,tex_root,items,cmd_map,path)
            except Exception as e:
                print(f"❌ Erreur lecture {f}: {e}")
    return items

def list_java_assets():
    # Affiche la structure du dossier assets Java pour debug
    print("🔍 Structure du pack Java assets :")
    for root, dirs, files in os.walk(os.path.join(JAVA_RP_DIR, 'assets')):
        level = root.replace(JAVA_RP_DIR, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        for d in dirs:
            print(f"{indent}    {d}/")
        for f in files:
            print(f"{indent}    {f}")

def generate_item_texture_json(items):
    texture_data = {}
    for item in items:
        texture_path = item['texture'].replace('\\', '/').split('.')[0]
        if texture_path.startswith('custom_stuff_v1:'):
            texture_path = texture_path[len('custom_stuff_v1:'):]
        full_texture_path = f"textures/item/{texture_path}"
        unique_name = f"{item['id']}_cmd{item['custom_model_data']}"
        texture_data[unique_name] = {
            "textures": full_texture_path
        }

    item_texture = {
        "resource_pack_name": "Converted Resource Pack",
        "texture_name": "atlas.items",
        "texture_data": texture_data
    }

    out_path = os.path.join(BEDROCK_RP_DIR, "textures", "item_texture.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(item_texture, f, indent=4)
    print(t("item_texture_generated"))

def generate_behavior_pack(items):
    bp_dir = BEDROCK_RP_DIR.replace('bedrock', 'behavior')
    if os.path.exists(bp_dir):
        shutil.rmtree(bp_dir)
    os.makedirs(os.path.join(bp_dir, 'items'), exist_ok=True)

    # Manifest for behavior pack
    # Manifest du behavior pack (FR)
    header_uuid = str(uuid.uuid4())
    module_uuid = str(uuid.uuid4())
    manifest = {
        "format_version": 2,
        "header": {
            "name": "Converted Resource Pack",
            "description": "Pack converti de Java à Bedrock",
            "uuid": header_uuid,
            "version": [1, 0, 0],
            "min_engine_version": [1, 21, 0]
        },
        "modules": [
            {
                "type": "data",
                "uuid": module_uuid,
                "version": [1, 0, 0]
            }
        ]
    }
    with open(os.path.join(bp_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=4)

    # Générer chaque fichier item
    # Generate each item file (EN)
    for item in items:
        item_json = {
            "format_version": "1.16.100",
            "minecraft:item": {
                "description": {
                    "identifier": item['name'],
                    "category": "Equipment"
                },
                "components": {
                    "minecraft:icon": item['name'].split(":")[-1],
                    "minecraft:hand_equipped": True,
                    "minecraft:max_stack_size": 1,
                    "minecraft:display_name": { "value": item['display_name'] },
                    "minecraft:on_use": { "event": "play_sound_custom" }
                },
                "events": {
                    "play_sound_custom": {
                        "run_command": { "command": ["playsound custom:item_sound @s"] }
                    }
                },
                "client": {
                    "custom_render": f"controller.render.{item['name'].split(':')[-1]}"
                }
            }
        }
        item_file = os.path.join(bp_dir, 'items', f"{item['name'].split(':')[-1]}.json")
        with open(item_file, 'w', encoding='utf-8') as f:
            json.dump(item_json, f, indent=4)
    print(f"✅ Behavior pack généré ({len(items)} items)")


def generate_geyser_mapping_json(items):
    mappings = {
        "format_version": 2,
        "items": {}
    }

    for item in items:
        base_item = item['id'] if item['id'].startswith("minecraft:") else f"minecraft:{item['id']}"
        cmd = str(item['custom_model_data'])

        # Créer la structure si absente
        # Create structure if missing (EN)
        if base_item not in mappings["items"]:
            mappings["items"][base_item] = {
                "custom_model_data": {}
            }

        # Ajouter le mapping pour ce CustomModelData
        # Add mapping for this CustomModelData (EN)
        mappings["items"][base_item]["custom_model_data"][cmd] = {
            "bedrock_identifier": base_item,  # Peut être adapté si nécessaire
            "display_name": item.get("display_name", "")
        }

    output_path = os.path.join(BEDROCK_RP_DIR.replace("bedrock", "geyser_mappings"), "geyser-mapping.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=4)
    print(t("geyser_mapping_generated"))


def create_mcpack(source_dir, output_dir, pack_name):
    import zipfile
    temp_dir = os.path.join(output_dir, 'temp_pack')
    mcpack_path = os.path.join(output_dir, f"{pack_name}.mcpack")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    shutil.copytree(source_dir, temp_dir)

    zip_path = mcpack_path.replace('.mcpack', '.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)

    if os.path.exists(mcpack_path):
        os.remove(mcpack_path)
    os.rename(zip_path, mcpack_path)
    shutil.rmtree(temp_dir)

    print(t("mcpack_created", mcpack_path=mcpack_path))

def validate_consistency(items):
    print(t("coherence_validation"))
    rc_path = os.path.join(BEDROCK_RP_DIR, "render_controllers")
    geo_path = os.path.join(BEDROCK_RP_DIR, "models", "entity")
    tex_path = os.path.join(BEDROCK_RP_DIR, "textures", "item")
    custom_items_path = os.path.join(BEDROCK_RP_DIR, "custom_items.json")
    errors = 0

    for item in items:
        name = item["name"].split(":")[-1]
        tex_key = item.get("texture", "")
        expected_texture = os.path.join(tex_path, tex_key + ".png")

        geo_file = os.path.join(geo_path, f"{name}.geo.json")
        rc_file = os.path.join(rc_path, f"{name}.render_controller.json")

        if not os.path.isfile(geo_file):
            print(t("missing_geo", name=name))
            errors += 1

        if not os.path.isfile(rc_file):
            print(t("missing_rc", name=name))
            errors += 1
            continue

        try:
            with open(rc_file, encoding='utf-8') as f:
                rc = json.load(f)
            expected_geometry = f"geometry.{name}"
            actual_geometry = rc["render_controllers"][f"controller.render.{name}"]["geometry"]
            if actual_geometry != expected_geometry:
                print(t("bad_geometry", actual=actual_geometry, expected=expected_geometry))
                errors += 1

            tex_array = rc.get("arrays", {}).get("textures", {}).get(f"Array.textures.{name}", [])
            if not tex_array or not os.path.isfile(os.path.join(BEDROCK_RP_DIR, tex_array[0] + ".png")):
                print(t("missing_texture", expected_texture=os.path.join(BEDROCK_RP_DIR, tex_array[0] + ".png") if tex_array else ""))
                errors += 1
        except Exception as e:
            print(f"❌ Erreur lecture {name}.render_controller.json: {e}")
            errors += 1

        if not os.path.isfile(expected_texture):
            print(t("missing_texture", expected_texture=expected_texture))
            errors += 1

    print(t("coherence_validation_done", valid=len(items) - errors, total=len(items)))

def copy_pack_icon():
    src = os.path.join(JAVA_RP_DIR, "pack.png")
    dst = os.path.join(BEDROCK_RP_DIR, "pack_icon.png")
    if os.path.isfile(src):
        shutil.copy(src, dst)
        print(t("pack_icon_copied"))
    else:
        print(t("no_pack_icon"))


TRANSLATIONS = {
    "fr": {
        "select_java_dir": "Dossier Resource Pack Java:",
        "select_bedrock_dir": "Dossier Resource Pack Bedrock:",
        "browse": "Parcourir",
        "start_conversion": "Lancer la conversion",
        "logs": "Logs:",
        "conversion_done": "✅ Conversion terminée.",
        "conversion_success": "Conversion terminée avec succès !",
        "conversion_error": "Erreur lors de la conversion : {e}",
        "error": "❌ Erreur : {e}",
        "choose_language": "Langue",
        "success": "Succès",
        "error_title": "Erreur",
        "start_console": "⏳ Démarrage conversion (mode console)...",
        "console_done": "✅ Conversion terminée.",
        "no_java_dir": "❌ JAVA_RP_DIR ou BEDROCK_RP_DIR n'est pas défini. Vérifie que les variables d'environnement sont bien passées.",
        "deleted_folder": "🪟 Dossier supprimé : {target}",
        "all_textures_copied": "📁 Toutes les textures item copiées.",
        "sounds_copied": "🔊 Sons copiés + sound_definitions.json généré.",
        "no_sounds": "🔇 Aucun son trouvé à copier.",
        "manifest_generated": "📝 Manifest généré.",
        "geo_validation": "🔍 Validation des fichiers .geo.json...",
        "geo_validation_done": "✅ Validation terminée ({count} fichiers .geo.json valides)",
        "custom_items_generated": "✅ custom_items.json généré",
        "item_texture_generated": "✅ item_texture.json généré",
        "geyser_mapping_generated": "✅ Fichier geyser-mapping.json généré correctement.",
        "mcpack_created": "✅ Fichier .mcpack créé : {mcpack_path}",
        "coherence_validation": "🔎 Validation de cohérence entre les fichiers...",
        "coherence_validation_done": "✅ Validation cohérence terminée ({valid} valides / {total} total)",
        "missing_geo": "❌ GEO manquant : {name}.geo.json",
        "missing_rc": "❌ Render controller manquant : {name}.render_controller.json",
        "bad_geometry": "⚠️ Mauvais identifiant de géométrie : {actual} (attendu: {expected})",
        "missing_texture": "❌ Fichier texture manquant : {expected_texture}",
        "pack_icon_copied": "🖼️ pack_icon.png copié depuis pack.png",
        "no_pack_icon": "⚠️ Aucun pack.png trouvé à copier.",
    },
    "en": {
        "select_java_dir": "Java Resource Pack Folder:",
        "select_bedrock_dir": "Bedrock Resource Pack Folder:",
        "browse": "Browse",
        "start_conversion": "Start Conversion",
        "logs": "Logs:",
        "conversion_done": "✅ Conversion finished.",
        "conversion_success": "Conversion finished successfully!",
        "conversion_error": "Error during conversion: {e}",
        "error": "❌ Error: {e}",
        "choose_language": "Language",
        "success": "Success",
        "error_title": "Error",
        "start_console": "⏳ Starting conversion (console mode)...",
        "console_done": "✅ Conversion finished.",
        "no_java_dir": "❌ JAVA_RP_DIR or BEDROCK_RP_DIR not set. Check your environment variables.",
        "deleted_folder": "🪟 Deleted folder: {target}",
        "all_textures_copied": "📁 All item textures copied.",
        "sounds_copied": "🔊 Sounds copied + sound_definitions.json generated.",
        "no_sounds": "🔇 No sounds found to copy.",
        "manifest_generated": "📝 Manifest generated.",
        "geo_validation": "🔍 Validating .geo.json files...",
        "geo_validation_done": "✅ Validation done ({count} valid .geo.json files)",
        "custom_items_generated": "✅ custom_items.json generated",
        "item_texture_generated": "✅ item_texture.json generated",
        "geyser_mapping_generated": "✅ geyser-mapping.json generated successfully.",
        "mcpack_created": "✅ .mcpack file created: {mcpack_path}",
        "coherence_validation": "🔎 Checking file consistency...",
        "coherence_validation_done": "✅ Consistency check done ({valid} valid / {total} total)",
        "missing_geo": "❌ Missing GEO: {name}.geo.json",
        "missing_rc": "❌ Missing render controller: {name}.render_controller.json",
        "bad_geometry": "⚠️ Wrong geometry identifier: {actual} (expected: {expected})",
        "missing_texture": "❌ Missing texture file: {expected_texture}",
        "pack_icon_copied": "🖼️ pack_icon.png copied from pack.png",
        "no_pack_icon": "⚠️ No pack.png found to copy.",
    }
}

LANG = "fr"

def t(key, **kwargs):
    return TRANSLATIONS[LANG].get(key, key).format(**kwargs)

class PackConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PackConverter Java ➔ Bedrock")
        self.root.geometry("650x400")
        self.root.resizable(False, False)

        # Langue
        self.lang_var = tk.StringVar(value=LANG)
        lang_frame = tk.Frame(root)
        lang_frame.pack(anchor="ne", padx=10, pady=(10, 0))
        self.lang_label = tk.Label(lang_frame, text=t("choose_language"), font=("Segoe UI", 10))
        self.lang_label.pack(side="left")
        self.lang_menu = tk.OptionMenu(lang_frame, self.lang_var, *TRANSLATIONS.keys(), command=self.change_language)
        self.lang_menu.pack(side="left")

        # Variables
        self.java_dir = tk.StringVar(value=JAVA_RP_DIR)

        # Modern Card-like Frame
        self.main_card = tk.Frame(root, bg="#f4f4f4", bd=2, relief="groove")
        self.main_card.pack(fill="x", padx=20, pady=(20, 5))

        # Java RP selection
        self.java_frame = tk.Frame(self.main_card, bg="#f4f4f4")
        self.java_frame.pack(fill="x", pady=10, padx=10)
        self.java_label = tk.Label(self.java_frame, text=t("select_java_dir"), font=("Segoe UI", 11), bg="#f4f4f4")
        self.java_label.pack(side="left")
        self.java_entry = tk.Entry(self.java_frame, textvariable=self.java_dir, width=40, font=("Segoe UI", 10))
        self.java_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)
        self.java_browse_btn = tk.Button(self.java_frame, text=t("browse"), command=self.browse_java, font=("Segoe UI", 10), bg="#e0e0e0")
        self.java_browse_btn.pack(side="left", padx=10)

        # Start conversion button
        self.convert_btn = tk.Button(self.main_card, text=t("start_conversion"), command=self.run_conversion,
                                     bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), height=2)
        self.convert_btn.pack(fill="x", padx=10, pady=(10, 10))

        # Logs section
        self.logs_card = tk.Frame(root, bg="#f4f4f4", bd=2, relief="groove")
        self.logs_card.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.logs_label = tk.Label(self.logs_card, text=t("logs"), font=("Segoe UI", 11, "bold"), bg="#f4f4f4")
        self.logs_label.pack(anchor="w", padx=10, pady=(8, 0))
        self.logbox = scrolledtext.ScrolledText(self.logs_card, height=10, state="disabled", font=("Consolas", 10), bg="#fafafa")
        self.logbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Validation initiale des chemins
        self.java_dir.trace_add("write", lambda *args: self.validate_paths())
        self.validate_paths()

    def validate_paths(self):
        # Vérifie si le dossier Java RP contient des fichiers items valides
        java_items_dir = os.path.normpath(os.path.join(self.java_dir.get(), 'assets', 'minecraft', 'items'))
        has_items = os.path.isdir(java_items_dir) and any(
            f.lower().endswith(('.json', '.yml', '.yaml'))
            for f in os.listdir(java_items_dir)
        ) if os.path.isdir(java_items_dir) else False

        if has_items:
            self.convert_btn.config(state="normal")
        else:
            self.convert_btn.config(state="disabled")

    def browse_java(self):
        path = filedialog.askdirectory(title="Sélectionne le dossier Java RP")
        if path:
            self.java_dir.set(path)

    def browse_bedrock(self):
        path = filedialog.askdirectory(title="Sélectionne le dossier Bedrock RP")
        if path:
            self.bedrock_dir.set(path)

    def log(self, msg):
        self.logbox.config(state="normal")
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.logbox.config(state="disabled")
        self.root.update()

    def run_conversion(self):
        import sys
        import io

        # Redirige stdout/stderr vers la logbox
        class TextRedirector(io.StringIO):
            def __init__(self, gui):
                super().__init__()
                self.gui = gui
            def write(self, s):
                self.gui.log(s.rstrip())
            def flush(self): pass

        sys.stdout = TextRedirector(self)
        sys.stderr = TextRedirector(self)

        try:
            # Met à jour les variables globales
            global JAVA_RP_DIR, BEDROCK_RP_DIR
            JAVA_RP_DIR = self.java_dir.get()
            BEDROCK_RP_DIR = self.bedrock_dir.get()

            # Lancement conversion
            clean_bedrock_directory()
            create_bedrock_structure()
            copy_all_item_textures()
            copy_sounds()
            copy_pack_icon()
            generate_manifest()
            items = extract_custom_model_data()
            generate_custom_items_json(items)
            generate_item_texture_json(items)
            generate_geyser_mapping_json(items)
            validate_geo_json_files(os.path.join(BEDROCK_RP_DIR, "models", "entity"))
            validate_consistency(items)

            # Sélection du dossier de sortie par l'utilisateur
            output_dir = filedialog.askdirectory(title="Sélectionnez le dossier de sortie pour le ZIP")
            if not output_dir:
                self.log("❌ Opération annulée : aucun dossier de sortie sélectionné.")
                return

            converted_name = os.path.basename(JAVA_RP_DIR.strip().rstrip("/\\"))
            zip_path = os.path.join(output_dir, f"{converted_name}.zip")

            # Création du fichier zip contenant tout le pack Bedrock
            import zipfile
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for rootdir, dirs, files in os.walk(BEDROCK_RP_DIR):
                    for file in files:
                        file_path = os.path.join(rootdir, file)
                        arcname = os.path.relpath(file_path, BEDROCK_RP_DIR)
                        zipf.write(file_path, arcname)

            self.log(f"✅ Pack exporté dans : {zip_path}")
            messagebox.showinfo(t("success"), f"Pack exporté dans :\n{zip_path}")
        except Exception as e:
            self.log(t("error", e=str(e)))
            messagebox.showerror(t("error_title"), t("conversion_error", e=str(e)))

    def update_labels(self):
        # Met à jour tous les labels/boutons selon la langue
        self.lang_label.config(text=t("choose_language"))
        self.java_label.config(text=t("select_java_dir"))
        self.java_browse_btn.config(text=t("browse"))
        self.convert_btn.config(text=t("start_conversion"))
        self.logs_label.config(text=t("logs"))
        
        # Reconstruction du menu
        menu = self.lang_menu["menu"]
        menu.delete(0, "end")
        for lang in TRANSLATIONS.keys():
            menu.add_command(label=lang, command=lambda l=lang: self.change_language(l))

    def change_language(self, lang):
        global LANG
        LANG = lang
        self.lang_var.set(lang)  # Important: mettre à jour la variable StringVar
        self.update_labels()


if __name__ == "__main__":
    try:
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "--nogui":
            # Mode console classique
            print(t("start_console"))
            clean_bedrock_directory()
            create_bedrock_structure()
            copy_all_item_textures()
            copy_sounds()
            copy_pack_icon()
            generate_manifest()
            items = extract_custom_model_data()
            generate_custom_items_json(items)
            generate_item_texture_json(items)
            generate_geyser_mapping_json(items)
            validate_geo_json_files(os.path.join(BEDROCK_RP_DIR, "models", "entity"))
            validate_consistency(items)
            # Ajout : demande du dossier de sortie et création du zip
            output_dir = input("Dossier de sortie pour le ZIP : ").strip()
            if output_dir:
                converted_name = os.path.basename(JAVA_RP_DIR.strip().rstrip("/\\"))
                zip_path = os.path.join(output_dir, f"{converted_name}.zip")
                import zipfile
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for rootdir, dirs, files in os.walk(BEDROCK_RP_DIR):
                        for file in files:
                            file_path = os.path.join(rootdir, file)
                            arcname = os.path.relpath(file_path, BEDROCK_RP_DIR)
                            zipf.write(file_path, arcname)
                print(f"✅ Pack exporté dans : {zip_path}")
            else:
                print("❌ Opération annulée : aucun dossier de sortie sélectionné.")
            print(t("console_done"))
        else:
            # Mode GUI
            root = tk.Tk()
            app = PackConverterGUI(root)
            root.mainloop()
            import sys
            sys.exit(0)
    except Exception as e:
        print(t("error", e=str(e)))
