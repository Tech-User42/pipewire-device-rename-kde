#!/usr/bin/env python3
import subprocess
import sys
import json
from os import environ as env
from os import system as run_system_command

def get_pactl_output(command):
    """Exécute une commande pactl et retourne sa sortie."""
    try:
        return subprocess.check_output(command, shell=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de la commande : {e}")
        sys.exit(1)

def parse_sinks(raw_output):
    """Parse la sortie de 'pactl list sinks' pour extraire les informations des 'sinks'."""
    return parse_devices(raw_output, "Destination")

def parse_sources(raw_output):
    """Parse la sortie de 'pactl list sources' pour extraire les informations des 'sources'."""
    return parse_devices(raw_output, "Source #")

def parse_devices(raw_output, device_type):
    """Parse les dispositifs audio (sinks ou sources) à partir de la sortie de pactl."""
    devices = []
    current_device = {}

    for line in raw_output.splitlines():
        line = line.strip()
        
        # Identifier un nouveau dispositif audio (sink/source)
        if device_type in line:
            if current_device:
                devices.append(current_device)
            current_device = {}

        # Extraire les informations du dispositif
        if "Nom" in line:
            current_device["name"] = line.split(":", 1)[1].strip()
            current_device["type"] = ("input" if line.split(":", 1)[1].strip().replace('"','').startswith("alsa_input") else "output")
        elif "Description" in line:
            current_device["description"] = line.split(":", 1)[1].strip()

    if current_device:
        devices.append(current_device)

    return devices

# Fonction pour afficher les dispositifs audio (sinks ou sources)
def display_devices(devices, type, label=""):
    """Affiche la liste des dispositifs audio avec leurs détails."""
    print(f"=== Liste des {label} audio ===")
    for i, device in enumerate(devices):
        if(device.get("type") == type):
            print(f"[{i}] Nom : {device.get('name')}")
            print(f"     Description : {device.get('description')}")
            print(f"     Type : {device.get('type')}")
            print("")
    print(f"===============================")
# Fonction pour générer le fichier JSON avec les règles de PipeWire
def generate_rules_json(sinks, sources):
    """Génère les règles pour PipeWire en fonction des dispositifs audio."""
    device_rules = []
    node_rules = []

    # Fonction interne pour ajouter les règles d'un dispositif (sink/source)
    def append_rules(device_list):
        for device in device_list:
            device_name = device.get("name")
            description = device.get("description")
            device_type = device.get("type")

            node_rules.append({
                    "matches": [{"node.name": device_name}],
                    "actions": {
                        "update-props": {
                            "node.description": description,
                            "node.nick": description,
                            "node.product.name": description
                        }
                    }
                })
                

    append_rules(sinks)
    append_rules(sources)

    path = f"{env['HOME']}/.config/pipewire/pipewire.conf.d/custom.conf"
    with open(path, "w") as f:
        f.write("device.rules = ")
        json.dump(device_rules, f, indent=4, ensure_ascii=False)
        f.write("\n\n")
        f.write("node.rules = ")
        json.dump(node_rules, f, indent=4, ensure_ascii=False)
        f.write("\n")

    print(f"📄 Fichier PipeWire '{path}' généré avec succès.")

def ask_and_rename(devices, label="sink/source"):
    """Demande à l'utilisateur de sélectionner un dispositif et de le renommer."""
    try:
        choice = int(input(f"Sélectionne l'index du {label} à renommer : "))
        selected = devices[choice]
    except (ValueError, IndexError):
        print("⛔ Index invalide.")
        return

    new_nick = input("Entre le nouveau nom ou rien pour passer : ").strip()
    selected["description"] = new_nick


def main():
    """Point d'entrée principal du script."""
    sinks = parse_sinks(get_pactl_output("pactl list sinks"))
    sources = parse_sources(get_pactl_output("pactl list sources"))
    if not sinks and not sources:
        print("⛔ Aucun dispositif audio trouvé.")
        sys.exit(1)
    choice = input("Sélectionnez un type de périphérique audio (entrée/sortie)\n[1] Sorties (sinks)\n[2] Entrées (sources)\n[CTRL + C] Sortir\nChoix : ")
    
    if choice == "1":
        display_devices(sinks, "output", "sorties (sinks)")
        ask_and_rename(sinks, "sink")
    if choice == "2":
        display_devices(sources, "input", "entrées (sources)")
        ask_and_rename(sources, "source")

    generate_rules_json(sinks, sources)
    run_system_command("systemctl --user restart pipewire pipewire-pulse")
    print("🔄 PipeWire a été redémarré avec succès.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⛔ Sortie du programme.")
