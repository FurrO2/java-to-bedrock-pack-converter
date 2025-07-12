import os
import subprocess
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

# --- Auto-install required packages if missing ---
def ensure_package(pkg, import_name=None):
    import_name = import_name or pkg
    try:
        __import__(import_name)
        return True
    except ImportError:
        print(f"[Setup] Installation du package requis : {pkg}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        try:
            __import__(import_name)
            return True
        except ImportError:
            print(f"[Setup] Erreur lors de l'installation de {pkg}. Veuillez l'installer manuellement.")
            return False

# Vérifie et installe Pillow, PyYAML, orjson si besoin
PIL_AVAILABLE = ensure_package("Pillow", "PIL")
YAML_AVAILABLE = ensure_package("PyYAML", "yaml")
ORJSON_AVAILABLE = ensure_package("orjson")

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import glob
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# --- TRANSLATIONS block and t() function must be defined before any use of t() ---
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
        "java_assets_structure": "🔍 Structure du pack Java assets :",
        "clear_logs": "Effacer les logs",
        "export_format": "Format d'export :",
        "writing_geo_file": "💾 Écriture du fichier GEO : {out_geo}",
        "writing_render_controller_file": "💾 Écriture du fichier RenderController : {out_rc}",
        "conversion_success_advanced": "✅ Conversion avancée réussie: {output_name}",
        "conversion_model_error": "❌ Conversion modèle {model_path}: {error}",
        "missing_yaml_module": "❌ Le module YAML n'est pas installé. Veuillez l'installer avec `pip install pyyaml`.",
        "model_not_found": "❌ Modèle non trouvé : {rel}",
        "texture_not_found": "❌ Texture non trouvée dans le modèle {model_path} : {error}",
        "assets_folder_not_found": "❌ Dossier assets non trouvé dans le pack Java.",
        "pillow_not_installed": "❌ Le module Pillow n'est pas installé. Veuillez l'installer avec `pip install Pillow`.",
        "png8_generated": "✅ PNG8 généré : {dst}",
        "png8_error": "❌ Erreur lors de la génération du PNG8 depuis {src} : {error}",
        "bedrock_animation_error": "❌ Erreur lors de la génération de l'animation Bedrock : {error}",
        "attachable_generated": "✅ Fichier attachable généré : {out_path}",
        "lang_files_generated": "✅ Fichiers de langue générés dans {out_dir}",
        "reading_java_model": "📖 Lecture du modèle Java...",
        "elements_and_groups": "🔍 Nombre d'éléments : {elements}, groupes : {groups}",
        "item_texture_json_generated": "✅ item_texture.json généré",
        "item_texture_not_found": "❌ Texture non trouvée pour l'item {item_name} : {error}",
        "pack_exported_folder_msg": "✅ Dossier exporté : {out_dir}",
        "pack_exported_folder_title": "Dossier exporté",
        "pack_exported_zip_msg": "✅ Fichier .mcpack exporté : {out_zip}",
        "pack_exported_zip_title": "Fichier .mcpack exporté",
        "pack_exported_zip_error": "❌ Erreur lors de l'exportation du fichier .mcpack : {error}",
        "pack_exported_zip_success": "✅ Fichier .mcpack exporté avec succès : {out_zip}",
        "java_rp_placeholder": "Chemin du dossier Resource Pack Java (ou ZIP)",
        "bedrock_rp_placeholder": "Chemin du dossier Resource Pack Bedrock (ou ZIP)",
        "geyser_mapping_format": "Format Geyser Mapping :",
        "geyser_mapping_v1": "v1 (simple)",
        "geyser_mapping_v2": "v2 (avancé)"
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
        "java_assets_structure": "🔍 Java pack assets structure:",
        "clear_logs": "Clear logs",
        "export_format": "Export format:",
        "writing_geo_file": "💾 Writing GEO file: {out_geo}",
        "writing_render_controller_file": "💾 Writing RenderController file: {out_rc}",
        "conversion_success_advanced": "✅ Advanced conversion successful: {output_name}",
        "conversion_model_error": "❌ Model conversion error {model_path}: {error}",
        "missing_yaml_module": "❌ YAML module is not installed. Please install it with `pip install pyyaml`.",
        "model_not_found": "❌ Model not found: {rel}",
        "texture_not_found": "❌ Texture not found in model {model_path}: {error}",
        "assets_folder_not_found": "❌ Assets folder not found in the Java pack.",
        "pillow_not_installed": "❌ Pillow module is not installed. Please install it with `pip install Pillow`.",
        "png8_generated": "✅ PNG8 generated: {dst}",
        "png8_error": "❌ Error generating PNG8 from {src}: {error}",
        "bedrock_animation_error": "❌ Error generating Bedrock animation: {error}",
        "attachable_generated": "✅ Attachable file generated: {out_path}",
        "lang_files_generated": "✅ Language files generated in {out_dir}",
        "elements_and_groups": "🔍 Number of elements: {elements}, groups: {groups}",
        "reading_java_model": "📖 Reading Java model...",
        "item_texture_json_generated": "✅ item_texture.json generated",
        "item_texture_not_found": "❌ Texture not found for item {item_name}: {error}",
        "pack_exported_folder_msg": "✅ Folder exported: {out_dir}",
        "pack_exported_folder_title": "Folder exported",
        "pack_exported_zip_msg": "✅ .mcpack file exported: {out_zip}",
        "pack_exported_zip_title": ".mcpack file exported",
        "pack_exported_zip_error": "❌ Error exporting .mcpack file: {error}",
        "pack_exported_zip_success": "✅ .mcpack file exported successfully: {out_zip}",
        "java_rp_placeholder": "Path to Java Resource Pack folder (or ZIP)",
        "bedrock_rp_placeholder": "Path to Bedrock Resource Pack folder (or ZIP)",
        "geyser_mapping_format": "Geyser Mapping format:",
        "geyser_mapping_v1": "v1 (simple)",
        "geyser_mapping_v2": "v2 (advanced)"
    }
}

LANG = "en"


def t(key, **kwargs):
    value = TRANSLATIONS[LANG].get(key)
    if value is None:
        value = key
    return value.format(**kwargs)

try:
    import yaml
except ImportError:
    print(t("missing_yaml_module"))
    raise

# Charger les chemins depuis les variables d'environnement
JAVA_RP_DIR = os.environ.get("JAVA_RP_DIR", t("java_rp_placeholder"))
TEMP_UNZIP_DIR = None

if JAVA_RP_DIR.lower().endswith('.zip') and os.path.isfile(JAVA_RP_DIR):
    TEMP_UNZIP_DIR = tempfile.mkdtemp(prefix="javarp_unzip_")
    with zipfile.ZipFile(JAVA_RP_DIR, 'r') as zip_ref:
        zip_ref.extractall(TEMP_UNZIP_DIR)
    JAVA_RP_DIR = TEMP_UNZIP_DIR + os.sep
else:
    if not JAVA_RP_DIR.endswith(os.sep):
        JAVA_RP_DIR += os.sep

BEDROCK_RP_DIR = os.environ.get("BEDROCK_RP_DIR", t("bedrock_rp_placeholder"))
if not BEDROCK_RP_DIR.endswith(os.sep):
    BEDROCK_RP_DIR += os.sep
CUSTOM_ITEMS_FILE = "custom_items.json"

if not JAVA_RP_DIR or not BEDROCK_RP_DIR:
    raise EnvironmentError(t("no_java_dir"))

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
    # Ajout : Génération automatique du manifest.json Bedrock après création de la structure
    if 'generate_manifest' in globals():
        generate_manifest()

