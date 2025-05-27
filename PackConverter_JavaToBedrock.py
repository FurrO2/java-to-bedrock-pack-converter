import os
import shutil
import json
import uuid
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("Module 'yaml' non trouvé. Installe-le avec : pip install pyyaml")
    raise

# Charger les chemins depuis les variables d'environnement
# Load paths from environment variables

JAVA_RP_DIR = os.environ.get("JAVA_RP_DIR", r"C:\\Users\\User_name\\Desktop\\converter\\java\\name_of_your_pack")
BEDROCK_RP_DIR = os.environ.get("BEDROCK_RP_DIR", r"C:\\Users\\User_name\\Desktop\\converter\\bedrock\\name_of_your_pack")
CUSTOM_ITEMS_FILE = "custom_items.json"
CUSTOM_NAMESPACE = "custom_stuff_v1"

if not JAVA_RP_DIR or not BEDROCK_RP_DIR:
    raise EnvironmentError("❌ JAVA_RP_DIR ou BEDROCK_RP_DIR n'est pas défini. Vérifie que les variables d'environnement sont bien passées.")

# Structure minimale
# Minimal structure
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
            print(f"🪟 Dossier supprimé : {target}")

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
    possible_paths = [
        os.path.join(JAVA_RP_DIR, 'assets', *rel.split('/')) + '.json',
        os.path.join(JAVA_RP_DIR, 'assets', CUSTOM_NAMESPACE, 'models', *rel.split('/')) + '.json',
        os.path.join(JAVA_RP_DIR, 'assets', 'minecraft', 'models', *rel.split('/')) + '.json'
    ]

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
    print("📁 Toutes les textures item copiées.")

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

        def correct_uv_mapping(face, uv_data):
            """Corrige le mapping UV selon les standards Bedrock"""
            if "uv" not in uv_data or len(uv_data['uv']) != 4:
                return {"uv": [0, 0], "uv_size": [1, 1]}
            
            u0, v0, u1, v1 = uv_data['uv']
            
            if face == "up":
                # CORRECTION: Pour la face du haut - mapping standard
                # FIX: For the top face - standard mapping
                return {
                    "uv": [round(u0, 5), round(v0, 5)],
                    "uv_size": [round(u1 - u0, 5), round(v1 - v0, 5)]
                }
            elif face == "down":
                # Pour la face du bas : inversion U et taille V négative
                # For the bottom face: U inversion and negative V size
                return {
                    "uv": [round(u1, 5), round(v1, 5)],
                    "uv_size": [round(u0 - u1, 5), round(v0 - v1, 5)]
                }
            else:
                # Faces latérales : mapping standard
                # Side faces: standard mapping
                return {
                    "uv": [round(u0, 5), round(v0, 5)],
                    "uv_size": [round(u1 - u0, 5), round(v1 - v0, 5)]
                }

        def calculate_pivot_from_origin(origin):
            """Calcule le pivot Bedrock à partir de l'origine Java"""
            # CORRECTION: Conversion standard Java -> Bedrock : X-8, Y inchangé, Z-8
            # FIX: Java -> Bedrock standard conversion: X-8, Y unchanged, Z-8
            return [
                round(origin[0] - 8, 5),
                round(origin[1], 5),
                round(origin[2] - 8, 5)
            ]

        def build_bone(group, parent_name=None):
            name = group['name'].replace(' ', '').lower()

            # Calcul du pivot selon l'origine du groupe
            # Calculation of the pivot according to the origin of the group
            if 'origin' in group and len(group['origin']) == 3:
                bone_pivot = calculate_pivot_from_origin(group['origin'])
            else:
                print(f"❗ Pivot manquant pour le groupe: {group.get('name', 'inconnu')}, pivot forcé [0,0,0]")
                bone_pivot = [0, 0, 0]

            cubes = []
            children_names = []
            sub_bones = []

            # Traitement des enfants du groupe
            # Treatment of children in the group
            for child in group.get('children', []):
                if isinstance(child, int):
                    # Enfant = élément géométrique
                    # Child = geometric element
                    e = elements[child]
                    
                    # Conversion des coordonnées Java vers Bedrock
                    # Converting coordinates from Java to Bedrock
                    cube_origin = [
                        round(e['from'][0] - 8, 5),
                        round(e['from'][1], 5),
                        round(e['from'][2] - 8, 5)
                    ]
                    size = [round(e['to'][i] - e['from'][i], 5) for i in range(3)]

                    cube = {
                        "origin": cube_origin,
                        "size": size,
                        "uv": {}
                    }

                    # Mapping UV corrigé pour chaque face
                    # Corrected UV mapping for each face
                    for face, data in e.get('faces', {}).items():
                        cube['uv'][face] = correct_uv_mapping(face, data)

                    cubes.append(cube)

                elif isinstance(child, dict):
                    # Enfant = sous-groupe (bone enfant)
                    # Child = subgroup (child bone)
                    nested_bones = build_bone(child, parent_name=name)
                    sub_bones.extend(nested_bones)
                    children_names.append(nested_bones[0]['name'])

            # Construction de l'os
            # Bone construction
            bone = {
                "name": name,
                "pivot": bone_pivot
            }
            
            # Ajout des cubes s'il y en a
            # Adding cubes if there are any
            if cubes:
                bone["cubes"] = cubes
            
            # CORRECTION: Hiérarchie parent-enfant correcte
            # FIX: Correct parent-child hierarchy
            if parent_name:
                bone["parent"] = parent_name
            if children_names:
                bone['children'] = children_names

            print(f"✅ Bone finalisé: {name} avec {len(cubes)} cubes, parent={parent_name}")
            return [bone] + sub_bones

        # Construction de tous les os à partir des groupes
        # Construction of all bones from groups
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
        # Building display transformations
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
        # Final assembly of the geometric file
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
        # Writing the .geo.json file
        out_geo = os.path.join(BEDROCK_RP_DIR, 'models', 'entity', f'{output_name}.geo.json')
        print(f"💾 Écriture du fichier GEO : {out_geo}")
        with open(out_geo, 'w', encoding='utf-8') as f:
            json.dump(geo, f, indent='\t', separators=(',', ': '))

        # Génération du render controller
        # Generating the render controller
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









