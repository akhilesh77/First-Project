---
name: Ultra-Premium Culinary Discovery
colors:
  surface: '#111317'
  surface-dim: '#111317'
  surface-bright: '#37393e'
  surface-container-lowest: '#0c0e12'
  surface-container-low: '#1a1c20'
  surface-container: '#1e2024'
  surface-container-high: '#282a2e'
  surface-container-highest: '#333539'
  on-surface: '#e2e2e8'
  on-surface-variant: '#ddc0c0'
  inverse-surface: '#e2e2e8'
  inverse-on-surface: '#2f3035'
  outline: '#a48a8b'
  outline-variant: '#564243'
  surface-tint: '#ffb2b7'
  primary: '#ffb2b7'
  on-primary: '#65061d'
  primary-container: '#ff7e8b'
  on-primary-container: '#751427'
  inverse-primary: '#a43947'
  secondary: '#d1bcff'
  on-secondary: '#3d008f'
  secondary-container: '#5d04d2'
  on-secondary-container: '#c8afff'
  tertiary: '#3cddc7'
  on-tertiary: '#003731'
  tertiary-container: '#00baa7'
  on-tertiary-container: '#00443c'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdadb'
  primary-fixed-dim: '#ffb2b7'
  on-primary-fixed: '#40000e'
  on-primary-fixed-variant: '#842131'
  secondary-fixed: '#eaddff'
  secondary-fixed-dim: '#d1bcff'
  on-secondary-fixed: '#24005b'
  on-secondary-fixed-variant: '#5800c8'
  tertiary-fixed: '#62fae3'
  tertiary-fixed-dim: '#3cddc7'
  on-tertiary-fixed: '#00201c'
  on-tertiary-fixed-variant: '#005047'
  background: '#111317'
  on-background: '#e2e2e8'
  surface-variant: '#333539'
typography:
  display-lg:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Outfit
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-margin: 24px
  gutter: 16px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style
The design system is centered on the intersection of culinary artistry and artificial intelligence. It targets a sophisticated audience that views food as an experiential journey rather than a utility. The brand personality is "Intelligent Luxury"—combining the precision of high-tech exploration with the warmth of a gourmet kitchen.

The visual style is a **Modern Glassmorphic** evolution. It utilizes deep, multi-layered backgrounds to create a sense of infinite space, while UI elements appear as suspended crystalline panes. This approach ensures the vibrant food photography remains the focal point, framed by high-end, translucent interface components that feel lightweight and futuristic.

## Colors
This design system utilizes a "Midnight Canvas" palette. The foundation is a deep charcoal-navy (`#0F1115`) which provides the necessary contrast for glass effects and vibrant food imagery.

*   **Primary (Brand Coral):** `#FF7E8B` - Used for primary actions, branding, and highlighting "appetizing" elements.
*   **Secondary (Royal Purple):** `#8A4FFF` - Represents the AI intelligence and premium status; used for special features and gradients.
*   **Tertiary (Hyper Teal):** `#2DD4BF` - Used for freshness, sustainability indicators, and success states.
*   **Surface:** Semi-transparent variations of `#1A1D23` at 60-80% opacity with a 20px backdrop blur.

## Typography
The typography strategy pairs the geometric, modern character of **Outfit** for headlines with the high-utility legibility of **Inter** for secondary information. 

Headlines should use tight letter-spacing to feel "curated" and impactful. For mobile, display sizes scale down to prevent awkward line breaks while maintaining a bold weight. Body copy utilizes generous line heights to ensure readability against dark, textured backgrounds. Labels and metadata use increased letter-spacing and semi-bold weights to maintain hierarchy within glass containers.

## Layout & Spacing
The design system employs a **Fluid Grid** with a fixed 12-column structure for desktop and a 4-column structure for mobile. 

The layout relies on "Negative Space Air" to prevent the dark UI from feeling cramped. Content is grouped into logical modules with a standard 32px vertical rhythm. For mobile, a 24px side margin is mandatory to create a "floating" effect for card components. On desktop, the max-width is capped at 1440px to ensure food photography maintains its resolution and impact.

## Elevation & Depth
Depth is communicated through **Refractive Layers** rather than traditional shadows.

1.  **Level 0 (Base):** Deep navy `#0F1115` with subtle radial gradients of Secondary/Tertiary colors at 5% opacity to simulate ambient light.
2.  **Level 1 (Glass Cards):** Surfaces with 70% opacity, 24px backdrop blur, and a 1px solid border at 10% white (top-left) to simulate a light-catching edge.
3.  **Level 2 (Floating Elements):** Modals and floating action buttons use 90% opacity and a 40px "Deep Glow" shadow—a diffused shadow tinted with the primary coral color at very low alpha (15%).

## Shapes
The shape language is organic and approachable yet disciplined. A standard **0.5rem (8px)** corner radius is the default for input fields and small buttons. Larger containers like restaurant cards and modals utilize a **1.5rem (24px)** radius to feel softer and more premium.

Pill shapes (full rounding) are reserved exclusively for interactive tags, status indicators, and the primary "Explore" action to distinguish them from structural content containers.

## Components

*   **Glass Cards:** These are the primary vessels for restaurant data. They must include a 1px inner stroke to define the glass edge and a 20px background blur.
*   **Segmented Controls:** Budget and proximity toggles should look like "recessed" tracks with a glass "thumb" that slides over the active selection.
*   **Pill Tags:** Cuisine types and tags use a low-opacity fill of the primary or secondary color (e.g., 10% opacity) with high-contrast text.
*   **Smooth Sliders:** Rating sliders use a gradient track (Purple to Coral) with a glow effect on the handle to indicate AI-assisted precision.
*   **Skeleton Loaders:** Instead of static grey, use a pulsing shimmer that mimics the light moving through glass, transitioning from `#1A1D23` to `#252932`.
*   **AI Exploration Node:** A unique component—a floating, glowing orb that acts as the entry point for the AI explorer, using a mesh gradient of all brand colors.