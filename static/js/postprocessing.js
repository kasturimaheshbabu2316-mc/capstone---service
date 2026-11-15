/**
 * Three.js Post-Processing Passes (ES Module)
 * Extracted from three.js examples/jsm/postprocessing
 */

// RenderPass
export class RenderPass {
  constructor(scene, camera, overrideMaterial = null, clearColor = 0x000000, clearAlpha = 0) {
    this.scene = scene;
    this.camera = camera;
    this.overrideMaterial = overrideMaterial;
    this.clearColor = new THREE.Color(clearColor);
    this.clearAlpha = clearAlpha;
    this.clear = true;
    this.clearDepth = true;
    this.needsSwap = false;
  }

  render(renderer, writeBuffer, readBuffer, deltaTime, maskActive) {
    const oldAutoClear = renderer.autoClear;
    renderer.autoClear = false;

    this.scene.overrideMaterial = this.overrideMaterial;

    let oldClearColor, oldClearAlpha;
    if (this.clearColor) {
      oldClearColor = renderer.getClearColor(new THREE.Color());
      oldClearAlpha = renderer.getClearAlpha();
      renderer.setClearColor(this.clearColor, this.clearAlpha);
    }

    if (this.clearDepth) {
      renderer.clearDepth();
    }

    renderer.setRenderTarget(writeBuffer);
    if (this.clear) renderer.clear(renderer.autoClearColor, renderer.autoClearDepth, renderer.autoClearStencil);
    renderer.render(this.scene, this.camera);

    if (this.clearColor) {
      renderer.setClearColor(oldClearColor, oldClearAlpha);
    }

    this.scene.overrideMaterial = null;
    renderer.autoClear = oldAutoClear;
  }

  dispose() {
    this.scene = null;
    this.camera = null;
    this.overrideMaterial = null;
  }
}

// ShaderPass (base for custom passes)
export class ShaderPass {
  constructor(shader, textureID = "tDiffuse") {
    this.textureID = textureID;
    this.uniforms = THREE.UniformsUtils.clone(shader.uniforms);
    this.material = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      vertexShader: shader.vertexShader,
      fragmentShader: shader.fragmentShader
    });
    this.renderToScreen = false;
    this.enabled = true;
    this.needsSwap = true;
    this.clear = false;
    this.fsQuad = new FullScreenQuad(this.material);
  }

  render(renderer, writeBuffer, readBuffer, deltaTime, maskActive) {
    if (this.uniforms[this.textureID]) {
      this.uniforms[this.textureID].value = readBuffer.texture;
    }
    this.fsQuad.render(renderer);
  }

  dispose() {
    this.material.dispose();
    this.fsQuad.dispose();
  }
}

