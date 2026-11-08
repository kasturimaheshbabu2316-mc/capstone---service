This is a single self-contained fix; keep it small and focused. Adjust the 3D Three.js orbit display to be a little smaller and well-balanced so that it looks good like a circle.

Working directory: c:\Users\kastu\Desktop\capstone - service
Integrity mode: development

## Requirements

### R1. Orbit Dimensions and Geometry Adjustment
Adjust the 3D Three.js orbital rings and stage container size (scaling from 320px down to ~260–280px) so the orbit appears slightly smaller, compact, and balanced like a circle without clipping or distorting.

### R2. Visual Integration and Animation Stability
Ensure all orbital ring animations, satellite node trajectories, and UI responsiveness remain smooth and functional across both expanded and active chat states.

## Acceptance Criteria

### Visual Geometry and Sizing
- [ ] The 3D orbit stage container is reduced from 320px to ~260–280px with proportional orbital ring radii.
- [ ] The rendered orbit presents a balanced, circular appearance in the UI without oblong distortion or overflow clipping.

### Animation and Interaction Verification
- [ ] Inspecting the rendered UI in the browser confirms the 3D orbit spins smoothly and maintains node orbits without layout shifts or console errors.