def process_model_entry(entry, item_base_name, texture_root, items, cmd_map, source_file, model_index=None):
    model_ref = entry.get('model', {}).get('model') or entry.get('model')
    if not model_ref:
        return
    threshold = entry.get('threshold', 0)

    rel = model_ref.split(':', 1)[-1] if ':' in model_ref else model_ref
    # Utilisation de l'index pour lookup rapide
    model_path = None
    if model_index is not None:
        # Essaye d'abord model_ref tel quel
        if ':' in model_ref:
            model_path = model_index.get(model_ref)
        # Sinon, essaye tous les namespaces
        if not model_path:
            for ns in model_index:
                if ns.endswith(f':{rel}'):
                    model_path = model_index[ns]
                    break
    # Fallback legacy (si pas trouvé dans l'index)
    if not model_path:
        assets_root = os.path.join(JAVA_RP_DIR, 'assets')
        possible_paths = [
            os.path.join(assets_root, *rel.split('/')) + '.json'
        ]
        if os.path.isdir(assets_root):
            for ns in os.listdir(assets_root):
                ns_model = os.path.join(assets_root, ns, 'models', *rel.split('/')) + '.json'
                possible_paths.append(ns_model)
        possible_paths.append(os.path.join(assets_root, 'minecraft', 'models', *rel.split('/')) + '.json')
        model_path = next((p for p in possible_paths if os.path.isfile(p)), None)
    if not model_path:
        print(t("model_not_found", rel=rel))
        return

    texture_list = []
    try:
        with open(model_path, encoding='utf-8') as f:
            bb_model = json.load(f)
        textures = bb_model.get('textures', {})
        texture_list = []
        for tex_value in textures.values():
            if ':' in tex_value:
                texture_list.append(tex_value)
            else:
                model_ns = model_path.split('assets' + os.sep)[-1].split(os.sep)[0]
                if model_ns != 'minecraft':
                    texture_list.append(f"{model_ns}:{tex_value}")
                else:
                    texture_list.append(tex_value)
    except Exception as e:
        print(t("texture_not_found", model_path=model_path, error=str(e)))

    geo_name = f"{item_base_name.lower().replace(' ', '_')}_cmd{threshold}"
    tex_entry = texture_list[0] if texture_list else rel
    # Correction : transformer le chemin Java en chemin Bedrock
    # Ex : custom_stuff_v1:item/coins/1 -> textures/custom_stuff_v1/item/coins/1.png
    if ':' in tex_entry:
        ns, tex_path = tex_entry.split(':', 1)
        bedrock_texture_path = f"textures/{ns}/{tex_path}.png"
        tex_name_for_rc = f"{ns}/{tex_path}"
    else:
        bedrock_texture_path = f"textures/item/{tex_entry}.png"
        tex_name_for_rc = tex_entry
    item_name = f"{item_base_name}_cmd{threshold}"
    items.append({
        "name": f"custom:{item_name}",
        "id": item_base_name,
        "custom_model_data": threshold,
        "display_name": f"§f{item_base_name.replace('_', ' ').title()} (CMD:{threshold})",
        "texture": tex_entry,
        "bedrock_texture_path": bedrock_texture_path,
        "tex_name_for_rc": tex_name_for_rc
    })
    convert_java_model_to_geo(model_path, item_name, tex_entry, bedrock_texture_path, tex_name_for_rc)

def copy_all_item_textures():
    """
    Copie les textures en préservant la structure du namespace original.
    Par exemple: assets/custom_stuff_v1/textures/item/... -> textures/custom_stuff_v1/item/...
    """
    import time
    start = time.time()
    src_root = os.path.join(JAVA_RP_DIR, 'assets')
    if not os.path.exists(src_root):
        print(t("assets_folder_not_found"))
        return
    copy_jobs = []
    ns_list = os.listdir(src_root)
    print(f"[Textures] {len(ns_list)} namespaces à traiter...")
    for ns in ns_list:
        ns_textures = os.path.join(src_root, ns, 'textures')
        if not os.path.isdir(ns_textures):
            continue
        for root, dirs, files in os.walk(ns_textures):
            rel_path = os.path.relpath(root, ns_textures)
            dst_path = os.path.join(BEDROCK_RP_DIR, 'textures', ns, rel_path)
            os.makedirs(dst_path, exist_ok=True)
            for file in files:
                if file.endswith('.png'):
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dst_path, file)
                    copy_jobs.append((src_file, dst_file))
    print(f"[Textures] {len(copy_jobs)} fichiers à copier...")
    def do_copy(src, dst):
        shutil.copy2(src, dst)
    run_parallel(do_copy, copy_jobs)
    print(t("all_textures_copied"))
    print(f"[Textures] Copie terminée en {round(time.time()-start,1)}s.")

import os
import json
import traceback

# --- Patch: JSON parser rapide (orjson si dispo) ---
try:
    import orjson
    def fast_json_load(f):
        # orjson expects bytes, so read in 'rb' mode
        if hasattr(f, 'buffer'):
            return orjson.loads(f.buffer.read())
        else:
            return orjson.loads(f.read())
except ImportError:
    def fast_json_load(f):
        return json.load(f)

