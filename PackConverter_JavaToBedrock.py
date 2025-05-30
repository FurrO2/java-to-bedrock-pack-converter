import os
import shutil
import json
import uuid
from collections import defaultdict
import tempfile
import zipfile
from tkinter import ttk
import datetime
import hashlib
from decimal import Decimal, ROUND_HALF_UP
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

try:
    import yaml
except ImportError:
    print("Module 'yaml' non trouvé. Installe-le avec : pip install pyyaml")
    raise

# Charger les chemins depuis les variables d'environnement
JAVA_RP_DIR = os.environ.get("JAVA_RP_DIR", r"Put the path to your Java Resource Pack here")
TEMP_UNZIP_DIR = None

if JAVA_RP_DIR.lower().endswith('.zip') and os.path.isfile(JAVA_RP_DIR):
    TEMP_UNZIP_DIR = tempfile.mkdtemp(prefix="javarp_unzip_")
    with zipfile.ZipFile(JAVA_RP_DIR, 'r') as zip_ref:
        zip_ref.extractall(TEMP_UNZIP_DIR)
    JAVA_RP_DIR = TEMP_UNZIP_DIR + os.sep
else:
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
            
        # Handle textures with namespace preservation
        textures = bb_model.get('textures', {})
        # First try to get the textures with their namespace
        texture_list = []
        for tex_value in textures.values():
            # If texture has explicit namespace, preserve it
            if ':' in tex_value:
                texture_list.append(tex_value)
            else:
                # Try to infer namespace from model path
                model_ns = model_path.split('assets' + os.sep)[-1].split(os.sep)[0]
                if model_ns != 'minecraft':
                    texture_list.append(f"{model_ns}:{tex_value}")
                else:
                    texture_list.append(tex_value)
    except Exception as e:
        print(f"⚠️ Texture introuvable dans {model_path}: {e}")

    geo_name = f"{item_base_name.lower().replace(' ', '_')}_cmd{threshold}"
    # Use namespaced texture path if available
    tex_entry = texture_list[0] if texture_list else rel

    item_name = f"{item_base_name}_cmd{threshold}"
    items.append({
        "name": f"custom:{item_name}",
        "id": item_base_name,
        "custom_model_data": threshold,
        "display_name": f"§f{item_base_name.replace('_', ' ').title()} (CMD:{threshold})",
        "texture": tex_entry  # valeur brute
    })

    convert_java_model_to_geo(model_path, item_name, tex_entry)

def copy_all_item_textures(items=None):
    """
    Copie les textures en préservant la structure du namespace original.
    Par exemple: assets/custom_stuff_v1/textures/item/... -> textures/custom_stuff_v1/item/...
    """
    src_root = os.path.join(JAVA_RP_DIR, 'assets')
    if not os.path.exists(src_root):
        print("⚠️ Dossier assets non trouvé")
        return
        
    # Pour chaque namespace dans assets/
    for ns in os.listdir(src_root):
        ns_textures = os.path.join(src_root, ns, 'textures')
        if not os.path.isdir(ns_textures):
            continue
            
        # Parcours récursif des textures
        for root, dirs, files in os.walk(ns_textures):
            # Calcule le chemin relatif à partir de textures/
            rel_path = os.path.relpath(root, ns_textures)
            # Construit le chemin de destination en préservant le namespace
            dst_path = os.path.join(BEDROCK_RP_DIR, 'textures', ns, rel_path)
            
            # Crée le dossier de destination
            os.makedirs(dst_path, exist_ok=True)
            
            # Copie les fichiers
            for file in files:
                if file.endswith('.png'):
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dst_path, file)
                    shutil.copy2(src_file, dst_file)
    print(t("all_textures_copied"))

import os
import json
import traceback

