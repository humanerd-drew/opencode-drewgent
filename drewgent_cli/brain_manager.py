"""NeuronFS Brain Governance — filesystem-based AI constraint engine.

This module implements brain management for Drewgent Agent, treating the
filesystem as a constraint engine where folder structure and special tokens
force AI behavior via the vorq (value-or-lookup) harness.

Brain Structure (7-Layer Subsumption):
    ~/.drewgent/brain/<name>/
    ├── P0-brainstem/     # CRITICAL: survival, safety, never-do rules
    ├── P1-limbic/        # EMOTIONAL: values, tone, style constraints
    ├── P2-hippocampus/   # MEMORY: context boundaries, recall patterns
    ├── P3-sensors/       # INPUT: tool routing, platform hints
    ├── P4-cortex/        # LEARNING: patterns, skills, workflows
    ├── P5-ego/           # SELF: identity, personality, voice
    └── P6-prefrontal/    # PLANNING: high-level strategy, reasoning

Key Concepts:
    - vorq harness: Unique tokens that force AI to look up meaning
    - 禁 (禁) micro-opcode: 1-char Chinese = NEVER_DO directive
    - bomb.neuron: Kill switch that disables a path
    - Neuron firing: Incrementing weights to strengthen patterns
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

BRAIN_DIR_NAME = "brain"
BRAIN_LAYERS = [
    "P0-brainstem",
    "P1-limbic",
    "P2-hippocampus",
    "P3-sensors",
    "P4-cortex",
    "P5-ego",
    "P6-prefrontal",
]
BRAIN_LAYER_DESCRIPTIONS = {
    "P0-brainstem": "CRITICAL: survival, safety, never-do rules",
    "P1-limbic": "EMOTIONAL: values, tone, style constraints",
    "P2-hippocampus": "MEMORY: context boundaries, recall patterns",
    "P3-sensors": "INPUT: tool routing, platform hints",
    "P4-cortex": "LEARNING: patterns, skills, workflows",
    "P5-ego": "SELF: identity, personality, voice",
    "P6-prefrontal": "PLANNING: high-level strategy, reasoning",
}
NEURON_EXTENSIONS = (".neuron", ".rule", ".md")
FORBIDDEN_DIR_NAME = "禁"
BOMB_FILE = "bomb.neuron"
WEIGHT_FILE = ".weight"
ACTIVE_BRAIN_FILE = "active_brain.txt"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class NeuronInfo:
    """Information about a single neuron (rule/pattern file)."""
    path: Path
    layer: str
    name: str
    weight: int = 1
    is_bombed: bool = False
    content: str = ""


@dataclass
class BrainLayer:
    """A single layer in the brain hierarchy."""
    name: str
    description: str
    path: Path
    neurons: list[NeuronInfo] = field(default_factory=list)
    sublayers: list["BrainLayer"] = field(default_factory=list)
    bombed_count: int = 0


@dataclass
class Brain:
    """A complete brain with all layers."""
    name: str
    path: Path
    layers: list[BrainLayer] = field(default_factory=list)
    total_neurons: int = 0
    bombed_count: int = 0

    def load(self) -> "Brain":
        """Load brain content from disk (idempotent - already in-memory after scan)."""
        # Brain is already populated by scan_brain() which calls _scan_layer recursively.
        # This method exists for API compatibility with code that expects a load() method.
        return self


# =============================================================================
# Path Helpers
# =============================================================================

def get_brain_home() -> Path:
    """Get the brain home directory."""
    from drewgent_constants import get_drewgent_home
    return get_drewgent_home() / BRAIN_DIR_NAME


def get_active_brain_name() -> Optional[str]:
    """Get the name of the currently active brain."""
    brain_home = get_brain_home()
    active_file = brain_home / ACTIVE_BRAIN_FILE
    if active_file.exists():
        try:
            return active_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return None


def set_active_brain(name: str) -> None:
    """Set the active brain name."""
    brain_home = get_brain_home()
    brain_home.mkdir(parents=True, exist_ok=True)
    active_file = brain_home / ACTIVE_BRAIN_FILE
    active_file.write_text(name, encoding="utf-8")


def get_brain_path(name: str) -> Path:
    """Get the path for a specific brain."""
    return get_brain_home() / name


# =============================================================================
# Brain Initialization
# =============================================================================

def init_brain(name: str) -> tuple[bool, str]:
    """Initialize a new brain with the 7-layer structure.
    
    Returns (success, message).
    """
    if not name or not name.strip():
        return False, "Brain name cannot be empty"
    
    name = name.strip().lower().replace(" ", "-")
    if not name.replace("-", "").replace("_", "").isalnum():
        return False, "Brain name must contain only letters, numbers, hyphens, and underscores"
    
    brain_path = get_brain_path(name)
    if brain_path.exists():
        return False, f"Brain '{name}' already exists at {brain_path}"
    
    try:
        # Create layer directories
        for layer_name in BRAIN_LAYERS:
            layer_path = brain_path / layer_name
            layer_path.mkdir(parents=True, exist_ok=True)
            
            # Add forbidden subdirectory in P0-brainstem
            if layer_name == "P0-brainstem":
                forb_path = layer_path / FORBIDDEN_DIR_NAME
                forb_path.mkdir(parents=True, exist_ok=True)
        
        # Create README for the brain
        readme_content = f"""# Brain: {name}