def convert_java_model_to_geo(model_path, output_name, texture_key, bedrock_texture_path=None, tex_name_for_rc=None):
    start_time = time.time()
    try:
        print(t("reading_java_model"))
        with open(model_path, encoding='utf-8') as f:
            # Lecture RAM + parsing rapide
            model = fast_json_load(f)
        
        # Extraire le namespace et le chemin de la texture
        texture_namespace = "minecraft"  # namespace par défaut
        texture_path = texture_key
        if ":" in texture_key:
            texture_namespace, texture_path = texture_key.split(":", 1)

        identifier = f"geometry.{output_name}"
        tex_w, tex_h = model.get('texture_size', [16, 16])
        # Si texture_size est spécifié, divise par 2 pour l'output Bedrock
        if 'texture_size' in model:
            tex_w = int(tex_w // 2)
            tex_h = int(tex_h // 2)
        bounds_width = model.get('visible_bounds_width', 2)
        bounds_height = model.get('visible_bounds_height', 2.5)
        bounds_offset = model.get('visible_bounds_offset', [0, 0.75, 0])
        elements = model.get('elements', [])
        groups = model.get('groups', [])
        print(t("elements_and_groups", elements=len(elements), groups=len(groups)))

        def correct_uv_mapping(face, uv_data):
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
            return round(value, 4)

        def round6(value):
            return round(value, 6)

        def make_cube(e):
            from_ = e.get('from', [0, 0, 0])
            to_ = e.get('to', [0, 0, 0])
            origin_x = round6(-to_[0] + 8)
            origin_y = round6(from_[1])
            origin_z = round6(from_[2] - 8)
            size = [round6(to_[i] - from_[i]) for i in range(3)]
            rot = e.get('rotation', {})
            if isinstance(rot, dict) and 'origin' in rot:
                pivot_raw = rot['origin']
                pivot_x = round6(-pivot_raw[0] + 8)
                pivot_y = round6(pivot_raw[1])
                pivot_z = round6(-pivot_raw[2] + 8)
            else:
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
                count = name_counts.get(base_name, 0) + 1
                name_counts[base_name] = count
                name = f"{base_name}{count if count > 1 else ''}"
                origin = group.get('origin', [8, 8, 8])
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
                # Only return bone if it has cubes or children
                if cubes or children_bones:
                    return bone
                return None
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
            # Only add orphan bone if there are truly orphan elements
            if orphan_elements:
                cubes = []
                for idx, e in orphan_elements:
                    cubes.append(make_cube(e))
                bones.append({
                    "name": "bb_main",
                    "pivot": [0, 0, 0],
                    "cubes": cubes
                })
        else:
            # No groups: one bone per element
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
        os.makedirs(os.path.dirname(out_geo), exist_ok=True)
        print(t("writing_geo_file", out_geo=out_geo))
        with open(out_geo, 'w', encoding='utf-8') as f:
            json.dump(geo, f, indent='\t', separators=(',', ': '))

        # Correction: le nom de la texture dans le render_controller doit correspondre au chemin copié depuis le pack Java
        # On utilise tex_entry (chemin brut issu du modèle Java)
        # Remplace les ':' par '/' dans le chemin de texture pour Bedrock
        tex_name = texture_key.replace(':', '/')
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
                    f"Array.textures.{output_name}": [tex_name]
                }
            }
        }
        out_rc = os.path.join(BEDROCK_RP_DIR, 'render_controllers', f'{output_name}.render_controller.json')
        os.makedirs(os.path.dirname(out_rc), exist_ok=True)
        print(t("writing_render_controller_file", out_rc=out_rc))
        with open(out_rc, 'w', encoding='utf-8') as f:
            json.dump(rc, f, indent='\t', separators=(',', ': '))
        print(t("conversion_success_advanced", output_name=output_name))

        # --- Génération d'une seule animation Bedrock par item ---
        anim_dir = os.path.join(BEDROCK_RP_DIR, 'animations')
        os.makedirs(anim_dir, exist_ok=True)
        # Essayons d'utiliser les données display du modèle Java si elles existent
        animation_data = None
        try:
            with open(model_path, encoding='utf-8') as f:
                model_data = json.load(f)
            display = model_data.get('display', {})
            # Structure d'animation avancée, similaire aux exemples fournis
            bones_anim = {}
            # Pour chaque perspective, crée une animation si les données existent
            for key, data in display.items():
                # Noms de bones typiques : main_hand, off_hand, head, etc.
                bone_name = key.lower()
                bones_anim[bone_name] = {}
                if 'rotation' in data:
                    bones_anim[bone_name]['rotation'] = data['rotation']
                if 'translation' in data:
                    bones_anim[bone_name]['position'] = data['translation']
                if 'scale' in data:
                    bones_anim[bone_name]['scale'] = data['scale']
            # Compose l'animation unique
            animation_data = {
                "format_version": "1.8.0",
                "animations": {
                    f"animation.{output_name}": {
                        "loop": True,
                        "bones": bones_anim
                    }
                }
            }
        except Exception as e:
            print(f"[Animation] Erreur lors de la lecture des données display du modèle : {e}")
        # Fallback si aucune donnée display n'est trouvée
        if not animation_data:
            # Utilise la position du root bone comme fallback
            rightitem_pos = [0, 0, 0]
            if bones:
                root_bone = bones[0]
                if isinstance(root_bone, dict) and "pivot" in root_bone:
                    rightitem_pos = [float(round(v, 3)) for v in root_bone["pivot"]]
            animation_data = {
                "format_version": "1.8.0",
                "animations": {
                    f"animation.{output_name}": {
                        "loop": True,
                        "bones": {
                            "main_hand": {
                                "position": rightitem_pos
                            }
                        }
                    }
                }
            }
        anim_path = os.path.join(anim_dir, f"animation.{output_name}.json")
        with open(anim_path, 'w', encoding='utf-8') as f:
            json.dump(animation_data, f, indent=4)
        print(f"[Animation] Animation Bedrock générée : {anim_path}")
    except Exception as e:
        print(t("conversion_model_error", model_path=model_path, error=str(e)))
        traceback.print_exc()
        return
    elapsed = time.time() - start_time
    print(f"[Profiling] Conversion {output_name} en {elapsed:.2f}s")

# --- Conversion PNG8 ---
def convert_texture_to_png8(src, dst):
    if not PIL_AVAILABLE:
        print(t("pillow_not_installed", src=src))
        shutil.copy2(src, dst)
        return
    try:
        from PIL import Image
        img = Image.open(src).convert("RGBA")
        img = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
        img.save(dst, optimize=True)
        print(t("png8_generated", dst=dst))
    except Exception as e:
        print(t("png8_error", src=src, error=str(e)))
        shutil.copy2(src, dst)

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
    print(t("lang_files_generated", out_dir=out_dir))

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
    
