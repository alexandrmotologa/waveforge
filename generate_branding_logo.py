"""Generate authentic anti-AI-slop developer-branding mascot logo for WaveForge."""

import math

def generate_logo_svg() -> str:
    # 1024x1024 Squircle Canvas
    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">')
    svg.append('  <defs>')
    svg.append('    <linearGradient id="emeraldGlow" x1="0%" y1="0%" x2="100%" y2="100%">')
    svg.append('      <stop offset="0%" stop-color="#10b981"/>')
    svg.append('      <stop offset="100%" stop-color="#06b6d4"/>')
    svg.append('    </linearGradient>')
    svg.append('    <linearGradient id="facetHighlight" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg.append('      <stop offset="0%" stop-color="#64748b"/>')
    svg.append('      <stop offset="100%" stop-color="#334155"/>')
    svg.append('    </linearGradient>')
    svg.append('    <linearGradient id="wingGradL" x1="0%" y1="0%" x2="100%" y2="100%">')
    svg.append('      <stop offset="0%" stop-color="#334155"/>')
    svg.append('      <stop offset="100%" stop-color="#0f172a"/>')
    svg.append('    </linearGradient>')
    svg.append('    <linearGradient id="wingGradR" x1="100%" y1="0%" x2="0%" y2="100%">')
    svg.append('      <stop offset="0%" stop-color="#1e293b"/>')
    svg.append('      <stop offset="100%" stop-color="#090d16"/>')
    svg.append('    </linearGradient>')
    svg.append('  </defs>')

    # 1. Luxury White Squircle Container
    svg.append('  <!-- 1. Luxury Squircle Canvas -->')
    svg.append('  <rect x="12" y="12" width="1000" height="1000" rx="220" fill="#ffffff" stroke="#e2e8f0" stroke-width="8"/>')

    # 2. Outer Hexagonal Gateway Frame (Center 512, 512; Radius ~410)
    # Hexagon vertices: (512, 102), (867, 307), (867, 717), (512, 922), (157, 717), (157, 307)
    svg.append('  <!-- 2. Hexagonal Gateway Frame -->')
    svg.append('  <polygon points="512,102 867,307 867,717 512,922 157,717 157,307"')
    svg.append('           fill="none" stroke="#0f172a" stroke-width="36" stroke-linejoin="round"/>')
    
    # Concentric inner dashed accent ring
    # Inner hexagon vertices: Radius ~365: (512, 147), (828, 330), (828, 694), (512, 877), (196, 694), (196, 330)
    svg.append('  <polygon points="512,147 828,330 828,694 512,877 196,694 196,330"')
    svg.append('           fill="none" stroke="#10b981" stroke-width="6" stroke-dasharray="16 12" opacity="0.45"/>')

    # Acoustic Concentric Radar Arcs in background of hexagon
    svg.append('  <!-- Acoustic Wave Echolocation Rings -->')
    svg.append('  <circle cx="512" cy="512" r="300" fill="none" stroke="#f1f5f9" stroke-width="4"/>')
    svg.append('  <circle cx="512" cy="512" r="230" fill="none" stroke="#e2e8f0" stroke-width="3"/>')
    svg.append('  <circle cx="512" cy="512" r="160" fill="none" stroke="#cbd5e1" stroke-width="2" stroke-dasharray="8 8"/>')

    # 3. Mascot: The Ultrasonic Acoustic Echo Bat (Wave & Forge Metaphor)
    # 85% mass inside hexagon, perfectly symmetrical across vertical axis X=512.
    
    # Solid watertight silhouette path to guarantee zero leaks
    svg.append('  <!-- Solid Base Silhouette (Watertight Base) -->')
    base_points = [
        # Left ear tip down to wing tips and tail
        "512,410", "470,360", "400,290", "340,170", "365,340", "420,440",
        "280,480", "190,560", "240,680", "320,770", "420,830", "512,870",
        "604,830", "704,770", "784,680", "834,560", "744,480",
        "604,440", "659,340", "684,170", "624,290", "554,360"
    ]
    svg.append(f'  <polygon points="{" ".join(base_points)}" fill="#090d16"/>')

    # Low-Poly Faceted Anatomy
    svg.append('  <!-- Low-Poly Body and Wings Facets -->')

    # Left Wing Facets (Light / Volumetric side)
    svg.append('  <polygon points="512,560 420,680 512,870" fill="#1e293b"/>')
    svg.append('  <polygon points="512,560 360,570 420,680" fill="#334155"/>')
    svg.append('  <polygon points="420,680 320,770 512,870" fill="#0f172a"/>')
    svg.append('  <polygon points="360,570 280,670 420,680" fill="#1e293b"/>')
    svg.append('  <polygon points="360,570 240,560 280,670" fill="#475569"/>')
    svg.append('  <polygon points="280,670 240,680 320,770" fill="#0b1120"/>')
    svg.append('  <polygon points="240,560 190,560 280,670" fill="#334155"/>')
    svg.append('  <polygon points="360,570 280,480 240,560" fill="#64748b"/>')
    svg.append('  <polygon points="420,440 280,480 360,570" fill="#475569"/>')
    svg.append('  <polygon points="512,510 420,440 360,570" fill="#334155"/>')

    # Right Wing Facets (Shadow side, perfectly symmetrical)
    svg.append('  <polygon points="512,560 604,680 512,870" fill="#0f172a"/>')
    svg.append('  <polygon points="512,560 664,570 604,680" fill="#1e293b"/>')
    svg.append('  <polygon points="604,680 704,770 512,870" fill="#090d16"/>')
    svg.append('  <polygon points="664,570 744,670 604,680" fill="#131c2e"/>')
    svg.append('  <polygon points="664,570 784,560 744,670" fill="#1e293b"/>')
    svg.append('  <polygon points="744,670 784,680 704,770" fill="#070a12"/>')
    svg.append('  <polygon points="784,560 834,560 744,670" fill="#182235"/>')
    svg.append('  <polygon points="664,570 744,480 784,560" fill="#334155"/>')
    svg.append('  <polygon points="604,440 744,480 664,570" fill="#1e293b"/>')
    svg.append('  <polygon points="512,510 604,440 664,570" fill="#151e30"/>')

    # Thorax & Chest Armor Plate (Anvil Metaphor)
    svg.append('  <!-- Chest & Core Resonator -->')
    svg.append('  <polygon points="512,510 450,580 512,660" fill="#334155"/>')
    svg.append('  <polygon points="512,510 574,580 512,660" fill="#1e293b"/>')
    svg.append('  <polygon points="512,660 450,580 512,740" fill="#1e293b"/>')
    svg.append('  <polygon points="512,660 574,580 512,740" fill="#0f172a"/>')

    # Giant Acoustic Echolocation Ears
    svg.append('  <!-- Acoustic Echolocation Ears -->')
    # Left Ear
    svg.append('  <polygon points="430,420 340,170 390,300" fill="#1e293b"/>')
    svg.append('  <polygon points="430,420 390,300 460,350" fill="#334155"/>')
    svg.append('  <polygon points="340,170 390,300 365,340" fill="#0f172a"/>')
    svg.append('  <polygon points="430,420 365,340 420,440" fill="#151e30"/>')
    # Inner ear acoustic acoustic cavity (Resonant Emerald/Cyan)
    svg.append('  <polygon points="390,300 355,200 420,380" fill="url(#emeraldGlow)"/>')
    svg.append('  <polygon points="420,380 375,340 430,410" fill="#06b6d4" opacity="0.8"/>')

    # Right Ear (Symmetrical)
    svg.append('  <polygon points="594,420 684,170 634,300" fill="#0f172a"/>')
    svg.append('  <polygon points="594,420 634,300 564,350" fill="#1e293b"/>')
    svg.append('  <polygon points="684,170 634,300 659,340" fill="#080c14"/>')
    svg.append('  <polygon points="594,420 659,340 604,440" fill="#0d1320"/>')
    # Inner ear right cavity
    svg.append('  <polygon points="634,300 669,200 604,380" fill="url(#emeraldGlow)" opacity="0.9"/>')
    svg.append('  <polygon points="604,380 649,340 594,410" fill="#0891b2" opacity="0.8"/>')

    # Head and Craniofacial Geometry (Sharp Aerodynamic Wedge)
    svg.append('  <!-- Head & Muzzle Geometry -->')
    svg.append('  <polygon points="512,330 460,350 470,420" fill="#475569"/>')
    svg.append('  <polygon points="512,330 564,350 554,420" fill="#334155"/>')
    svg.append('  <polygon points="512,330 470,420 512,470" fill="#334155"/>')
    svg.append('  <polygon points="512,330 554,420 512,470" fill="#1e293b"/>')
    
    # Brow and Forehead Plate (Sound Wave Anvil)
    svg.append('  <polygon points="512,410 470,420 512,470" fill="#64748b"/>')
    svg.append('  <polygon points="512,410 554,420 512,470" fill="#475569"/>')

    # Muzzle & Noseleaf (Acoustic Echolocation Horn)
    svg.append('  <polygon points="512,470 485,500 512,530" fill="#94a3b8"/>')
    svg.append('  <polygon points="512,470 539,500 512,530" fill="#64748b"/>')
    svg.append('  <polygon points="512,530 495,545 512,555" fill="#475569"/>')
    svg.append('  <polygon points="512,530 529,545 512,555" fill="#334155"/>')

    # Alert Echolocation Eyes (Almond sharp polygons, electric cyan/emerald)
    svg.append('  <!-- Focused Echolocation Eyes -->')
    svg.append('  <polygon points="468,435 488,442 476,448 462,442" fill="#00f5ff"/>')
    svg.append('  <polygon points="472,440 482,443 475,446" fill="#ffffff"/>')
    svg.append('  <polygon points="556,435 536,442 548,448 562,442" fill="#00f5ff"/>')
    svg.append('  <polygon points="552,440 542,443 549,446" fill="#ffffff"/>')

    # Echolocation Soundwave Nodes on Wings
    svg.append('  <!-- PolyBLEP Wave nodes in Wing tips -->')
    svg.append('  <circle cx="280" cy="480" r="7" fill="#10b981"/>')
    svg.append('  <circle cx="744" cy="480" r="7" fill="#10b981"/>')
    svg.append('  <circle cx="190" cy="560" r="6" fill="#06b6d4"/>')
    svg.append('  <circle cx="834" cy="560" r="6" fill="#06b6d4"/>')
    svg.append('  <circle cx="240" cy="680" r="6" fill="#10b981"/>')
    svg.append('  <circle cx="784" cy="680" r="6" fill="#10b981"/>')
    svg.append('  <circle cx="320" cy="770" r="5" fill="#06b6d4"/>')
    svg.append('  <circle cx="704" cy="770" r="5" fill="#06b6d4"/>')
    svg.append('  <circle cx="512" cy="870" r="8" fill="#10b981"/>')

    svg.append('</svg>')
    return '\n'.join(svg)

if __name__ == '__main__':
    svg_content = generate_logo_svg()
    out_path = 'docs/images/waveforge_logo.svg'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f'Successfully generated {out_path}')