This brain follows the NeuronFS 7-layer subsumption architecture.

## Layers

"""
        for layer in BRAIN_LAYERS:
            desc = BRAIN_LAYER_DESCRIPTIONS.get(layer, "")
            readme_content += f"- **{layer}**: {desc}\n"
        
        readme_content += f"""
## Usage

- `/brain fire <path>` — Increment neuron weight
- `/brain bomb <path>` — Kill a neuron path
- `/brain emit` — Export brain to system prompt
- `/brain diag` — Visualize brain structure

## Creating Rules

Place `.neuron` files in any layer. Use the `禁` prefix for forbidden patterns:

```
禁console_log
FORBIDDEN: console.log statements
REPLACEMENT: Use proper logging libraries
```
"""
        readme_path = brain_path / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")
        
        return True, f"Initialized brain '{name}' at {brain_path}"
    
    except Exception as e:
        logger.error("Failed to initialize brain '%s': %s", name, e)
        return False, f"Failed to initialize brain: {e}"


# =============================================================================
# Brain Scanning
# =============================================================================

def _scan_neuron(neuron_path: Path, layer: str) -> Optional[NeuronInfo]:
    """Scan a single neuron file and return its info."""
    if neuron_path.suffix not in NEURON_EXTENSIONS:
        return None
    if neuron_path.name == BOMB_FILE:
        return None  # Don't count bomb files as neurons
    
    try:
        weight = 1
        weight_file = neuron_path.parent / WEIGHT_FILE
        if weight_file.exists():
            try:
                weight = int(weight_file.read_text(encoding="utf-8").strip())
            except ValueError:
                weight = 1
        
        content = ""
        try:
            content = neuron_path.read_text(encoding="utf-8")
        except Exception:
            pass
        
        return NeuronInfo(
            path=neuron_path,
            layer=layer,
            name=neuron_path.stem,
            weight=weight,
            is_bombed=False,
            content=content,
        )
    except Exception as e:
        logger.debug("Failed to scan neuron %s: %s", neuron_path, e)
        return None


def _scan_layer(layer_path: Path, layer_name: str) -> BrainLayer:
    """Scan a brain layer directory."""
    layer = BrainLayer(
        name=layer_name,
        description=BRAIN_LAYER_DESCRIPTIONS.get(layer_name, ""),
        path=layer_path,
    )
    
    if not layer_path.exists():
        return layer
    
    # Scan neurons directly in this layer
    for item in layer_path.iterdir():
        if item.is_file() and item.suffix in NEURON_EXTENSIONS:
            neuron = _scan_neuron(item, layer_name)
            if neuron:
                layer.neurons.append(neuron)
        
        elif item.is_dir():
            # Scan subdirectories recursively
            sublayer = _scan_layer(item, f"{layer_name}/{item.name}")
            if sublayer.neurons:
                layer.sublayers.append(sublayer)
            
            # Check for bomb file
            if (item / BOMB_FILE).exists():
                layer.bombed_count += 1
    
    return layer


def scan_brain(name: str) -> Optional[Brain]:
    """Scan a brain and return its structure."""
    brain_path = get_brain_path(name)
    if not brain_path.exists():
        return None
    
    brain = Brain(name=name, path=brain_path)
    
    for layer_name in BRAIN_LAYERS:
        layer_path = brain_path / layer_name
        if not layer_path.exists():
            continue
        
        # Check if entire layer is bombed
        if (layer_path / BOMB_FILE).exists():
            brain.bombed_count += 1
            continue
        
        layer = _scan_layer(layer_path, layer_name)
        brain.layers.append(layer)
        brain.total_neurons += len(layer.neurons)
        
        # Count sublayer neurons
        for sublayer in layer.sublayers:
            brain.total_neurons += len(sublayer.neurons)
    
    return brain


def list_brains() -> list[dict]:
    """List all available brains with their stats."""
    brain_home = get_brain_home()
    brains = []
    active_name = get_active_brain_name()
    
    if not brain_home.exists():
        return brains
    
    for item in brain_home.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            brain = scan_brain(item.name)
            if brain:
                brains.append({
                    "name": brain.name,
                    "path": str(brain.path),
                    "is_active": brain.name == active_name,
                    "total_neurons": brain.total_neurons,
                    "bombed_layers": brain.bombed_count,
                })
    
    return sorted(brains, key=lambda x: (not x["is_active"], x["name"]))


# =============================================================================
# Brain Operations
# =============================================================================

def fire_neuron(path: str) -> tuple[bool, str]:
    """Increment the weight of a neuron.
    
    Args:
        path: Relative path to the neuron (e.g., "P0-brainstem/禁console_log")
    
    Returns:
        (success, message)
    """
    active_name = get_active_brain_name()
    if not active_name:
        return False, "No active brain. Use /brain activate <name> first."
    
    brain_path = get_brain_path(active_name)
    neuron_path = brain_path / path
    
    # Handle both file and directory paths
    if neuron_path.is_dir():
        neuron_path = neuron_path / WEIGHT_FILE
    elif not neuron_path.suffix:
        # Try .neuron extension
        neuron_path = neuron_path.with_suffix(".neuron")
    
    # Ensure parent exists
    neuron_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Increment weight
    current_weight = 0
    if neuron_path.exists():
        try:
            current_weight = int(neuron_path.read_text(encoding="utf-8").strip())
        except ValueError:
            current_weight = 1
    
    new_weight = current_weight + 1
    neuron_path.write_text(str(new_weight), encoding="utf-8")
    
    return True, f"Neuron fired: weight increased to {new_weight}"


def bomb_neuron(path: str) -> tuple[bool, str]:
    """Create a bomb at a neuron path (kill switch).
    
    Args:
        path: Relative path to the neuron to bomb
    
    Returns:
        (success, message)
    """
    active_name = get_active_brain_name()
    if not active_name:
        return False, "No active brain. Use /brain activate <name> first."
    
    brain_path = get_brain_path(active_name)
    target_path = brain_path / path
    
    # If targeting a file, put bomb in its parent
    if target_path.is_file():
        target_path = target_path.parent
    
    bomb_path = target_path / BOMB_FILE
    bomb_path.parent.mkdir(parents=True, exist_ok=True)
    bomb_path.write_text("BOMBED\n", encoding="utf-8")
    
    return True, f"Neuron bombed: {path} is now disabled"


def unbomb_neuron(path: str) -> tuple[bool, str]:
    """Remove a bomb from a neuron path.
    
    Args:
        path: Relative path to the neuron to unbomb
    
    Returns:
        (success, message)
    """
    active_name = get_active_brain_name()
    if not active_name:
        return False, "No active brain. Use /brain activate <name> first."
    
    brain_path = get_brain_path(active_name)
    target_path = brain_path / path
    
    if target_path.is_file():
        target_path = target_path.parent
    
    bomb_path = target_path / BOMB_FILE
    if bomb_path.exists():
        bomb_path.unlink()
        return True, f"Neuron unbombed: {path} is now active"
    
    return False, f"No bomb found at {path}"


# =============================================================================
# Brain Emission
# =============================================================================

def get_layer_content(layer_path: Path, layer_name: str) -> str:
    """Read full content of all neuron files in a layer directory.
    
    Args:
        layer_path: Path to the layer directory
        layer_name: Name of the layer (e.g., "P0-brainstem")
    
    Returns:
        Full content of all .neuron, .rule, and .md files in the layer
    """
    if not layer_path.exists():
        return ""
    
    content_parts = []
    
    # Scan for all neuron files in this layer directory (not subdirectories)
    for item in layer_path.iterdir():
        if item.is_file() and item.suffix in NEURON_EXTENSIONS:
            if item.name == BOMB_FILE:
                continue
            try:
                file_content = item.read_text(encoding="utf-8")
                if file_content.strip():
                    content_parts.append(f"\n--- {item.name} ---\n{file_content}")
            except Exception:
                pass
        elif item.is_dir():
            # Also scan files in subdirectories (like 禁 subdirectory in P0)
            for sub_item in item.iterdir():
                if sub_item.is_file() and sub_item.suffix in NEURON_EXTENSIONS:
                    if sub_item.name == BOMB_FILE:
                        continue
                    try:
                        file_content = sub_item.read_text(encoding="utf-8")
                        if file_content.strip():
                            content_parts.append(f"\n--- {sub_item.name} ---\n{file_content}")
                    except Exception:
                        pass
    
    return "".join(content_parts)


def emit_layer_content(layer_path: Path, layer_name: str, depth: int = 0) -> list[str]:
    """Emit full content for a layer as governance text.
    
    Args:
        layer_path: Path to the layer directory
        layer_name: Name of the layer (e.g., "P0-brainstem")
        depth: Indentation depth for nested output
    
    Returns:
        List of formatted lines for the layer
    """
    result = []
    indent = "  " * depth
    
    description = BRAIN_LAYER_DESCRIPTIONS.get(layer_name, "")
    
    result.append(f"{indent}### {layer_name}")
    if description:
        result.append(f"{indent}*{description}*")
    result.append("")
    
    # Get full content from all neuron files
    full_content = get_layer_content(layer_path, layer_name)
    
    if full_content:
        # Split and add with proper indentation
        for line in full_content.splitlines():
            result.append(f"{indent}{line}")
        result.append("")
    else:
        result.append(f"{indent}[No neurons loaded for this layer]")
        result.append("")
    
    return result


def emit_brain(name: Optional[str] = None) -> tuple[bool, str]:
    """Emit the brain content as governance text.
    
    Args:
        name: Brain name (uses active brain if not specified)
    
    Returns:
        (success, content_or_error_message)
    """
    if name:
        brain = scan_brain(name)
    else:
        active_name = get_active_brain_name()
        if not active_name:
            return False, "No active brain. Use /brain activate <name> first."
        brain = scan_brain(active_name)
    
    if not brain:
        return False, f"Brain '{name or active_name}' not found"
    
    lines = [
        "# Brain Governance",
        f"## Brain: {brain.name}",
        "",
        "This brain implements NeuronFS-style governance. Follow the rules",
        "in order from P0 (highest priority) to P6 (lowest priority).",
        "",
    ]
    
    # Iterate through ALL 7 layers (not just brain.layers which only has scanned layers)
    for layer_name in BRAIN_LAYERS:
        layer_path = brain.path / layer_name
        
        # Skip if bombed
        if layer_path.exists() and (layer_path / BOMB_FILE).exists():
            continue
        
        # Always show the layer header with description
        description = BRAIN_LAYER_DESCRIPTIONS.get(layer_name, "")
        lines.append(f"### {layer_name}")
        if description:
            lines.append(f"*{description}*")
        lines.append("")
        
        # Get all neurons in this layer (full content, not truncated)
        if layer_path.exists():
            # Get full content from all neuron files
            full_content = get_layer_content(layer_path, layer_name)
            
            if full_content:
                # For P0, keep the FORBIDDEN token prefix visible
                # For other layers, just show the content
                for line in full_content.splitlines():
                    lines.append(line)
                lines.append("")
            else:
                lines.append("[No neurons loaded for this layer]")
                lines.append("")
        else:
            lines.append("[Layer directory does not exist yet]")
            lines.append("")
    
    lines.extend([
        "",
        "## Subsumption Notes",
        "- P0 (brainstem) rules OVERRIDE all other layers",
        "- Earlier layers take precedence over later layers",
        "- Bombed paths are completely disabled",
        "- Use /brain fire <path> to strengthen frequently-used patterns",
    ])
    
    return True, "\n".join(lines)


def load_brain_for_prompt(name: Optional[str] = None) -> str:
    """Load brain content for injection into the system prompt.
    
    This is the main entry point for prompt_builder.py integration.
    """
    success, content = emit_brain(name)
    if success:
        return content
    logger.debug("Failed to load brain for prompt: %s", content)
    return ""


# =============================================================================
# Brain Visualization
# =============================================================================

def diag_brain(name: Optional[str] = None) -> tuple[bool, str]:
    """Generate a visual tree diagram of the brain.
    
    Args:
        name: Brain name (uses active brain if not specified)
    
    Returns:
        (success, diagram_or_error_message)
    """
    if name:
        brain = scan_brain(name)
    else:
        active_name = get_active_brain_name()
        if not active_name:
            return False, "No active brain. Use /brain activate <name> first."
        brain = scan_brain(active_name)
    
    if not brain:
        return False, f"Brain '{name or active_name}' not found"
    
    lines = [
        f"🧠 Brain: {brain.name}",
        f"📍 Path: {brain.path}",
        f"📊 Total neurons: {brain.total_neurons}",
        f"💣 Bombed layers: {brain.bombed_count}",
        "",
    ]
    
    if brain.name == get_active_brain_name():
        lines.append("✅ ACTIVE")
    else:
        lines.append("○ INACTIVE")
    lines.append("")
    
    def format_tree(layer: BrainLayer, prefix: str = "", is_last: bool = True) -> list[str]:
        result = []
        
        # Check if layer is bombed
        is_bombed = (layer.path / BOMB_FILE).exists()
        bomb_marker = " 💣" if is_bombed else ""
        
        # Layer header
        connector = "└── " if is_last else "├── "
        result.append(f"{prefix}{connector}📁 {layer.name}{bomb_marker}")
        
        # Add description
        if layer.description:
            desc_prefix = prefix + ("    " if is_last else "│   ")
            result.append(f"{desc_prefix}   {layer.description}")
        
        # Add neurons
        neuron_prefix = prefix + ("    " if is_last else "│   ")
        for i, neuron in enumerate(layer.neurons):
            is_last_neuron = (i == len(layer.neurons) - 1) and not layer.sublayers
            neuron_connector = "└── " if is_last_neuron else "├── "
            weight_marker = f" (×{neuron.weight})" if neuron.weight > 1 else ""
            result.append(f"{neuron_prefix}{neuron_connector}⚡ {neuron.name}{weight_marker}")
        
        # Add sublayers recursively
        sublayer_prefix = prefix + ("    " if is_last else "│   ")
        for i, sublayer in enumerate(layer.sublayers):
            is_last_sublayer = (i == len(layer.sublayers) - 1)
            result.extend(format_tree(sublayer, sublayer_prefix, is_last_sublayer))
        
        return result
    
    lines.append("📂 Structure:")
    lines.append("")
    
    for i, layer in enumerate(brain.layers):
        is_last = (i == len(brain.layers) - 1)
        lines.extend(format_tree(layer, "", is_last))
    
    lines.extend([
        "",
        "Legend: 📁 folder  ⚡ neuron  💣 bombed",
        f"Use /brain activate {brain.name} to make this the active brain",
    ])
    
    return True, "\n".join(lines)


# =============================================================================
# Brain Activation
# =============================================================================

def activate_brain(name: str) -> tuple[bool, str]:
    """Activate a brain for use in the system prompt.
    
    Args:
        name: Brain name to activate
    
    Returns:
        (success, message)
    """
    brain_path = get_brain_path(name)
    if not brain_path.exists():
        return False, f"Brain '{name}' not found at {brain_path}"
    
    set_active_brain(name)
    return True, f"Activated brain '{name}'"


# =============================================================================
# CLI Integration Helpers
# =============================================================================

def handle_brain_command(args: list[str]) -> tuple[bool, str]:
    """Handle /brain command arguments.
    
    Args:
        args: Command arguments (e.g., ["init", "mybrain"])
    
    Returns:
        (success, output_message)
    """
    if not args:
        # Show brain status
        active = get_active_brain_name()
        brains = list_brains()
        
        if not brains:
            return True, """No brains found. Create one with:

