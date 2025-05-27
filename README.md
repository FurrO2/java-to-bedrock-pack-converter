# 🛠️ Java ➜ Bedrock Resource Pack Converter

This script automates the conversion of a Minecraft Java Edition resource pack to Bedrock Edition, especially handling **Custom Model Data** (`custom_model_data`) items.

---


## ❗⛔ FOR NOW, THE MODEL CONVERTER ISN'T WORKING WELL, so this need to be fixed ⛔❗


## 📦 Features

- 🔁 Automatically converts Java JSON models to Bedrock-compatible geometries (`.geo.json`)
- 🖼️ Copies item textures
- 🧱 Generates custom items based on `custom_model_data`
- 📁 Creates a ready-to-use Bedrock Edition folder structure
- 🧩 Supports both `elements` and `groups` in models
- ✅ Compatible with **Geyser** for cross-platform servers

---

## 🚀 Requirements

- Python 3.7 or higher  
- Python module: `pyyaml`

Install with:

`
pip install pyyaml
`
 📁 Java Pack Structure Required
The script expects your Java resource pack to be structured like:
`
java/
assets/
minecraft/
models/
`
📁 Output Bedrock Structure
It will generate:
`
bedrock/
textures/
models/
entity/
render_controllers/
`
⚙️ Configuration

# Windows example

set `JAVA_RP_DIR=C:\path\to\your\java\pack`

set `BEDROCK_RP_DIR=C:\path\to\output\bedrock\pack
`

Or modify the script directly:

JAVA_RP_DIR = `r"C:\path\to\your\java\pack"`
BEDROCK_RP_DIR = `r"C:\path\to\output\bedrock\pack"`

🧪 Usage
Place your Java resource pack in the defined JAVA_RP_DIR

Run the script:`
python convertisseur.py
`
The Bedrock-compatible pack will be created in BEDROCK_RP_DIR