### Sounds don't seem to be converted, i think geyser don't allow that part
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
                            # Automatic "stream" detection for long music
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
        print("🔊 Sons copiés + sound_definitions.json généré.")
    else:
        print("🔇 Aucun son trouvé à copier.")

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
    print("📝 Manifest généré.")

def validate_geo_json_files(directory):
    print("🔍 Validation des fichiers .geo.json...")
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
    print(f"✅ Validation terminée ({count} fichiers .geo.json valides)")

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
    print("✅ custom_items.json généré")

def extract_custom_model_data():
    items,cmd_map=[],{}
    items_dir=os.path.join(JAVA_RP_DIR,'assets','minecraft','items')
    tex_root=os.path.join(BEDROCK_RP_DIR,'textures','item')
    if not os.path.isdir(items_dir): print(f"❌ Introuvable: {items_dir}"); return items
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
    # Shows the Java assets folder structure for debugging
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
    print("✅ item_texture.json généré")

def generate_behavior_pack(items):
    bp_dir = BEDROCK_RP_DIR.replace('bedrock', 'behavior')
    if os.path.exists(bp_dir):
        shutil.rmtree(bp_dir)
    os.makedirs(os.path.join(bp_dir, 'items'), exist_ok=True)

    # Manifest for behavior pack
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
        
    # Generate each item file
    # Générer chaque fichier item
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
        # Create structure if absent
        if base_item not in mappings["items"]:
            mappings["items"][base_item] = {
                "custom_model_data": {}
            }

        # Ajouter le mapping pour ce CustomModelData
        # Add the mapping for this CustomModelData
        mappings["items"][base_item]["custom_model_data"][cmd] = {
            "bedrock_identifier": base_item,  # Peut être adapté si nécessaire / # Can be adapted if necessary
            "display_name": item.get("display_name", "")
        }

    output_path = os.path.join(BEDROCK_RP_DIR.replace("bedrock", "geyser_mappings"), "geyser-mapping.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=4)
    print("✅ Fichier geyser-mapping.json généré correctement.")


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

    print(f"✅ Fichier .mcpack créé : {mcpack_path}")

def validate_consistency(items):
    print("🔎 Validation de cohérence entre les fichiers...")
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
            print(f"❌ GEO manquant : {name}.geo.json")
            errors += 1

        if not os.path.isfile(rc_file):
            print(f"❌ Render controller manquant : {name}.render_controller.json")
            errors += 1
            continue

        try:
            with open(rc_file, encoding='utf-8') as f:
                rc = json.load(f)
            expected_geometry = f"geometry.{name}"
            actual_geometry = rc["render_controllers"][f"controller.render.{name}"]["geometry"]
            if actual_geometry != expected_geometry:
                print(f"⚠️ Mauvais identifiant de géométrie : {actual_geometry} (attendu: {expected_geometry})")
                errors += 1

            tex_array = rc.get("arrays", {}).get("textures", {}).get(f"Array.textures.{name}", [])
            if not tex_array or not os.path.isfile(os.path.join(BEDROCK_RP_DIR, tex_array[0] + ".png")):
                print(f"⚠️ Texture introuvable ou incorrecte pour {name}: {tex_array}")
                errors += 1
        except Exception as e:
            print(f"❌ Erreur lecture {name}.render_controller.json: {e}")
            errors += 1

        if not os.path.isfile(expected_texture):
            print(f"❌ Fichier texture manquant : {expected_texture}")
            errors += 1

    print(f"✅ Validation cohérence terminée ({len(items) - errors} valides / {len(items)} total)")

def copy_pack_icon():
    src = os.path.join(JAVA_RP_DIR, "pack.png")
    dst = os.path.join(BEDROCK_RP_DIR, "pack_icon.png")
    if os.path.isfile(src):
        shutil.copy(src, dst)
        print("🖼️ pack_icon.png copié depuis pack.png")
    else:
        print("⚠️ Aucun pack.png trouvé à copier.")

if __name__ == '__main__':
    print("⏳ Démarrage conversion...")
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
    final_output_dir = os.path.join(os.path.dirname(BEDROCK_RP_DIR), 'final_output')
    os.makedirs(final_output_dir, exist_ok=True)
    converted_name = os.path.basename(JAVA_RP_DIR.strip().rstrip("/\\"))
    create_mcpack(BEDROCK_RP_DIR, final_output_dir, converted_name)
    print("✅ Conversion terminée.")
