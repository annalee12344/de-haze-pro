# Clear Vision Studio

Design a modern, premium web interface for an image dehazing tool called DEHAZE.

The product removes haze, fog, and atmospheric distortion from images and allows users to compare the original image with the enhanced result.

Overall Design Direction

Create a UI that feels current, sophisticated, minimal, and technically credible — like a modern creative/image-processing tool rather than a generic AI startup landing page.

Avoid the typical overused AI visual language:

No robot illustrations

No AI brain icons

No excessive sparkle icons

No purple/blue AI gradients everywhere

No glowing neon buttons

No unnecessary futuristic HUD elements

No excessive glassmorphism

No generic “Powered by AI” messaging

The interface should communicate image processing, precision, clarity, and visual transformation through the imagery itself rather than through AI-themed decoration.

Use a restrained visual system:

Neutral background

Strong typography

Subtle borders

Soft shadows

Carefully controlled accent color

Large image previews as the main visual element

Generous whitespace

Editorial / professional design feeling

Main Page

Create a single-page application with three main areas:

1. Header

A minimal navigation bar.

Left:
DEHAZE

Small subtitle:
Image Restoration

Center/right navigation:

Workspace

How it works

About

Right:
A subtle Upload Image button.

Keep the header compact and elegant.

2. Hero / Upload Area

Large centered headline:

See clearly again.

Supporting text:

Remove haze and atmospheric distortion from your images with a simple, precise enhancement workflow.

Below it, create a large drag-and-drop upload area.

The upload area should feel like a modern image editor rather than a generic SaaS upload box.

Display:

Drop an image here

or

Choose an image

Small supporting text:

JPG, PNG, WEBP · Up to 20 MB

Use a very subtle visual cue such as a thin image-frame outline instead of a large upload icon.

Add a small text link:

Try a sample image

The sample image should demonstrate a hazy landscape or city scene.

3. Processing Workspace

After an image is uploaded, transition into an image-processing workspace.

The workspace should become the primary focus of the screen.

Use a large image comparison viewer.

Left side:
Original

Right side:
Dehazed

Provide an interactive before/after comparison slider in the center.

The comparison should be visually impressive because the image itself demonstrates the product's value.

Below the image:

A compact control panel with:

Dehazing

Auto

Mild

Balanced

Strong

Fine adjustment

Haze Removal

Contrast

Brightness

Saturation

Keep controls minimal and professional. Avoid excessive sliders.

Include:

Reset

and a prominent but understated:

Download Image

button.

Visual Style

Use a sophisticated editorial-tech aesthetic.

Typography:

Modern sans-serif

Strong large headline

Clear hierarchy

Avoid overly rounded “startup” typography

Colors:

Mostly neutral

Off-white or very light gray background

Near-black text

One restrained accent color

Accent should be used only for interactive states and important actions

The interface should feel similar in quality to a professional creative tool such as a modern photo editor.

Interaction Design

Include subtle micro-interactions:

Drag-and-drop upload area responds to hover

Image preview fades smoothly into the workspace

Before/after slider moves smoothly

Processing state uses a minimal progress indicator

Buttons have subtle hover transitions

Avoid excessive animations

For the processing state, do NOT use a spinning AI brain or “AI magic” animation.

Instead display:

Analyzing image…

followed by:

Restoring visibility…

with a subtle linear progress indicator.

Important UX Principle

The product should visually communicate:

Before → Process → After

The transformation of the image should be the hero of the experience.

Do not make the interface look like an AI chatbot or an AI generator.

It should feel like a professional computational photography / image restoration tool.

Responsive Design

Desktop:

Large image comparison workspace

Spacious layout

Maximum content width around 1200–1400px

Tablet:

Reduce spacing

Maintain large image preview

Mobile:

Stack controls vertically

Make the before/after comparison swipe-friendly

Keep upload experience simple

Overall Impression

The final design should feel:

Minimal + premium + visual + technical + contemporary

rather than:

Generic SaaS + AI + neon + excessive icons

The interface should be simple enough that a user immediately understands:

Upload → Dehaze → Compare → Download

This project was built with [Lovable](https://lovable.dev).

**Live app**: https://de-haze-pro.lovable.app

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/0bae3ee5-ad36-4297-8ef0-52e8d467cb0c).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