def convert_java_model_to_geo(model_path, output_name, texture_key):
    try:
        print("🔄 Lecture du modèle Java avancée")
        with open(model_path, encoding='utf-8') as f:
            model = json.load(f)
            
        # Extraire le namespace et le chemin de la texture
        texture_namespace = "custom_stuff_v1"  # namespace par défaut
        texture_path = texture_key
        if ":" in texture_key:
            texture_namespace, texture_path = texture_key.split(":", 1)

        identifier = f"geometry.{output_name}"
        tex_w, tex_h = model.get('texture_size', [16, 16])
        bounds_width = model.get('visible_bounds_width', 2)
        bounds_height = model.get('visible_bounds_height', 2.5)
        bounds_offset = model.get('visible_bounds_offset', [0, 0.75, 0])
        elements = model.get('elements', [])
        groups = model.get('groups', [])
        print(f"➡️  {len(elements)} éléments, {len(groups)} groupes")

        def correct_uv_mapping(face, uv_data):
            # Si les UV ne sont pas valides, ne pas inclure la face
            if "uv" not in uv_data or len(uv_data['uv']) != 4:
                return None
            u0, v0, u1, v1 = uv_data['uv']
            if face in ["north", "east", "south", "west"]:
                uv = [round(u0, 3), round(v0, 3)]
                uv_size = [round(abs(u1 - u0), 3), round(abs(v1 - v0), 3)]
            elif face == "up":
                uv = [round(u1, 3), round(v1, 3)]
                uv_size = [round(abs(u1 - u0), 3), round(abs(v1 - v0), 3)]
            elif face == "down":
                uv = [round(u1, 3), round(v1, 3)]
                uv_size = [round(abs(u1 - u0), 3), -round(abs(v1 - v0), 3)]
            else:
                uv = [round(u0, 3), round(v0, 3)]
                uv_size = [round(abs(u1 - u0), 3), round(abs(v1 - v0), 3)]
            return {
                "uv": uv,
                "uv_size": uv_size
            }

        def round4(value):
            """Rounds a value to 4 decimal places."""
            return round(value, 4)

        def round6(value):
            """Rounds a value to 5 decimal places."""
            return round(value, 5)

        def make_cube(e):
            from_ = e.get('from', [0, 0, 0])
            to_ = e.get('to', [0, 0, 0])
            # X : -to[0] + 8, Y : from[1], Z : from[2] - 8
            origin_x = round6(-to_[0] + 8)
            origin_y = round6(from_[1])
            origin_z = round6(from_[2] - 8)
            size = [round6(to_[i] - from_[i]) for i in range(3)]
            # Gestion du pivot : si rotation.origin existe, utiliser la même logique que pour les groupes
            rot = e.get('rotation', {})
            if isinstance(rot, dict) and 'origin' in rot:
                pivot_raw = rot['origin']
                pivot_x = round6(-pivot_raw[0] + 8)
                pivot_y = round6(pivot_raw[1])
                pivot_z = round6(pivot_raw[2] - 8)
            else:
                # Centre géométrique
                pivot_x = round6(origin_x + size[0] / 2)
                pivot_y = round6(origin_y + size[1] / 2)
                pivot_z = round6(origin_z + size[2] / 2)
            cube = {
                "origin": [origin_x, origin_y, origin_z],
                "size": size,
                "uv": {},
                "pivot": [pivot_x, pivot_y, pivot_z]
            }
            if isinstance(rot, dict):
                angle = rot.get('angle', 0)
                axis = rot.get('axis', 'y')
                rotation = [0, 0, 0]
                # Multiplier l'angle par -1 pour X et Y
                if axis == 'x': rotation[0] = round6(-angle)
                elif axis == 'y': rotation[1] = round6(-angle)
                elif axis == 'z': rotation[2] = round6(angle)
                if any(abs(r) > 1e-6 for r in rotation):
                    cube["rotation"] = [r for r in rotation]
            for face, data in e.get('faces', {}).items():
                if data:
                    cube['uv'][face] = correct_uv_mapping(face, data)
            return cube

        def build_bone(group, name_counts=None):
            try:
                if name_counts is None:
                    name_counts = {}
                base_name = group.get('name', 'unnamed').replace(' ', '_')
                # Incrémente le compteur pour ce nom de groupe
                count = name_counts.get(base_name, 0) + 1
                name_counts[base_name] = count
                # Ajoute un suffixe si ce n'est pas le premier
                name = f"{base_name}{count if count > 1 else ''}"
                origin = group.get('origin', [8, 8, 8])
                # Pivot groupe : X : -origin[0] + 8, Y : origin[1], Z : origin[2] - 8
                bone_pivot = [round6(-origin[0] + 8), round6(origin[1]), round6(origin[2] - 8)]
                cubes = []
                children_bones = []
                cube_list = []
                for child in group.get('children', []):
                    if isinstance(child, int) and child < len(elements):
                        e = elements[child]
                        cube_list.append(e)
                    elif isinstance(child, dict):
                        child_bone = build_bone(child, name_counts)
                        if child_bone:
                            children_bones.append(child_bone)
                for e in cube_list:
                    cubes.append(make_cube(e))
                bone = {
                    "name": name,
                    "pivot": bone_pivot
                }
                if cubes:
                    bone["cubes"] = cubes
                if children_bones:
                    bone["children"] = [b["name"] for b in children_bones if isinstance(b, dict) and "name" in b]
                return bone
            except Exception as e:
                print(f"Error processing group {group.get('name')}: {e}")
                traceback.print_exc()
                return None

        bones = []
        # --- Collecte des éléments orphelins (non inclus dans un groupe) ---
        orphan_elements = []
        grouped_indices = set()
        if groups and isinstance(groups, list):
            for group in groups:
                if isinstance(group, dict):
                    for child in group.get('children', []):
                        if isinstance(child, int):
                            grouped_indices.add(child)
        all_indices = set(range(len(elements)))
        orphan_indices = all_indices - grouped_indices
        for idx in orphan_indices:
            orphan_elements.append((idx, elements[idx]))
        # --- Fin collecte ---

        if groups and isinstance(groups, list) and any(isinstance(g, dict) for g in groups):
            name_counts = {}
            for group in groups:
                if isinstance(group, dict):
                    built_bone = build_bone(group, name_counts=name_counts)
                    if built_bone:
                        bones.append(built_bone)
        # Ajout : écrire les orphelins dans un bone séparé (même logique de cube)
        if orphan_elements:
            cubes = []
            for idx, e in orphan_elements:
                cubes.append(make_cube(e))
            bones.insert(0, {
                "name": "bb_main",
                "pivot": [0, 0, 0],
                "cubes": cubes
            })
        else:
            for idx, e in enumerate(elements):
                cubes = [make_cube(e)]
                bone = {
                    "name": f"bone_{idx}",
                    "pivot": [0, 0, 0],
                    "cubes": cubes
                }
                bones.append(bone)

        item_display_transforms = {}
        if "display" in model:
            for key, data in model.get("display", {}).items():
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

        out_geo = os.path.join(BEDROCK_RP_DIR, 'models', 'entity', f'{output_name}.geo.json')
        print(f"💾 Écriture du fichier GEO : {out_geo}")
        with open(out_geo, 'w', encoding='utf-8') as f:
            json.dump(geo, f, indent='\t', separators=(',', ': '))

        # Utilise la valeur brute de texture_key pour le render_controller        # Create render controller with proper texture namespace handling
        rc = {
            "format_version": "1.8.0",
            "render_controllers": {
                f"controller.render.{output_name}": {
                    "geometry": identifier,
                    "materials": [ {"*": "material.default"} ],
                    "textures": f"Array.textures.{output_name}"
                }
            },
            "arrays": {
                "textures": {
                    f"Array.textures.{output_name}": [
                        # Use proper namespace:path format for textures, with fallback to minecraft namespace
                        texture_key if ":" in texture_key else f"minecraft:{texture_key}"
                    ]
                }
            }
        }
        out_rc = os.path.join(BEDROCK_RP_DIR, 'render_controllers', f'{output_name}.render_controller.json')
        print(f"💾 Écriture du fichier RenderController : {out_rc}")
        with open(out_rc, 'w', encoding='utf-8') as f:
            json.dump(rc, f, indent='\t', separators=(',', ': '))
        print(f"✅ Conversion avancée réussie: {output_name}")
    except Exception as e:
        print(f"❌ Conversion modèle {model_path}: {e}")
        traceback.print_exc()
        raise

