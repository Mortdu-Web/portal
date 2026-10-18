"""Garde-fous du thème : les deux palettes restent complètes, identiques entre elles, et sans couleur en dur."""
import re
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "hub_web" / "static" / "css"


def _blocks():
    css = (CSS / "base.css").read_text(encoding="utf-8")
    dark = re.search(r"^:root \{(.*?)\n\}", css, re.S | re.M).group(1)
    media = re.search(r":root:not\(\[data-theme\]\) \{(.*?)\n  \}", css, re.S).group(1)
    light = re.search(r':root\[data-theme="light"\] \{(.*?)\n\}', css, re.S).group(1)
    parse = lambda b: dict(re.findall(r"(--[\w-]+):\s*([^;]+);", b))
    return parse(dark), parse(media), parse(light)


def test_light_blocks_are_identical():
    _, media, light = _blocks()
    assert media == light, "Le bloc clair (prefers-color-scheme) et le bloc [data-theme=light] ont divergé"


def test_light_overrides_every_color_token():
    dark, _, light = _blocks()
    colors = {k for k in dark if k not in ("--nav-h",)}
    assert colors <= set(light), f"Tokens absents du thème clair : {colors - set(light)}"


def test_no_hardcoded_text_colors_outside_base():
    # Évite qu'un futur CSS réintroduise une couleur illisible dans un des deux thèmes.
    pattern = re.compile(r"(?<![\w-])color:\s*(#[0-9a-fA-F]{3,8}|rgba?\()")
    allowed = {"apropos.css"}  # .cv-* : visionneuse de CV, volontairement blanche sur blanc
    for f in CSS.rglob("*.css"):
        if f.name == "base.css":
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line) and f.name not in allowed:
                raise AssertionError(f"{f.name}:{n} couleur en dur : {line.strip()}")