/brain init <name>

Example: /brain init myproject"""

        lines = ["🧠 Available Brains:", ""]
        for brain in brains:
            active_marker = " ✅ ACTIVE" if brain["is_active"] else ""
            lines.append(f"- {brain['name']}{active_marker}")
            lines.append(f"  Neurons: {brain['total_neurons']}, Bombed: {brain['bombed_layers']}")
        
        if active:
            lines.extend(["", f"Active brain: {active}"])
        
        return True, "\n".join(lines)
    
    subcommand = args[0].lower()
    sub_args = args[1:]
    
    if subcommand == "init":
        if not sub_args:
            return False, "Usage: /brain init <name>"
        success, msg = init_brain(sub_args[0])
        return success, msg
    
    elif subcommand == "list":
        brains = list_brains()
        if not brains:
            return True, "No brains found. Create one with /brain init <name>"
        
        lines = ["🧠 Available Brains:", ""]
        for brain in brains:
            marker = " ✅" if brain["is_active"] else ""
            lines.append(f"- {brain['name']}{marker}")
            lines.append(f"  📊 {brain['total_neurons']} neurons, 💣 {brain['bombed_layers']} bombed")
        return True, "\n".join(lines)
    
    elif subcommand == "activate":
        if not sub_args:
            active = get_active_brain_name()
            return True, f"Active brain: {active or 'None'}"
        success, msg = activate_brain(sub_args[0])
        return success, msg
    
    elif subcommand == "emit":
        success, content = emit_brain()
        return success, content
    
    elif subcommand == "fire":
        if not sub_args:
            return False, "Usage: /brain fire <path>"
        success, msg = fire_neuron("/".join(sub_args))
        return success, msg
    
    elif subcommand == "bomb":
        if not sub_args:
            return False, "Usage: /brain bomb <path>"
        success, msg = bomb_neuron("/".join(sub_args))
        return success, msg
    
    elif subcommand == "unbomb":
        if not sub_args:
            return False, "Usage: /brain unbomb <path>"
        success, msg = unbomb_neuron("/".join(sub_args))
        return success, msg
    
    elif subcommand == "diag":
        name = sub_args[0] if sub_args else None
        success, output = diag_brain(name)
        return success, output
    
    elif subcommand == "scan":
        # Scan and show stats for a brain
        name = sub_args[0] if sub_args else get_active_brain_name()
        if not name:
            return False, "No brain specified and no active brain"
        brain = scan_brain(name)
        if not brain:
            return False, f"Brain '{name}' not found"
        
        lines = [
            f"🧠 Brain: {brain.name}",
            f"📍 Path: {brain.path}",
            f"📊 Total neurons: {brain.total_neurons}",
            f"💣 Bombed: {brain.bombed_count}",
            "",
            "Layers:",
        ]
        for layer in brain.layers:
            lines.append(f"  - {layer.name}: {len(layer.neurons)} neurons")
        
        return True, "\n".join(lines)
    
    else:
        return False, f"Unknown subcommand: {subcommand}\n\nValid subcommands: init, list, activate, emit, fire, bomb, unbomb, diag, scan"
