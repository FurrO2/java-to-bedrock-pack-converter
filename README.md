# 🛠️ Java ➜ Bedrock Resource Pack Converter

Hello, I'm FurrO2, i'm new here and don't really know how to use Github well, sorry in advance !  I don't have much talent in the development field, but I've been trying to create a Java resource pack converter to Bedrock for the game, capable of supporting versions higher than 1.21.4. My mission is to offer a simple tool that allows anyone to easily convert a Java resource pack in just a few clicks, making it compatible with Geyser.

Thank you.


This script automates the conversion of a Minecraft Java Edition resource pack to Bedrock Edition, especially handling **Custom Model Data** (`custom_model_data`) items.

---


## ❗⛔FOR NOW, THE MODEL CONVERTER ISN'T WORKING WELL, so this need to be fixed⛔❗


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

##🧪 Usage

Run the script:`
PackConverter_JavaToBedrock.py
`


Place your Java resource pack folder into the GUI/Panem directory. (Do not use a zip file.)

Click the Start Conversion button.

A .zip file will be generated containing your pack and the Geyser mappings.

You're done! Review the contents, then rename the .zip file to use the .mcpack extension.