// UnrealBloomPass - Simplified single-pass version to avoid feedback loops
export class UnrealBloomPass {
  constructor(resolution, strength = 1, radius = 0.4, threshold = 0.85) {
    this.strength = strength;
    this.radius = radius;
    this.threshold = threshold;
    this.resolution = resolution.isVector2 ? resolution : new THREE.Vector2(resolution.x, resolution.y);

    // Single render target for bloom extraction
    const pars = {
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      format: THREE.RGBAFormat,
      type: THREE.HalfFloatType
    };

    this.renderTarget = new THREE.WebGLRenderTarget(
      this.resolution.x, this.resolution.y, pars
    );
    this.renderTarget.texture.name = "UnrealBloomPass.bloom";
    this.renderTarget.texture.generateMipmaps = false;

    // Simple bloom composite shader - combines bloom with original in one pass
    const bloomShader = {
      uniforms: {
        "tDiffuse": { value: null },
        "tBloom": { value: null },
        "bloomStrength": { value: strength },
        "bloomRadius": { value: radius },
        "bloomThreshold": { value: threshold }
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform sampler2D tBloom;
        uniform float bloomStrength;
        uniform float bloomRadius;
        uniform float bloomThreshold;
        varying vec2 vUv;

        vec3 luma(vec3 rgb) {
          return vec3(dot(rgb, vec3(0.299, 0.587, 0.114)));
        }

        void main() {
          vec4 color = texture2D(tDiffuse, vUv);
          vec4 bloomColor = texture2D(tBloom, vUv);

          vec3 lumaColor = luma(color.rgb);
          vec3 bloom = max(vec3(0.0), color.rgb - lumaColor - bloomThreshold) * bloomStrength;

          // Add pre-blurred bloom
          gl_FragColor = vec4(color.rgb + bloom + bloomColor.rgb * bloomStrength * 0.5, color.a);
        }
      `
    };

    this.material = new THREE.ShaderMaterial({
      uniforms: bloomShader.uniforms,
      vertexShader: bloomShader.vertexShader,
      fragmentShader: bloomShader.fragmentShader
    });

    // Brightness extraction + single blur pass
    const extractShader = {
      uniforms: {
        "tDiffuse": { value: null },
        "bloomThreshold": { value: threshold }
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float bloomThreshold;
        varying vec2 vUv;

        void main() {
          vec4 color = texture2D(tDiffuse, vUv);
          vec3 luma = vec3(dot(color.rgb, vec3(0.299, 0.587, 0.114)));
          vec3 bright = max(vec3(0.0), color.rgb - luma - bloomThreshold);
          gl_FragColor = vec4(bright * 2.0, color.a);
        }
      `
    };

    this.extractMaterial = new THREE.ShaderMaterial({
      uniforms: extractShader.uniforms,
      vertexShader: extractShader.vertexShader,
      fragmentShader: extractShader.fragmentShader
    });

    // Simple box blur for bloom
    const blurShader = {
      uniforms: {
        "tDiffuse": { value: null },
        "direction": { value: new THREE.Vector2() },
        "resolution": { value: new THREE.Vector2() }
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform vec2 direction;
        uniform vec2 resolution;
        varying vec2 vUv;

        void main() {
          vec2 texelSize = 1.0 / resolution;
          vec4 sum = vec4(0.0);
          float weightSum = 0.0;

          for (int i = -4; i <= 4; i++) {
            float offset = float(i);
            vec2 sampleOffset = direction * texelSize * offset;
            vec4 sampleColor = texture2D(tDiffuse, vUv + sampleOffset);
            float weight = exp(-0.5 * offset * offset / 4.0);
            sum += sampleColor * weight;
            weightSum += weight;
          }

          gl_FragColor = sum / weightSum;
        }
      `
    };

    this.blurMaterial = new THREE.ShaderMaterial({
      uniforms: blurShader.uniforms,
      vertexShader: blurShader.vertexShader,
      fragmentShader: blurShader.fragmentShader
    });

    this.fsQuad = new FullScreenQuad(null);
    this.enabled = true;
    this.needsSwap = true;
    this.clear = false;
  }

  render(renderer, writeBuffer, readBuffer, deltaTime, maskActive) {
    // 1. Extract bright areas to bloom render target
    this.extractMaterial.uniforms["tDiffuse"].value = readBuffer.texture;
    this.extractMaterial.uniforms["bloomThreshold"].value = this.threshold;

    this.fsQuad.material = this.extractMaterial;
    renderer.setRenderTarget(this.renderTarget);
    renderer.clear();
    this.fsQuad.render(renderer);

    // 2. Apply horizontal blur to bloom texture
    this.blurMaterial.uniforms["tDiffuse"].value = this.renderTarget.texture;
    this.blurMaterial.uniforms["direction"].value.set(1.0, 0.0);
    this.blurMaterial.uniforms["resolution"].value.set(
      this.resolution.x, this.resolution.y
    );
    this.fsQuad.material = this.blurMaterial;
    renderer.setRenderTarget(this.renderTarget);
    renderer.clear();
    this.fsQuad.render(renderer);

    // 3. Apply vertical blur to bloom texture
    this.blurMaterial.uniforms["tDiffuse"].value = this.renderTarget.texture;
    this.blurMaterial.uniforms["direction"].value.set(0.0, 1.0);
    this.fsQuad.material = this.blurMaterial;
    renderer.setRenderTarget(this.renderTarget);
    renderer.clear();
    this.fsQuad.render(renderer);

    // 4. Composite bloom with original
    this.material.uniforms["tDiffuse"].value = readBuffer.texture;
    this.material.uniforms["tBloom"].value = this.renderTarget.texture;
    this.material.uniforms["bloomStrength"].value = this.strength;
    this.material.uniforms["bloomRadius"].value = this.radius;
    this.material.uniforms["bloomThreshold"].value = this.threshold;

    this.fsQuad.material = this.material;

    if (this.renderToScreen) {
      renderer.setRenderTarget(null);
    } else {
      renderer.setRenderTarget(writeBuffer);
    }
    renderer.clear();
    this.fsQuad.render(renderer);
  }

  dispose() {
    this.renderTarget.dispose();
    this.material.dispose();
    this.extractMaterial.dispose();
    this.blurMaterial.dispose();
    this.fsQuad.dispose();
  }
}

// FilmPass for film grain
export class FilmPass {
  constructor(noiseIntensity = 0.5, scanlinesIntensity = 0.5, scanlinesCount = 512, grayscale = false) {
    this.enabled = true;
    this.needsSwap = true;
    this.uniforms = {
      "tDiffuse": { value: null },
      "noiseIntensity": { value: noiseIntensity },
      "scanlinesIntensity": { value: scanlinesIntensity },
      "scanlinesCount": { value: scanlinesCount },
      "grayscale": { value: grayscale },
      "time": { value: 0 }
    };

    this.material = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float noiseIntensity;
        uniform float scanlinesIntensity;
        uniform float scanlinesCount;
        uniform bool grayscale;
        uniform float time;
        varying vec2 vUv;

        float rand(vec2 co) {
          return fract(sin(dot(co.xy, vec2(12.9898, 78.233))) * 43758.5453);
        }

        void main() {
          vec4 color = texture2D(tDiffuse, vUv);

          // Film grain
          float noise = rand(vUv * 1000.0 + time * 10.0) * 2.0 - 1.0;
          color.rgb += noise * noiseIntensity * 0.01;

          // Scanlines
          float scanline = sin(vUv.y * scanlinesCount * 3.14159) * scanlinesIntensity * 0.02;
          color.rgb += scanline;

          // Grayscale
          if (grayscale) {
            float gray = dot(color.rgb, vec3(0.299, 0.587, 0.114));
            color.rgb = vec3(gray);
          }

          gl_FragColor = color;
        }
      `
    });

    this.fsQuad = new FullScreenQuad(this.material);
  }

  render(renderer, writeBuffer, readBuffer, deltaTime, maskActive) {
    this.uniforms["tDiffuse"].value = readBuffer.texture;
    this.uniforms["time"].value += deltaTime;
    this.fsQuad.render(renderer);
  }

  dispose() {
    this.material.dispose();
    this.fsQuad.dispose();
  }
}

// VignettePass
export class VignettePass {
  constructor(intensity = 0.5, smoothness = 0.5, color = 0x000000) {
    this.enabled = true;
    this.needsSwap = true;
    this.uniforms = {
      "tDiffuse": { value: null },
      "intensity": { value: intensity },
      "smoothness": { value: smoothness },
      "color": { value: new THREE.Color(color) }
    };

    this.material = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float intensity;
        uniform float smoothness;
        uniform vec3 color;
        varying vec2 vUv;

        void main() {
          vec4 texel = texture2D(tDiffuse, vUv);
          vec2 center = vUv - 0.5;
          float dist = length(center) * 2.0;
          float vignette = smoothstep(1.0 - smoothness, 1.0, dist);
          vignette = 1.0 - vignette;
          vignette = mix(1.0, vignette, intensity);
          gl_FragColor = vec4(mix(color, texel.rgb, vignette), texel.a);
        }
      `
    });

    this.fsQuad = new FullScreenQuad(this.material);
  }

  render(renderer, writeBuffer, readBuffer, deltaTime, maskActive) {
    this.uniforms["tDiffuse"].value = readBuffer.texture;
    this.fsQuad.render(renderer);
  }

  dispose() {
    this.material.dispose();
    this.fsQuad.dispose();
  }
}

// EffectComposer
export class EffectComposer {
  constructor(renderer, renderTarget) {
    this.renderer = renderer;
    this.passes = [];

    if (renderTarget === undefined) {
      const pixelRatio = renderer.getPixelRatio();
      const size = renderer.getSize(new THREE.Vector2());
      this.renderTarget1 = new THREE.WebGLRenderTarget(size.x * pixelRatio, size.y * pixelRatio, {
        minFilter: THREE.LinearFilter,
        magFilter: THREE.LinearFilter,
        format: THREE.RGBAFormat,
        type: THREE.HalfFloatType
      });
      this.renderTarget2 = this.renderTarget1.clone();
    } else {
      this.renderTarget1 = renderTarget;
      this.renderTarget2 = renderTarget.clone();
    }

    this.writeBuffer = this.renderTarget1;
    this.readBuffer = this.renderTarget2;
  }

  swapBuffers() {
    const tmp = this.readBuffer;
    this.readBuffer = this.writeBuffer;
    this.writeBuffer = tmp;
  }

  addPass(pass) {
    this.passes.push(pass);
    pass.needsSwap = true;
  }

  insertPass(pass, index) {
    this.passes.splice(index, 0, pass);
    pass.needsSwap = true;
  }

  removePass(pass) {
    const index = this.passes.indexOf(pass);
    if (index !== -1) {
      this.passes.splice(index, 1);
    }
  }

  isLastEnabledPass(index) {
    for (let i = index + 1; i < this.passes.length; i++) {
      if (this.passes[i].enabled) return false;
    }
    return true;
  }

  render(deltaTime = 0) {
    if (this.passes.length === 0) return;

    const maskActive = false;
    let pass, i, il = this.passes.length;

    for (i = 0; i < il; i++) {
      pass = this.passes[i];
      if (!pass.enabled) continue;

      pass.render(this.renderer, this.writeBuffer, this.readBuffer, deltaTime, maskActive);

      if (pass.needsSwap) {
        if (maskActive) {
          // Handle stencil buffer if needed
        }
        this.swapBuffers();
      }
    }
  }

  renderToScreen() {
    this.passes[this.passes.length - 1].renderToScreen = true;
    this.render();
  }

  setSize(width, height) {
    const pixelRatio = this.renderer.getPixelRatio();
    this.renderTarget1.setSize(width * pixelRatio, height * pixelRatio);
    this.renderTarget2.setSize(width * pixelRatio, height * pixelRatio);

    this.passes.forEach(pass => {
      if (pass.setSize) pass.setSize(width, height);
    });
  }

  dispose() {
    this.renderTarget1.dispose();
    this.renderTarget2.dispose();
    this.passes.forEach(pass => pass.dispose());
  }
}

// FullScreenQuad helper
class FullScreenQuad {
  constructor(material) {
    this._mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(2, 2),
      material
    );
  }

  get material() {
    return this._mesh.material;
  }

  set material(value) {
    this._mesh.material = value;
  }

  render(renderer) {
    renderer.render(this._mesh, new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1));
  }

  dispose() {
    this._mesh.geometry.dispose();
  }
}