# --- Conversion PNG8 ---
def convert_texture_to_png8(src, dst):
    if not PIL_AVAILABLE:
        print(f"⚠️ Pillow non installé, conversion PNG8 impossible pour {src}")
        shutil.copy2(src, dst)
        return
    try:
        from PIL import Image
        img = Image.open(src).convert("RGBA")
        img = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
        img.save(dst, optimize=True)
        print(f"✅ PNG8 généré : {dst}")
    except Exception as e:
        print(f"❌ Erreur PNG8 {src}: {e}")
        shutil.copy2(src, dst)

# --- Génération animation Bedrock ---
def convert_java_display_to_bedrock_animation(model_path, geometry):
    try:
        with open(model_path, encoding='utf-8') as f:
            model = json.load(f)
        display = model.get('display', {})
        bones = {}
        for key, data in display.items():
            bone_name = f"{geometry}_{key}"
            bones[bone_name] = {
                "rotation": data.get("rotation", [0,0,0]),
                "translation": data.get("translation", [0,0,0]),
                "scale": data.get("scale", [1,1,1])
            }
        return {
            "format_version": "1.8.0",
            "animations": {
                f"animation.{geometry}.display": {
                    "loop": True,
                    "bones": bones
                }
            }
        }
    except Exception as e:
        print(f"❌ Erreur animation Bedrock: {e}")
        return {}

