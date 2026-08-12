import re

with open('website/style.css', 'r', encoding='utf-8') as f:
    style = f.read()

# Strip out :root and body so we can inject them correctly
style = re.sub(r':root\s*\{[^}]*\}', '', style, flags=re.DOTALL)
style = re.sub(r'body\s*\{[^}]*\}', '', style, flags=re.DOTALL)

# Refactor hardcoded backgrounds in style.css to use CSS variables
style = style.replace('background: rgba(5, 5, 5, 0.8)', 'background: var(--topbar-bg)')
style = style.replace('background: rgba(10, 10, 12, 0.9)', 'background: var(--nav-bg)')
style = style.replace('background: rgba(10, 10, 12, 0.7)', 'background: var(--bg-glass)')
style = style.replace('background: rgba(255, 255, 255, 0.03)', 'background: var(--hover)')
style = style.replace('background: rgba(255,255,255,0.03)', 'background: var(--hover)')
style = style.replace('background: rgba(255,255,255,0.08)', 'background: var(--track)')
style = style.replace('background: rgba(255, 255, 255, 0.1)', 'background: var(--btn)')
style = style.replace('background: rgba(255,255,255,0.1)', 'background: var(--btn)')
style = style.replace('rgba(255, 255, 255, 0.2)', 'var(--btn-hover)')
style = style.replace('background: rgba(0, 0, 0, 0.6)', 'background: var(--overlay)')
style = style.replace('background: rgba(255,255,255,0.25)', 'background: var(--private)')
style = style.replace('rgba(255, 255, 255, 0.12)', 'var(--border-light)')

content = """@import 'tailwindcss';
@import 'tw-animate-css';
@import 'shadcn/tailwind.css';

@custom-variant dark (&:is(.dark *));

@theme inline {
  --font-sans: "Inter", system-ui, sans-serif;
  --font-display: "Space Grotesk", sans-serif;
  --font-mono: "JetBrains Mono", monospace;
  --color-background: var(--background);
  --color-foreground: var(--foreground);
}

:root {
  color-scheme: light;
  --background: #f4f4f6;
  --foreground: #101013;
  --radius: 0.625rem;
}
.dark {
  color-scheme: dark;
  --background: #050505;
  --foreground: #ffffff;
}

.hs-app {
  --crimson: #b00020;
  --crimson-dark: #8b0000;
  --crimson-glow: rgba(176, 0, 32, 0.3);
  --border-red: rgba(176, 0, 32, 0.2);
  --border-red-glow: rgba(176, 0, 32, 0.5);
  --shadow-crimson: 0 8px 32px rgba(176, 0, 32, 0.15);
  --green: #2dd55b;
  --danger: #d92c2c;

  --bg-deep: #f4f4f6;
  --bg-surface: #ffffff;
  --bg-glass: rgba(255, 255, 255, 0.72);
  --border-light: rgba(0, 0, 0, 0.1);
  --text-main: #101013;
  --text-muted: #6b6b74;
  --hover: rgba(0, 0, 0, 0.04);
  --track: rgba(0, 0, 0, 0.08);
  --btn: rgba(0, 0, 0, 0.06);
  --btn-hover: rgba(0, 0, 0, 0.12);
  --topbar-bg: rgba(244, 244, 246, 0.8);
  --nav-bg: rgba(255, 255, 255, 0.9);
  --radial: rgba(176, 0, 32, 0.04);
  --private: rgba(0, 0, 0, 0.28);
  --overlay: rgba(0, 0, 0, 0.35);

  font-family: "Inter", system-ui, sans-serif;
  background: var(--bg-deep) radial-gradient(circle at top right, var(--radial), transparent 50%);
  color: var(--text-main);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  height: 100vh;
  height: 100dvh;
  width: 100vw;
  flex: 1;
  overflow: hidden;
  display: flex;
}

.dark .hs-app {
  --bg-deep: #050505;
  --bg-surface: #0a0a0c;
  --bg-glass: rgba(10, 10, 12, 0.7);
  --border-light: rgba(255, 255, 255, 0.12);
  --text-main: #ffffff;
  --text-muted: #a0a0a0;
  --hover: rgba(255, 255, 255, 0.03);
  --track: rgba(255, 255, 255, 0.1);
  --btn: rgba(255, 255, 255, 0.1);
  --btn-hover: rgba(255, 255, 255, 0.2);
  --topbar-bg: rgba(5, 5, 5, 0.8);
  --nav-bg: rgba(10, 10, 12, 0.9);
  --radial: rgba(139, 0, 0, 0.05);
  --private: rgba(255, 255, 255, 0.25);
  --overlay: rgba(0, 0, 0, 0.6);
}

@layer base {
  body {
    background: var(--background);
    color: var(--foreground);
    font-family: "Inter", system-ui, sans-serif;
  }
}
"""

with open('website/app/globals.css', 'w', encoding='utf-8') as f:
    f.write(content + '\n/* Vanilla Styles */\n' + style)

print("globals.css has been completely fixed and optimized for Light/Dark mode.")