# --- Génération animation Bedrock ---
def convert_java_display_to_bedrock_animation(model_path, geometry):
    try:
        with open(model_path, encoding='utf-8') as f:
            model = json.load(f)
        display = model.get('display', {})
        pose_to_bone = {
            "thirdperson_righthand": "thirdperson_righthand",
            "thirdperson_lefthand": "thirdperson_lefthand",
            "firstperson_righthand": "firstperson_righthand",
            "firstperson_lefthand": "firstperson_lefthand",
            "gui": "gui",
            "head": "head",
            "ground": "ground"
        }
        bones = {}
        for pose, bone in pose_to_bone.items():
            if pose in display:
                data = display[pose]
                bone_entry = {}
                if 'translation' in data:
                    bone_entry['position'] = [round(float(x), 5) for x in data['translation']]
                if 'rotation' in data:
                    bone_entry['rotation'] = [round(float(x), 5) for x in data['rotation']]
                if 'scale' in data:
                    scale = data['scale']
                    if isinstance(scale, (int, float)):
                        bone_entry['scale'] = round(float(scale), 5)
                    elif isinstance(scale, (list, tuple)):
                        bone_entry['scale'] = [round(float(x), 5) for x in scale]
                if bone_entry:
                    bones[bone] = bone_entry
        if 'thirdperson_righthand' in bones and 'thirdperson_lefthand' not in bones:
            bones['thirdperson_lefthand'] = bones['thirdperson_righthand'].copy()
        if 'thirdperson_lefthand' in bones and 'thirdperson_righthand' not in bones:
            bones['thirdperson_righthand'] = bones['thirdperson_lefthand'].copy()
        if 'firstperson_righthand' in bones and 'firstperson_lefthand' not in bones:
            bones['firstperson_lefthand'] = bones['firstperson_righthand'].copy()
        if 'firstperson_lefthand' in bones and 'firstperson_righthand' not in bones:
            bones['firstperson_righthand'] = bones['firstperson_lefthand'].copy()
        return {
            "format_version": "1.8.0",
            "animations": {
                f"animation.{geometry}": {
                    "loop": True,
                    "bones": bones
                }
            }
        }
    except Exception as e:
        print(t("bedrock_animation_error", error=str(e)))
        return {}
    
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
        if ':' in clean_texture:
            clean_texture = clean_texture.split(':', 1)[1]
        clean_texture = clean_texture.lstrip('/')
        while clean_texture.startswith('item/'):
            clean_texture = clean_texture[5:]
        # Correction: enlever les ':' dans le chemin de fichier
        clean_texture = clean_texture.replace(':', '/').replace('//', '/')
        bedrock_texture_path = f"textures/item/{clean_texture}"
        # Correction: vérifier la présence du fichier PNG et fallback si besoin
        icon_name = texture
        png_path = os.path.join(BEDROCK_RP_DIR, "textures", "item", f"{icon_name}.png")
        if not os.path.isfile(png_path):
            alt_icon_name = texture.replace("minecraft:", "")
            alt_png_path = os.path.join(BEDROCK_RP_DIR, "textures", "item", f"{alt_icon_name}.png")
            if os.path.isfile(alt_png_path):
                icon_name = alt_icon_name
            else:
                alt_icon_name2 = alt_icon_name.lower()
                alt_png_path2 = os.path.join(BEDROCK_RP_DIR, "textures", "item", f"{alt_icon_name2}.png")
                if os.path.isfile(alt_png_path2):
                    icon_name = alt_icon_name2
        custom_entry = {
            "name": texture,
            "id": texture,
            "components": {
                "minecraft:icon": icon_name,
                "minecraft:render_offsets": "tools",
                "minecraft:custom_components": {
                    "custom_model_data": float(cmd)
                },
                "minecraft:display_name": {
                    "value": f"§f{base_name.replace('_', ' ').title()} (CMD:{cmd})"
                },
                "minecraft:material_instances": {
                    "*": {
                        "texture": icon_name,
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
                    "texture": icon_name
                }
            }
        }
        custom_items.append(custom_entry)
    output_path = os.path.join(BEDROCK_RP_DIR, "custom_items.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(custom_items, f, indent=4)
    print(t("custom_items_generated"))

def extract_custom_model_data(model_index=None):
    start = time.time()
    items, cmd_map = [], {}
    items_dir = os.path.join(JAVA_RP_DIR, 'assets', 'minecraft', 'items')
    items_dir = os.path.normpath(items_dir)
    tex_root = os.path.join(BEDROCK_RP_DIR, 'textures', 'item')
    if not os.path.isdir(items_dir):
        print(t("items_folder_not_found", items_dir=items_dir))
        return items
    file_list = [os.path.join(r, f) for r, _, fs in os.walk(items_dir) for f in fs if f.lower().endswith(('.json','.yml','.yaml'))]
    print(f"[CustomModelData] {len(file_list)} fichiers à traiter...")
    count = 0
    for path in file_list:
        f = os.path.basename(path)
        try:
            with open(path, encoding='utf-8') as pf:
                data = yaml.safe_load(pf) if f.lower().endswith(('.yml','.yaml')) else json.load(pf)
            base = os.path.splitext(f)[0]
            for e in data.get('model',{}).get('entries',[]):
                process_model_entry(e, base, tex_root, items, cmd_map, path, model_index=model_index)
            fb = data.get('model',{}).get('fallback',{}).get('model')
            if fb:
                process_model_entry({'threshold':-1,'model':{'model':fb}}, base, tex_root, items, cmd_map, path, model_index=model_index)
            count += 1
            if count % 20 == 0:
                print(f"[CustomModelData] {count}/{len(file_list)} fichiers traités...")
        except Exception as e:
            print(t("read_error", file=f, error=str(e)))
    print(f"[CustomModelData] Extraction terminée en {round(time.time()-start,1)}s.")
    return items

# --- Indexation des modèles Java pour lookup rapide ---
def build_model_index():
    """
    Parcourt tous les assets/*/models/ et indexe les modèles Java (clé: namespace:path, valeur: chemin absolu).
    """
    model_index = {}
    assets_root = os.path.join(JAVA_RP_DIR, 'assets')
    if not os.path.isdir(assets_root):
        return model_index
    for ns in os.listdir(assets_root):
        ns_models = os.path.join(assets_root, ns, 'models')
        if not os.path.isdir(ns_models):
            continue
        for root, _, files in os.walk(ns_models):
            for file in files:
                if file.endswith('.json'):
                    rel_path = os.path.relpath(os.path.join(root, file), ns_models)
                    key = f"{ns}:{rel_path[:-5].replace(os.sep, '/')}"  # sans .json
                    model_index[key] = os.path.join(root, file)
    return model_index

def build_targeted_model_index(model_refs):
    """
    Indexe uniquement les modèles Java référencés dans model_refs (set de clés namespace:path).
    """
    start = time.time()
    model_index = {}
    assets_root = os.path.join(JAVA_RP_DIR, 'assets')
    # Regroupe les refs par namespace pour limiter les parcours
    ns_to_paths = {}
    for ref in model_refs:
        if ':' in ref:
            ns, rel = ref.split(':', 1)
        else:
            ns, rel = 'minecraft', ref
        ns_to_paths.setdefault(ns, set()).add(rel)
    for ns, rels in ns_to_paths.items():
        ns_models = os.path.join(assets_root, ns, 'models')
        if not os.path.isdir(ns_models):
            continue
        for rel in rels:
            model_path = os.path.join(ns_models, *rel.split('/')) + '.json'
            if os.path.isfile(model_path):
                model_index[f"{ns}:{rel}"] = model_path
    print(f"[Index ciblé] {len(model_index)}/{len(model_refs)} modèles référencés indexés en {round(time.time()-start,2)}s.")
    return model_index

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


def generate_geyser_mapping_json(items, mapping_version="v2"):
    """
    Génère un mapping Geyser v1 ou v2 selon la doc officielle :
    https://geysermc.org/wiki/geyser/custom-items/
    """
    if mapping_version == "v1":
        # v1: mapping objet {format_version: 1, items: {...}}
        mappings = {
            "format_version": 1,
            "items": {}
        }
        for item in items:
            base_item = item['id'] if item['id'].startswith("minecraft:") else f"minecraft:{item['id']}"
            cmd = int(item['custom_model_data'])
            unique_name = f"{item['id']}_cmd{item['custom_model_data']}"
            # Correction: l'icon doit correspondre exactement au nom du fichier PNG dans textures/item/
            # On vérifie la présence du fichier et on corrige le nom si besoin
            icon_name = unique_name
            # Vérification stricte du fichier PNG
            png_path = os.path.join(BEDROCK_RP_DIR, "textures", "item", f"{icon_name}.png")
            if not os.path.isfile(png_path):
                # Essai fallback: enlever "minecraft:" si présent
                alt_icon_name = unique_name.replace("minecraft:", "")
                alt_png_path = os.path.join(BEDROCK_RP_DIR, "textures", "item", f"{alt_icon_name}.png")
                if os.path.isfile(alt_png_path):
                    icon_name = alt_icon_name
                else:
                    # Essai fallback: tout en minuscule
                    alt_icon_name2 = alt_icon_name.lower()
                    alt_png_path2 = os.path.join(BEDROCK_RP_DIR, "textures", "item", f"{alt_icon_name2}.png")
                    if os.path.isfile(alt_png_path2):
                        icon_name = alt_icon_name2
            # Ajoute l'entrée dans le bon tableau
            if base_item not in mappings["items"]:
                mappings["items"][base_item] = []
            mappings["items"][base_item].append({
                "name": unique_name,
                "allow_offhand": True,
                "display_name": item.get("display_name", unique_name),
                "custom_model_data": cmd,
                "icon": icon_name
            })
        # Nom du fichier correct
        output_path = os.path.join(BEDROCK_RP_DIR, "Bconverted_Geyser_Mapping.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=4)
        print("✅ Bconverted_Geyser_Mapping.json (v1) generated in resource pack")
    else:
        # v2: Mapping par item (déjà présent dans ton code)
        mappings = {
            "format_version": 2,
            "items": {}
        }
        for item in items:
            base_item = item['id'] if item['id'].startswith("minecraft:") else f"minecraft:{item['id']}"
            cmd = str(item['custom_model_data'])
            unique_name = f"{item['id']}_cmd{item['custom_model_data']}"
            if base_item not in mappings["items"]:
                mappings["items"][base_item] = []
            mappings["items"][base_item].append({
                "custom_model_data": cmd,
                "bedrock_identifier": f"custom:{unique_name}",
                "display_name": item.get("display_name", ""),
                "texture": unique_name,
                "geometry": f"geometry.{unique_name}",
                "model": f"geometry.{unique_name}"
            })
        output_path = os.path.join(BEDROCK_RP_DIR, "geyser-mapping.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=4)
        print("✅ geyser-mapping.json (v2) generated in resource pack")


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
        # Correction stricte : vérifier la présence du PNG avec tous les fallback utilisés dans le script
        tex_key = item.get("texture", "")
        icon_name = name
        png_path = os.path.join(tex_path, f"{icon_name}.png")
        if not os.path.isfile(png_path):
            alt_icon_name = icon_name.replace("minecraft:", "")
            alt_png_path = os.path.join(tex_path, f"{alt_icon_name}.png")
            if os.path.isfile(alt_png_path):
                icon_name = alt_icon_name
            else:
                alt_icon_name2 = alt_icon_name.lower()
                alt_png_path2 = os.path.join(tex_path, f"{alt_icon_name2}.png")
                if os.path.isfile(alt_png_path2):
                    icon_name = alt_icon_name2
        expected_texture = os.path.join(tex_path, f"{icon_name}.png")

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
            # Vérifie aussi que le nom de la texture dans le render_controller correspond au PNG
            tex_array = rc.get("arrays", {}).get("textures", {})
            arr_key = f"Array.textures.{name}"
            if arr_key in tex_array:
                rc_tex = tex_array[arr_key][0]
                if rc_tex != icon_name:
                    print(f"[Validation] RenderController texture array: '{rc_tex}' ne correspond pas au PNG '{icon_name}'")
                    errors += 1
        except Exception as e:
            print(f"[Validation] Erreur lecture RC {rc_file}: {e}")
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

def generate_manifest():
    if not JAVA_RP_DIR or not BEDROCK_RP_DIR:
        raise EnvironmentError("JAVA_RP_DIR and BEDROCK_RP_DIR must be set before generating manifest.")
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
    os.makedirs(BEDROCK_RP_DIR, exist_ok=True)
    with open(os.path.join(BEDROCK_RP_DIR, "manifest.json"), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=4)
    print(t("manifest_generated"))

def validate_geo_json_files(geo_dir):
    """
    Validate all .geo.json files in the given directory.
    """
    count = 0
    if not os.path.isdir(geo_dir):
        print(t("geo_validation_done", count=0))
        return
    print(t("geo_validation"))
    for file in os.listdir(geo_dir):
        if file.endswith('.geo.json'):
            path = os.path.join(geo_dir, file)
            try:
                with open(path, encoding='utf-8') as f:
                    data = json.load(f)
                # Basic validation: check for required keys
                if "minecraft:geometry" in data:
                    count += 1
            except Exception as e:
                print(f"[Geo Validation] {file}: {e}")
    print(t("geo_validation_done", count=count))


def copy_sounds():
    """
    Copies all .ogg files from all namespaces in the Java resource pack to the Bedrock pack,
    and generates a sound_definitions.json compatible with Bedrock.
    """
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
                            rel_path = os.path.relpath(os.path.join(root, file), src).replace('\\', '/').replace('\\', '/')
                            sound_id = f"{namespace}:{os.path.splitext(rel_path)[0]}"
                            dest_path = os.path.join(sounds_dst, rel_path)
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            shutil.copy2(os.path.join(root, file), dest_path)

                            # Detect if this is a stream (long music)
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

WORKERS = min(8, os.cpu_count() or 4)

def run_parallel(func, iterable, desc=None):
    """
    Exécute func sur chaque élément de iterable en parallèle (ThreadPoolExecutor).
    """
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(func, *args): args for args in iterable}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"[Thread error] {e}")
    return results

# --- PATCH: Parallélisation de la copie des textures ---
# (duplicate removed)

# --- PATCH: Parallélisation de la conversion PNG8 ---
def batch_convert_textures_to_png8(texture_files):
    def convert(src, dst):
        convert_texture_to_png8(src, dst)
    run_parallel(convert, texture_files)

# --- PATCH: Parallélisation de la génération des modèles Bedrock ---
def batch_convert_java_models_to_geo(model_jobs):
    from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
    import traceback
    import time
    failed = []
    results = []
    total = len(model_jobs)
    print(f"[Batch] Début conversion de {total} modèles...")
    start = time.time()
    # Filtrer les jobs mal formés
    filtered_jobs = []
    for job in model_jobs:
        if isinstance(job, dict):
            if not job.get('model_path') or not job.get('output_name') or not job.get('texture_key'):
                print(f"[Batch] ⚠️ Job ignoré (incomplet): {job}")
                failed.append(job)
                continue
        else:
            if not job or len(job) != 3 or not all(job):
                print(f"[Batch] ⚠️ Job ignoré (incomplet): {job}")
                failed.append(job)
                continue
        filtered_jobs.append(job)
    if not filtered_jobs:
        print("[Batch] Aucun job valide à traiter.")
        return failed
    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            future_to_job = {}
            for job in filtered_jobs:
                print(f"[Batch] Soumission du job: {job}")
                future = executor.submit(_safe_convert_java_model_to_geo, job)
                future_to_job[future] = job
            for idx, future in enumerate(as_completed(future_to_job), 1):
                job = future_to_job[future]
                try:
                    result = future.result(timeout=30)
                    if result is not None and not result.get('success', False):
                        failed.append(job)
                        print(f"[Batch] ❌ Échec: {result.get('error', 'Erreur inconnue')} (job: {job})")
                    else:
                        print(f"[Batch] ✅ Succès {idx}/{total} : {job}")
                except TimeoutError:
                    failed.append(job)
                    print(f"[Batch] ❌ Timeout (>30s) pour {job}")
                except Exception as e:
                    failed.append(job)
                    print(f"[Batch] ❌ Exception non gérée pour {job}: {e}")
                    traceback.print_exc()
    except Exception as e:
        print(f"[Batch] ❌ Exception globale dans le batch: {e}")
        traceback.print_exc()
        failed.extend(filtered_jobs)
    print(f"[Batch] Conversion terminée en {round(time.time()-start,1)}s. Succès: {total - len(failed)}/{total}, Échecs: {len(failed)}")
    if failed:
        print(f"[Batch] Modèles échoués: {failed}")
    return failed

def _safe_convert_java_model_to_geo(job):
    # job is expected to be a tuple or dict with model_path, output_name, texture_key
    import traceback
    import sys
    try:
        print(f"[Batch] [THREAD] (TOP) Thread started for job: {job}"); sys.stdout.flush()
        print(f"[Batch] [THREAD] (BEFORE VARS) job type: {type(job)}"); sys.stdout.flush()
        if isinstance(job, dict):
            print(f"[Batch] [THREAD] (DICT) job.keys: {list(job.keys())}"); sys.stdout.flush()
            print(f"[Batch] [THREAD] (DICT) about to get model_path"); sys.stdout.flush()
            model_path = job.get('model_path')
            print(f"[Batch] [THREAD] (DICT) model_path={model_path}"); sys.stdout.flush()
            print(f"[Batch] [THREAD] (DICT) about to get output_name"); sys.stdout.flush()
            output_name = job.get('output_name')
            print(f"[Batch] [THREAD] (DICT) output_name={output_name}"); sys.stdout.flush()
            print(f"[Batch] [THREAD] (DICT) about to get texture_key"); sys.stdout.flush()
            texture_key = job.get('texture_key')
            print(f"[Batch] [THREAD] (DICT) texture_key={texture_key}"); sys.stdout.flush()
        else:
            print(f"[Batch] [THREAD] (TUPLE) job len: {len(job)}"); sys.stdout.flush()
            print(f"[Batch] [THREAD] (TUPLE) about to unpack"); sys.stdout.flush()
            model_path, output_name, texture_key = job
            print(f"[Batch] [THREAD] (TUPLE) model_path={model_path}, output_name={output_name}, texture_key={texture_key}"); sys.stdout.flush()
        print(f"[Batch] [THREAD] Variables: model_path={model_path}, output_name={output_name}, texture_key={texture_key}"); sys.stdout.flush()
        if not model_path or not os.path.isfile(model_path):
            print(f"[Batch] [THREAD] ERREUR: model_path inexistant ou vide: {model_path}"); sys.stdout.flush()
            return {'success': False, 'error': f'model_path inexistant: {model_path}'}
        print(f"[Batch] [THREAD] Appel convert_java_model_to_geo({model_path}, {output_name}, {texture_key})"); sys.stdout.flush()
        convert_java_model_to_geo(model_path, output_name, texture_key)
        print(f"[Batch] [THREAD] Fin OK du job: {job}"); sys.stdout.flush()
        return {'success': True}
    except Exception as e:
        print(f"[Batch] ❌ Exception dans _safe_convert_java_model_to_geo: {e} (job: {job})"); sys.stdout.flush()
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return {'success': False, 'error': str(e)}

# --- PATCH: Utilisation dans le pipeline principal ---
# Exemple d'utilisation dans un pipeline (à adapter selon le flux principal du script)
#
# try:
#     failed = batch_convert_java_models_to_geo(model_jobs)
# except Exception as e:
#     print(f"[Global] Exception inattendue lors du batch: {e}")
#     import traceback
#     traceback.print_exc()
#     failed = model_jobs  # Considérer tout échoué
# if failed:
#     print(f"[Global] {len(failed)} modèles n'ont pas pu être convertis. Voir logs ci-dessus.")
# else:
#     print("[Global] Tous les modèles ont été convertis avec succès.")
#
# (À placer dans run_conversion ou le pipeline principal, GUI et console)

import sys
if "--lang" in sys.argv:
    idx = sys.argv.index("--lang")
    if idx + 1 < len(sys.argv):
        LANG = sys.argv[idx + 1]

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

    def generate_item_texture_json(self, items, textures_dir):
        """
        Génère item_texture.json au format attendu :
        "texture_data": {
            "gmdl_xxx": { "textures": "textures/minecraft/item/cactus/bow_1" }, ...
        }
        "gmdl_xxx" = nom du modèle (item['name'] ou item['model'] ou item['id'] selon structure)
        "textures" = chemin complet sans extension .png
        """
        texture_data = {}
        for item in items:
            # La clé doit être le nom du modèle Bedrock (ex: copper_ingot_cmd10001), sans namespace ni custom:
            # On extrait à partir de item['name'] ou item['id'] (ex: "custom:copper_ingot_cmd10001" -> "copper_ingot_cmd10001")
            raw_name = item.get('name') or item.get('id') or item.get('model')
            if not raw_name:
                continue
            # Retire le namespace ou le préfixe custom:
            if ':' in raw_name:
                model_name = raw_name.split(':', 1)[1]
            else:
                model_name = raw_name
            model_name = os.path.splitext(os.path.basename(str(model_name)))[0]

            # Recherche le chemin de la texture (ex: textures/minecraft/item/cactus/bow_1)
            tex_path = None
            if 'texture' in item:
                tex = item['texture']
                # Nettoyage du chemin :
                # 1. Si "textures/" déjà présent, on retire "minecraft/item/" et remplace les : par /
                if tex.startswith('textures/'):
                    tex_path = tex.replace('minecraft/item/', '').replace(':', '/').replace('.png','')
                # 2. Si "minecraft:" présent, on retire le préfixe et remplace : par /
                elif tex.startswith('minecraft:'):
                    tex_path = 'textures/' + tex.split(':',1)[1].replace(':', '/').replace('.png','')
                # 3. Si "namespace:..." (autre que minecraft), on remplace : par /
                elif ':' in tex:
                    tex_path = 'textures/' + tex.replace(':', '/').replace('.png','')
                else:
                    tex_path = f'textures/{tex}'.replace('.png','')
            else:
                tex_path = f'textures/{model_name}'

            abs_tex_path = os.path.join(BEDROCK_RP_DIR, *tex_path.split('/')) + '.png'
            texture_data[model_name] = {"textures": tex_path}

        item_texture = {
            "resource_pack_name": "custom_items",
            "texture_name": "atlas.items",
            "texture_data": texture_data
        }
        os.makedirs(textures_dir, exist_ok=True)
        out_path = os.path.join(textures_dir, "item_texture.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(item_texture, f, indent=2)
        if hasattr(self, 'log'):
            self.log(t("item_texture_generated") if 'item_texture_generated' in globals() else f"item_texture.json generated: {out_path}")
        else:
            print(f"item_texture.json generated: {out_path}")

        # Ajout : Génération d'un fichier terrain_texture.json vide (structure Geyser)
        terrain_texture = {
            "resource_pack_name": "geyser_custom",
            "texture_name": "atlas.terrain",
            "texture_data": {}
        }
        terrain_path = os.path.join(textures_dir, "terrain_texture.json")
        with open(terrain_path, 'w', encoding='utf-8') as f:
            json.dump(terrain_texture, f, indent=2)
        if hasattr(self, 'log'):
            self.log(f"terrain_texture.json generated: {terrain_path}")
        else:
            print(f"terrain_texture.json generated: {terrain_path}")

    def __init__(self, root):
        self.root = root
        self.root.title("PackConverter Java ➔ Bedrock")
        self.root.geometry("850x600")
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

        # --- Export format option ---
        self.export_format_var = tk.StringVar(value="folder")
        export_frame = tk.Frame(root)
        export_frame.pack(anchor="ne", padx=10, pady=(0, 0))
        self.export_label = tk.Label(export_frame, text=t("export_format"), font=("Segoe UI", 10))
        self.export_label.pack(side="left")
        self.export_zip_radio = tk.Radiobutton(export_frame, text="ZIP", variable=self.export_format_var, value="zip")
        self.export_zip_radio.pack(side="left")
        self.export_folder_radio = tk.Radiobutton(export_frame, text=t("folder"), variable=self.export_format_var, value="folder")
        self.export_folder_radio.pack(side="left")
        self.export_mcpack_radio = tk.Radiobutton(export_frame, text=t("mcpack"), variable=self.export_format_var, value="mcpack")
        self.export_mcpack_radio.pack(side="left")
        # --- End export format option ---

        # --- Geyser mapping format option ---
        self.geyser_mapping_var = tk.StringVar(value="v1")
        geyser_frame = tk.Frame(root)
        geyser_frame.pack(anchor="ne", padx=10, pady=(0, 0))
        self.geyser_label = tk.Label(geyser_frame, text=t("geyser_mapping_format"), font=("Segoe UI", 10))
        self.geyser_label.pack(side="left")
        self.geyser_v1_radio = tk.Radiobutton(geyser_frame, text=t("geyser_mapping_v1"), variable=self.geyser_mapping_var, value="v1")
        self.geyser_v1_radio.pack(side="left")
        self.geyser_v2_radio = tk.Radiobutton(geyser_frame, text=t("geyser_mapping_v2"), variable=self.geyser_mapping_var, value="v2")
        self.geyser_v2_radio.pack(side="left")
        # --- End Geyser mapping format option ---

        # --- Render Controller option ---
        self.use_custom_render_controller = tk.BooleanVar(value=False)
        rc_frame = tk.Frame(root)
        rc_frame.pack(anchor="ne", padx=10, pady=(0, 0))
        self.rc_checkbox = tk.Checkbutton(rc_frame, text="Custom Render Controller", variable=self.use_custom_render_controller)
        self.rc_checkbox.pack(side="left")
        # --- End Render Controller option ---

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
        self.convert_btn.pack(fill="x", padx=10, pady=(10, 2))

        # Info label for disabled state
        self.info_label = tk.Label(self.main_card, text="", font=("Segoe UI", 9), fg="#b22222", bg="#f4f4f4")
        self.info_label.pack(fill="x", padx=10, pady=(0, 8))

        # Logs section
        self.logs_card = tk.Frame(root, bg="#f4f4f4", bd=2, relief="groove")
        self.logs_card.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.logs_label = tk.Label(self.logs_card, text=t("logs"), font=("Segoe UI", 11, "bold"), bg="#f4f4f4")
        self.logs_label.pack(anchor="w", padx=10, pady=(8, 0))
        # Bouton pour effacer les logs
        self.clear_logs_btn = tk.Button(self.logs_card, text=t("clear_logs"), command=self.clear_logs, font=("Segoe UI", 9), bg="#e0e0e0")
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
        info_msg = ""
        if os.path.isdir(path):
            java_items_dir = os.path.normpath(os.path.join(path, 'assets', 'minecraft', 'items'))
            is_valid = os.path.isdir(java_items_dir) and any(
                f.lower().endswith(('.json', '.yml', '.yaml'))
                for f in os.listdir(java_items_dir)
            ) if os.path.isdir(java_items_dir) else False
            if not is_valid:
                info_msg = "Le dossier sélectionné ne contient pas de fichiers items valides dans 'assets/minecraft/items/'."
        elif os.path.isfile(path) and path.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(path, 'r') as z:
                    is_valid = any(
                        name.lower().startswith('assets/minecraft/items/') and
                        name.lower().endswith(('.json', '.yml', '.yaml'))
                        for name in z.namelist()
                    )
                if not is_valid:
                    info_msg = "Le fichier ZIP sélectionné ne contient pas de fichiers items valides dans 'assets/minecraft/items/'."
            except Exception:
                is_valid = False
                info_msg = "Impossible de lire le fichier ZIP sélectionné. Il est peut-être corrompu ou invalide."
        else:
            info_msg = "Veuillez sélectionner un dossier ou un fichier ZIP valide pour le Resource Pack Java."
        if is_valid:
            self.convert_btn.config(state="normal")
            self.info_label.config(text="")
        else:
            self.convert_btn.config(state="disabled")
            self.info_label.config(text=info_msg)

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
        start_time = time.time()
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

            geyser_mapping_format = self.geyser_mapping_var.get()
            # Barre de progression et étapes
            steps = [
                lambda items=None: clean_bedrock_directory(),
                lambda items=None: create_bedrock_structure(),
                lambda items=None: copy_all_item_textures(),
                lambda items=None: copy_sounds(),
                lambda items=None: copy_pack_icon(),
                lambda items=None: extract_custom_model_data(),
                lambda items=None: copy_all_item_textures(),
                lambda items: generate_custom_items_json(items),
                lambda items: generate_geyser_mapping_json(items, geyser_mapping_format),
                lambda items=None: validate_geo_json_files(os.path.join(BEDROCK_RP_DIR, "models", "entity")),
                lambda items: validate_consistency(items)
            ]
            self.set_progress(0, len(steps))
            items = []
            for i, step in enumerate(steps):
                self.log("-" * 40 + f"  {t('step') if 'step' in TRANSLATIONS[LANG] else 'step'} {i+1}/{len(steps)}  " + "-" * 40)
                # Always call step with items, and update items if step returns a non-None value
                result = step(items)
                if result is not None:
                    items = result
                self.set_progress(i + 1)
                self.progress.update_idletasks()

            # Extraction des items custom
            items = extract_custom_model_data()
            # Indexation des modèles pour accélérer la recherche
            model_index = build_model_index()
            # Conversion avancée pour chaque item (geometry, animation, attachable, PNG8, lang) EN PARALLÈLE
            model_jobs = []
            lang_dict = {}
            for item in items:
                texture_key = item['texture']
                output_name = item['name'].split(":")[-1]
                # Recherche directe dans l'index (avec ou sans namespace explicite)
                model_path = model_index.get(texture_key) or model_index.get(f"minecraft:{texture_key}")
                if model_path:
                    model_jobs.append((model_path, output_name, texture_key))
                lang_dict[hash7(item['name'])] = item['name']
            # --- PATCH: Conversion des modèles en parallèle ---
            batch_convert_java_models_to_geo(model_jobs)
            # Génération des fichiers de langue Bedrock
            write_lang_files(lang_dict, os.path.join(BEDROCK_RP_DIR, "texts"))

            # --- Création des render controllers uniquement si activé ---
            if self.use_custom_render_controller.get():
                rc_dir = os.path.join(BEDROCK_RP_DIR, "render_controllers")
                os.makedirs(rc_dir, exist_ok=True)
                # Génération des fichiers render_controller.json pour chaque item
                for item in items:
                    output_name = item['name'].split(":")[-1]
                    rc_path = os.path.join(rc_dir, f"{output_name}.render_controller.json")
                    rc_data = {
                        "format_version": "1.10.0",
                        "render_controllers": {
                            f"controller.render.{output_name}": {
                                "geometry": f"geometry.{output_name}",
                                "materials": ["material.default"],
                                "textures": [output_name]
                            }
                        }
                    }
                    with open(rc_path, 'w', encoding='utf-8') as f:
                        json.dump(rc_data, f, indent=4)

            # --- Génération des fichiers attachable pour chaque item custom ---
            attachable_dir = os.path.join(BEDROCK_RP_DIR, "attachables")
            os.makedirs(attachable_dir, exist_ok=True)
            def _generate_attachable_json_full(
                output_name, texture_key, geometry, out_dir, identifier, 
                generated=False, atlas_index=None, attachable_material="material.default", 
                path_hash=None, namespace=None, model_path=None, model_name=None
            ):
                # Détermination du namespace et du vrai nom (sans prefix)
                if ':' in output_name:
                    ns, base_name = output_name.split(':', 1)
                else:
                    ns = namespace or "custom"
                    base_name = output_name

                # La geometry et les animations utilisent toujours le nom SANS namespace
                geometry_name = base_name
                anim_prefix = f"animation.{geometry_name}"

                # Chemin texture
                def compute_tex_path(item_name, texture_key):
                    if not texture_key:
                        return f"textures/{item_name}"
                    tex = texture_key
                    if tex.startswith('textures/'):
                        tex = tex[len('textures/'):]
                        return f"textures/{tex.replace('minecraft/item/', '').replace(':', '/').replace('.png','')}"
                    elif tex.startswith('minecraft:'):
                        return 'textures/' + tex.split(':',1)[1].replace(':', '/').replace('.png','')
                    elif ':' in tex:
                        return 'textures/' + tex.replace(':', '/').replace('.png','')
                    else:
                        return f'textures/{tex}'.replace('.png','')

                tex_path = compute_tex_path(base_name, texture_key)

                # Scripts logic
                v_main = "v.main_hand = c.item_slot == 'main_hand';"
                v_off = "v.off_hand = c.item_slot == 'off_hand';"
                v_head = "v.head = c.item_slot == 'head';"

                # Déduire le matériel à partir du nom de la geometry (avant _cmd ou .)
                mat_base = geometry_name.split('_cmd')[0].split('.')[0]
                attachable = {
                    "format_version": "1.16.100",
                    "minecraft:attachable": {
                        "description": {
                            "identifier": f"{ns}:{base_name}",
                            "materials": {
                                "default": mat_base,
                                "enchanted": "entity_alphatest_glint"
                            },
                            "textures": {
                                "default": f"{tex_path.lstrip('/')}",
                                "enchanted": "textures/misc/enchanted_item_glint"
                            },
                            "geometry": {
                                "default": f"geometry.{geometry_name}"
                            },
                            "scripts": {
                                "pre_animation": [v_main, v_off, v_head],
                                "animate": [
                                    {"third_person_main_hand": "v.main_hand && !c.is_first_person"},
                                    {"third_person_off_hand": "v.off_hand && !c.is_first_person"},
                                    {"third_person_head": "v.head && !c.is_first_person"},
                                    {"first_person_main_hand": "v.main_hand && c.is_first_person"},
                                    {"first_person_off_hand": "v.off_hand && c.is_first_person"},
                                    {"first_person_head": "c.is_first_person && v.head"}
                                ]
                            },
                            "animations": {
                                "third_person_main_hand": f"{anim_prefix}.third_person_main_hand",
                                "third_person_off_hand": f"{anim_prefix}.third_person_off_hand",
                                "third_person_head": f"{anim_prefix}.head",
                                "first_person_main_hand": f"{anim_prefix}.first_person_main_hand",
                                "first_person_off_hand": f"{anim_prefix}.first_person_off_hand",
                                "first_person_head": "animation.disable"
                            },
                            "render_controllers": ["controller.render.item_default"]
                        }
                    }
                }

                out_path = os.path.join(out_dir, f"{base_name}.attachable.json")
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(attachable, f, indent=4)
                print(t("attachable_generated", out_path=out_path))
            for item in items:
                output_name = item['name'].split(":")[-1]
                texture_key = item['texture']
                geometry = output_name
                # Utilise le namespace correct pour l'identifier
                if ':' in item['name']:
                    ns, _ = item['name'].split(':', 1)
                    identifier = f"{ns}:{output_name}"
                    namespace = ns
                else:
                    identifier = f"custom:{output_name}"
                    namespace = 'custom'
                # Gather extra info for attachable
                generated = item.get('generated', False)
                atlas_index = item.get('atlas_index')
                attachable_material = item.get('attachable_material', 'material.default')
                path_hash = hash7(output_name)
                model_path = os.path.dirname(texture_key.split(':', 1)[1]) if ':' in texture_key else ''
                model_name = os.path.basename(texture_key.split(':', 1)[1]) if ':' in texture_key else texture_key
                _generate_attachable_json_full(
                    output_name, texture_key, geometry, attachable_dir, identifier,
                    generated=generated, atlas_index=atlas_index, attachable_material=attachable_material,
                    path_hash=path_hash, namespace=namespace, model_path=model_path, model_name=model_name
                )

            # Génération du fichier item_texture.json dans textures/
            self.generate_item_texture_json(items, os.path.join(BEDROCK_RP_DIR, "textures"))

            # Affiche le temps de conversion AVANT l'étape d'export utilisateur
            elapsed = time.time() - start_time
            self.log(f"Conversion terminée en {elapsed:.2f} secondes (hors export).")

            # --- SUPPRESSION DU DOSSIER render_controllers SI NON UTILISÉ ---
            if not self.use_custom_render_controller.get():
                rc_dir = os.path.join(BEDROCK_RP_DIR, "render_controllers")
                if os.path.isdir(rc_dir):
                    try:
                        shutil.rmtree(rc_dir)
                        self.log("Dossier render_controllers supprimé (option décochée).")
                    except Exception as e:
                        self.log(f"Erreur lors de la suppression de render_controllers: {e}")

            # Sélection du dossier de sortie par l'utilisateur
            output_dir = filedialog.askdirectory(title="Sélectionnez le dossier de sortie")
            if not output_dir:
                self.log(t("export_cancelled"))
                self.set_progress(0)
                self.convert_btn.config(state="normal")
                return

            # --- Détermination du nom du fichier exporté ---
            java_input_path = self.java_dir.get()
            if java_input_path.lower().endswith('.zip'):
                base_name = os.path.splitext(os.path.basename(java_input_path))[0]
            else:
                base_name = os.path.basename(JAVA_RP_DIR.strip().rstrip("/\\"))
            export_name = f"{base_name}[BConverted]"
            # --- Fin nom fichier ---

            # --- Ajout : écrire les logs dans un fichier temporaire ---
            logs_path = os.path.join(output_dir, "conversion_logs.txt")
            with open(logs_path, "w", encoding="utf-8") as f:
                f.write(self.last_logs)
            # --- Fin ajout logs ---
            # --- Ajout : déplacer le geyser-mapping.json à côté du pack exporté ---
            geyser_mapping_src = os.path.join(BEDROCK_RP_DIR, "geyser-mapping.json")
            geyser_mapping_dst = os.path.join(output_dir, f"{export_name}_geyser-mapping.json")
            if os.path.exists(geyser_mapping_src):
                shutil.copy2(geyser_mapping_src, geyser_mapping_dst)
            # --- Fin ajout déplacement geyser-mapping.json ---

            export_format = self.export_format_var.get()
            if export_format == "zip":
                zip_path = os.path.join(output_dir, f"{export_name}.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for rootdir, dirs, files in os.walk(BEDROCK_RP_DIR):
                        for file in files:
                            file_path = os.path.join(rootdir, file)
                            arcname = os.path.relpath(file_path, BEDROCK_RP_DIR)
                            zipf.write(file_path, arcname)
                self.log(t("pack_exported_zip", zip_path=zip_path))
                messagebox.showinfo(t("success"), f"Pack exporté dans :\n{zip_path}")
            elif export_format == "mcpack":
                mcpack_path = os.path.join(output_dir, f"{export_name}.mcpack")
                # Utilise la fonction create_mcpack déjà définie
                create_mcpack(BEDROCK_RP_DIR, output_dir, export_name)
                self.log(f"✅ Pack exporté dans : {mcpack_path}")
                messagebox.showinfo(t("success"), f"Pack exporté dans :\n{mcpack_path}")
            elif export_format == "folder":
                dest_folder = os.path.join(output_dir, export_name)
                if os.path.exists(dest_folder):
                    shutil.rmtree(dest_folder)

                shutil.copytree(BEDROCK_RP_DIR, dest_folder)
                self.log(t("pack_exported_folder", out_dir=dest_folder))
                messagebox.showinfo(t("success"), t("pack_exported_folder_msg", out_dir=dest_folder))
            else:
                self.log(t("unknown_export_format"))
                messagebox.showerror(t("error_title"), t("unknown_export_format"))

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
        self.clear_logs_btn.config(text=t("clear_logs"))
        self.export_label.config(text=t("export_format"))
        self.export_folder_radio.config(text=t("folder"))
        self.export_mcpack_radio.config(text=t("mcpack"))
        self.geyser_label.config(text=t("geyser_mapping_format"))
        self.geyser_v1_radio.config(text=t("geyser_mapping_v1"))
        self.geyser_v2_radio.config(text=t("geyser_mapping_v2"))
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


# --- Point d'entrée conversion (exemple) ---
if __name__ == "__main__":
    try:
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "--nogui":
            # Mode console classique
            print(t("start_console"))
            clean_bedrock_directory()
            create_bedrock_structure()
            copy_all_item_textures()
            copy_pack_icon()
            t0 = time.time()
            items = extract_custom_model_data()
            t1 = time.time()
            print(f"[Profiling] Extraction des items : {round(t1-t0,2)}s")
            copy_all_item_textures()
            generate_custom_items_json(items)
            generate_geyser_mapping_json(items)
            validate_geo_json_files(os.path.join(BEDROCK_RP_DIR, "models", "entity"))
            validate_consistency(items)

            # --- Conversion avancée des modèles en parallèle ---
            # 1. Collecte des références de modèles
            t2 = time.time()
            model_refs = set()
            for item in items:
                tex = item['texture']
                if ':' in tex:
                    model_refs.add(tex)
                else:
                    model_refs.add(f"minecraft:{tex}")
            print(f"[Profiling] Références de modèles collectées : {len(model_refs)}")
            # 2. Indexation ciblée
            model_index = build_targeted_model_index(model_refs)
            t3 = time.time()
            # 3. Préparation des jobs
            model_jobs = []
            for item in items:
                texture_key = item['texture']
                output_name = item['name'].split(":")[-1]
                model_path = model_index.get(texture_key) or model_index.get(f"minecraft:{texture_key}")
                if model_path:
                    model_jobs.append((model_path, output_name, texture_key))
            t4 = time.time()
            print(f"[Profiling] Préparation des jobs : {round(t4-t3,2)}s")
            # 4. Conversion
            batch_convert_java_models_to_geo(model_jobs)
            t5 = time.time()
            print(f"[Profiling] Conversion des modèles : {round(t5-t4,2)}s")
            # --- Génération des fichiers de langue Bedrock ---
            lang_dict = {hash7(item['name']): item['name'] for item in items}
            write_lang_files(lang_dict, os.path.join(BEDROCK_RP_DIR, "texts"))


            # Ajout : demande du dossier de sortie et création du zip
            output_dir = input("Dossier de sortie pour le ZIP : ").strip()
            if output_dir:
                converted_name = os.path.basename(JAVA_RP_DIR.strip().rstrip("/\\"))
                zip_path = os.path.join(output_dir, f"{converted_name}.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for rootdir, dirs, files in os.walk(BEDROCK_RP_DIR):
                        for file in files:
                            file_path = os.path.join(rootdir, file)
                            arcname = os.path.relpath(file_path, BEDROCK_RP_DIR)
                            zipf.write(file_path, arcname)
                print(t("pack_exported_zip", zip_path=zip_path))
            else:
                print(t("export_cancelled"))
            print(t("console_done"))
        else:
            # Mode GUI
            root = tk.Tk()
            app = PackConverterGUI(root)
            root.mainloop()
            sys.exit(0)
    except Exception as e:
        print(t("error", e=str(e)))
