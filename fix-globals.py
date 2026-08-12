import re

with open('website/style.css', 'r', encoding='utf-8') as f:
    style = f.read()

# I will keep the original :root and body so it works perfectly.
# BUT I must add .hs-app { width: 100vw; flex: 1; }

content = """@import 'tailwindcss';
@import 'tw-animate-css';
@import 'shadcn/tailwind.css';

@custom-variant dark (&:is(.dark *));

@theme inline {
  --font-sans: "Inter", system-ui, sans-serif;
  --font-display: "Space Grotesk", sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}

.hs-app {
  width: 100vw;
  flex: 1;
}

/* ============================================
   Vanilla Styles 
   ============================================ */
"""

with open('website/app/globals.css', 'w', encoding='utf-8') as f:
    f.write(content + style)

print("Globals built successfully")