# --- Génération attachable Bedrock ---
def generate_attachable_json(output_name, texture_key, geometry, out_dir):
    # Parse the texture_key to handle namespaced paths
    if ":" in texture_key:
        namespace, texture_path = texture_key.split(":", 1)
        # Format the texture path to preserve namespace structure
        texture_ref = f"textures/{namespace}/{texture_path}"
    else:
        # Default to minecraft namespace if none provided
        texture_ref = f"textures/minecraft/{texture_key}"

    attachable = {
        "format_version": "1.10.0",
        "minecraft:attachable": {
            "description": {
                "identifier": f"custom:{output_name}",
                "materials": {"default": "material.default"},
                "textures": {"default": texture_ref},
                "geometry": {"default": f"geometry.{output_name}"},
                "render_controllers": [f"controller.render.{output_name}"]
            }
        }
    }
    out_path = os.path.join(out_dir, f"{output_name}.attachable.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(attachable, f, indent=4)
    print(f"💾 Attachable généré : {out_path}")

# --- Génération fichiers de langue Bedrock ---
def write_lang_files(lang_dict, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    lang_path = os.path.join(out_dir, "en_US.lang")
    with open(lang_path, "w", encoding="utf-8") as f:
        for path_hash, item in lang_dict.items():
            entry = f'item.custom:{path_hash}.name={item}\n'
            f.write(entry)
    shutil.copy(lang_path, os.path.join(out_dir, "en_GB.lang"))
    with open(os.path.join(out_dir, "languages.json"), "w", encoding="utf-8") as f:
        json.dump(["en_US", "en_GB"], f)
    print(f"📝 Lang files générés dans {out_dir}")

# --- Orchestrateur fidèle au squelette ---
def hash7(s):
    return hashlib.md5(s.encode()).hexdigest()[:7]

def convert_model(model_path, item_name, generated, lang_dict, bedrock_dir):
    # 1. Génération d'un hash unique pour l'item
    path_hash = hash7(item_name)
    geometry = item_name
    
    # Detect namespace from item_name or model_path
    namespace = "minecraft"
    if ":" in item_name:
        namespace, _ = item_name.split(":", 1)
    else:
        # Try to detect from model_path
        model_dir = os.path.dirname(model_path)
        assets_dir = os.path.join(JAVA_RP_DIR, "assets")
        if model_dir.startswith(assets_dir):
            rel_path = os.path.relpath(model_dir, assets_dir)
            if os.path.sep in rel_path:
                namespace = rel_path.split(os.path.sep)[0]

    # 2. Conversion du modèle Java en geometry Bedrock avec namespace
    convert_java_model_to_geo(model_path, item_name, f"{namespace}:{item_name}")  
    
    # 3. Génération de l'animation Bedrock
    anim = convert_java_display_to_bedrock_animation(model_path, geometry)
    anim_dir = os.path.join(bedrock_dir, "animations")
    os.makedirs(anim_dir, exist_ok=True)
    anim_path = os.path.join(anim_dir, f"animation.{item_name}.json")
    with open(anim_path, 'w', encoding='utf-8') as f:
        json.dump(anim, f, indent=4)
        
    # 4. Génération du fichier attachable avec le bon namespace
    attachable_dir = os.path.join(bedrock_dir, "attachables")
    os.makedirs(attachable_dir, exist_ok=True)
    generate_attachable_json(item_name, f"{namespace}:{item_name}", geometry, attachable_dir)
    
    # 5. Ajout au dictionnaire lang
    lang_dict[path_hash] = item_name
    # 6. Conversion PNG8 de la texture si elle existe
    src_texture = os.path.join(bedrock_dir, "textures", "item", f"{item_name}.png")
    if os.path.isfile(src_texture):
        convert_texture_to_png8(src_texture, src_texture)

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
        # Remove namespace if present
        if ':' in clean_texture:
            clean_texture = clean_texture.split(':', 1)[1]
        # Remove leading slashes
        clean_texture = clean_texture.lstrip('/')
        # Remove all leading 'item/'
        while clean_texture.startswith('item/'):
            clean_texture = clean_texture[5:]
        bedrock_texture_path = f"textures/item/{clean_texture}"

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
                            "default": bedrock_texture_path
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
        
    for r, _, fs in os.walk(items_dir):
        for f in fs:
            if not f.lower().endswith(('.json','.yml','.yaml')):
                continue
                
            path = os.path.join(r, f)
            try:
                with open(path, encoding='utf-8') as pf:
                    data = yaml.safe_load(pf) if f.lower().endswith(('.yml','.yaml')) else json.load(pf)
                base = os.path.splitext(f)[0]
                
                for e in data.get('model',{}).get('entries',[]):
                    process_model_entry(e, base, tex_root, items, cmd_map, path)
                    
                fb = data.get('model',{}).get('fallback',{}).get('model')
                if fb:
                    process_model_entry({'threshold':-1,'model':{'model':fb}}, base, tex_root, items, cmd_map, path)
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
        texture_path = item['texture']  # Use original texture path
        cmd = item.get('custom_model_data', '')
        item_id = item['id']

        # Create a unique identifier for items with custom model data
        texture_id = f"{item_id}_cmd{cmd}" if cmd else item_id

        # Handle namespaced texture paths
        if ':' in texture_path:
            namespace, path = texture_path.split(':', 1)
            texture_data[texture_id] = {
                "textures": f"textures/{namespace}/{path}"
            }
        else:
            # Try to infer namespace from item id
            if ':' in item_id:
                namespace = item_id.split(':', 1)[0]
                texture_data[texture_id] = {
                    "textures": f"textures/{namespace}/{texture_path}"
                }
            else:
                # Default to minecraft namespace as fallback
                texture_data[texture_id] = {
                    "textures": f"textures/minecraft/{texture_path}"
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
    """
    Génère un mapping Geyser v2 conforme à l'API ItemMappings.
    Voir https://github.com/eclipseisoffline/geyser-example-mappings
    """
    mappings = {
        "format_version": 2,
        "items": {}
    }

    for item in items:
        base_item = item['id'] if item['id'].startswith("minecraft:") else f"minecraft:{item['id']}"
        cmd = str(item['custom_model_data'])
        unique_name = f"{item['id']}_cmd{item['custom_model_data']}"

        if base_item not in mappings["items"]:
            mappings["items"][base_item] = {
                "custom_model_data": {}
            }

        mappings["items"][base_item]["custom_model_data"][cmd] = {
            "bedrock_identifier": f"custom:{unique_name}",
            "display_name": item.get("display_name", ""),
            "texture": unique_name,
            "geometry": f"geometry.{unique_name}"
        }

    output_path = os.path.join(BEDROCK_RP_DIR, "geyser-mapping.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=4)
    print("✅ geyser-mapping.json generated in resource pack")


def create_mcpack(source_dir, output_dir, pack_name):
    import zipfile
    temp_dir = os.path.join(output_dir, 'temp_pack')
    mcpack_path = os.path.join(output_dir, f"{pack_name}.mcpack")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    shutil.copytree(source_dir, temp_dir)

    # Ensure geyser-mapping.json exists in temp dir
    geyser_mapping_path = os.path.join(source_dir, "geyser-mapping.json")
    temp_geyser_mapping = os.path.join(temp_dir, "geyser-mapping.json")
    if os.path.exists(geyser_mapping_path) and not os.path.exists(temp_geyser_mapping):
        shutil.copy2(geyser_mapping_path, temp_geyser_mapping)

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

LANG = "en"

import sys
if "--lang" in sys.argv:
    idx = sys.argv.index("--lang")
    if idx + 1 < len(sys.argv):
        LANG = sys.argv[idx + 1]

def t(key, **kwargs):
    value = TRANSLATIONS[LANG].get(key)
    if value is None:
        value = key
    return value.format(**kwargs)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'packconverter_config.json')

def load_last_java_dir():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('last_java_rp_dir', '')
    except Exception:
        return ''

def save_last_java_dir(path):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'last_java_rp_dir': path}, f)
    except Exception:
        pass

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
        last_java_dir = load_last_java_dir()
        self.java_dir = tk.StringVar(value=last_java_dir if last_java_dir else JAVA_RP_DIR)
        self.bedrock_dir = tk.StringVar(value="")  # Ajouté pour éviter l'erreur d'attribut

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
        # Bouton pour effacer les logs
        self.clear_logs_btn = tk.Button(self.logs_card, text="Effacer les logs", command=self.clear_logs, font=("Segoe UI", 9), bg="#e0e0e0")
        self.clear_logs_btn.pack(anchor="e", padx=10, pady=(0, 5))
        # Progress bar
        self.progress = ttk.Progressbar(self.logs_card, orient="horizontal", mode="determinate", length=400)
        self.progress.pack(fill="x", padx=10, pady=(5, 5))
        self.progress["value"] = 0
        self.progress["maximum"] = 100  
        self.logbox = scrolledtext.ScrolledText(self.logs_card, height=10, state="disabled", font=("Consolas", 10), bg="#fafafa")
        self.logbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Validation initiale des chemins
        self.java_dir.trace_add("write", lambda *args: self.validate_paths())
        self.validate_paths()

        self.last_logs = ""  # Ajout pour stocker les dernières logs

    def validate_paths(self):
        path = self.java_dir.get()
        is_valid = False
        if os.path.isdir(path):
            java_items_dir = os.path.normpath(os.path.join(path, 'assets', 'minecraft', 'items'))
            is_valid = os.path.isdir(java_items_dir) and any(
                f.lower().endswith(('.json', '.yml', '.yaml'))
                for f in os.listdir(java_items_dir)
            ) if os.path.isdir(java_items_dir) else False
        elif os.path.isfile(path) and path.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(path, 'r') as z:
                    # Cherche au moins un fichier items dans le zip
                    is_valid = any(
                        name.lower().startswith('assets/minecraft/items/') and
                        name.lower().endswith(('.json', '.yml', '.yaml'))
                        for name in z.namelist()
                    )
            except Exception:
                is_valid = False
        if is_valid:
            self.convert_btn.config(state="normal")
        else:
            self.convert_btn.config(state="disabled")

    def browse_java(self):
        path = filedialog.askopenfilename(
            title="Sélectionne le dossier ou le fichier ZIP du Java RP",
            filetypes=[("Dossier ou ZIP", "*.zip"), ("Tous les fichiers", "*.*")]
        )
        if not path:
            # Si rien n'est sélectionné, proposer un dossier
            path = filedialog.askdirectory(title="Sélectionne le dossier Java RP")
        if path:
            self.java_dir.set(path)
            save_last_java_dir(path)

    def browse_bedrock(self):
        path = filedialog.askdirectory(title="Sélectionne le dossier Bedrock RP")
        if path:
            self.bedrock_dir.set(path)

    def clear_logs(self):
        self.last_logs = ""
        self.logbox.config(state="normal")
        self.logbox.delete("1.0", "end")
        self.logbox.config(state="disabled")

    def log(self, msg):
        now = datetime.datetime.now().strftime("[%H:%M:%S] ")
        self.logbox.config(state="normal")
        for line in msg.splitlines():
            log_line = now + line + "\n"
            self.logbox.insert("end", log_line)
            self.last_logs += log_line
        self.logbox.see("end")
        self.logbox.config(state="disabled")
        self.root.update()

    def set_progress(self, value, maximum=None):
        if maximum is not None:
            self.progress["maximum"] = maximum
        self.progress["value"] = value
        self.root.update_idletasks()

    def run_conversion(self):
        import sys
        import io
        import tempfile
        import zipfile

        # Redirige stdout/stderr vers la logbox
        class TextRedirector(io.StringIO):
            def __init__(self, gui):
                super().__init__()
                self.gui = gui

            def write(self, s: str) -> int:
                self.gui.log(s.rstrip())
                return len(s.encode('utf-8'))

            def flush(self) -> None:
                pass

        sys.stdout = TextRedirector(self)
        sys.stderr = TextRedirector(self)

        self.convert_btn.config(state="disabled")
        try:
            # Met à jour les variables globales
            global JAVA_RP_DIR, BEDROCK_RP_DIR
            JAVA_RP_DIR = self.java_dir.get()
            bedrock_dir_value = self.bedrock_dir.get()
            if not bedrock_dir_value:
                bedrock_dir_value = tempfile.mkdtemp(prefix="bedrock_rp_")
            BEDROCK_RP_DIR = bedrock_dir_value
            if not BEDROCK_RP_DIR.endswith(os.sep):
                BEDROCK_RP_DIR += os.sep

            # Ajout : décompression du zip si besoin
            temp_unzip_dir = None
            if JAVA_RP_DIR.lower().endswith('.zip') and os.path.isfile(JAVA_RP_DIR):
                temp_unzip_dir = tempfile.mkdtemp(prefix="javarp_unzip_")
                with zipfile.ZipFile(JAVA_RP_DIR, 'r') as zip_ref:
                    zip_ref.extractall(temp_unzip_dir)
                JAVA_RP_DIR = temp_unzip_dir + os.sep

            # Barre de progression et étapes
            steps = [
                clean_bedrock_directory,
                create_bedrock_structure,
                copy_all_item_textures,
                copy_sounds,
                copy_pack_icon,
                generate_manifest,
                extract_custom_model_data,
                # Ajout : copie des textures après extraction des items
                copy_all_item_textures,
                generate_custom_items_json,
                generate_item_texture_json,
                generate_geyser_mapping_json,
                lambda: validate_geo_json_files(os.path.join(BEDROCK_RP_DIR, "models", "entity")),
                lambda: validate_consistency(items)
            ]
            self.set_progress(0, len(steps))
            items = []
            for i, step in enumerate(steps):
                self.log("-" * 40 + f"  Étape {i+1}/{len(steps)}  " + "-" * 40)
                if step == extract_custom_model_data:
                    items = step()
                elif step in (generate_custom_items_json, generate_item_texture_json, generate_geyser_mapping_json, validate_consistency):
                    step(items)
                else:
                    step()
                self.set_progress(i + 1)
                self.progress.update_idletasks()

            # Extraction des items custom
            items = extract_custom_model_data()
            # Conversion avancée pour chaque item (geometry, animation, attachable, PNG8, lang)
            lang_dict = {}
            for item in items:
                model_path = os.path.join(JAVA_RP_DIR, 'assets', 'minecraft', 'models', f"{item['texture']}.json")
                if not os.path.isfile(model_path):
                    # fallback: cherche dans tous les namespaces
                    for ns in os.listdir(os.path.join(JAVA_RP_DIR, 'assets')):
                        candidate = os.path.join(JAVA_RP_DIR, 'assets', ns, 'models', f"{item['texture']}.json")
                        if os.path.isfile(candidate):
                            model_path = candidate
                            break
                if os.path.isfile(model_path):
                    convert_model(model_path, item['texture'], True, lang_dict, BEDROCK_RP_DIR)
            # Génération des fichiers de langue Bedrock
            write_lang_files(lang_dict, os.path.join(BEDROCK_RP_DIR, "texts"))

            # Sélection du dossier de sortie par l'utilisateur
            output_dir = filedialog.askdirectory(title="Sélectionnez le dossier de sortie pour le ZIP")
            if not output_dir:
                self.log("❌ Opération annulée : aucun dossier de sortie sélectionné.")
                self.set_progress(0)
                self.convert_btn.config(state="normal")
                return

            # --- Détermination du nom du fichier exporté ---
            java_input_path = self.java_dir.get()
            if java_input_path.lower().endswith('.zip'):
                base_name = os.path.splitext(os.path.basename(java_input_path))[0]
            else:
                base_name = os.path.basename(JAVA_RP_DIR.strip().rstrip("/\\"))
            export_name = f"{base_name}[BConverted].zip"
            zip_path = os.path.join(output_dir, export_name)
            # --- Fin nom fichier ---

            # Création du fichier zip contenant tout le pack Bedrock
            import zipfile
            # --- Ajout : écrire les logs dans un fichier temporaire ---
            logs_path = os.path.join(BEDROCK_RP_DIR, "conversion_logs.txt")
            with open(logs_path, "w", encoding="utf-8") as f:
                f.write(self.last_logs)
            # --- Fin ajout logs ---
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for rootdir, dirs, files in os.walk(BEDROCK_RP_DIR):
                    for file in files:
                        file_path = os.path.join(rootdir, file)
                        arcname = os.path.relpath(file_path, BEDROCK_RP_DIR)
                        zipf.write(file_path, arcname)

            self.log(f"✅ Pack exporté dans : {zip_path}")
            messagebox.showinfo(t("success"), f"Pack exporté dans :\n{zip_path}")
            self.set_progress(0)
            self.convert_btn.config(state="normal")
        except Exception as e:
            self.log(t("error", e=str(e)))
            messagebox.showerror(t("error_title"), t("conversion_error", e=str(e)))
            self.set_progress(0)
            self.convert_btn.config(state="normal")

    def update_labels(self):
        # Met à jour tous les labels/boutons selon la langue
        self.lang_label.config(text=t("choose_language"))
        self.java_label.config(text=t("select_java_dir"))
        self.java_browse_btn.config(text=t("browse"))
        self.convert_btn.config(text=t("start_conversion"))
        self.logs_label.config(text=t("logs"))
        self.clear_logs_btn.config(text="Effacer les logs" if LANG == "fr" else "Clear logs")
        
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
            copy_all_item_textures(items)
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
