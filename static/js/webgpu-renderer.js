/* WebGPU Canvas Renderer for High-Performance Parking Space Rendering */

class WebGPURenderer {
    constructor() {
        this.device = null;
        this.context = null;
        this.canvas = null;
        this.pipeline = null;
        this.bindGroup = null;
        this.uniformBuffer = null;
        this.spaceDataBuffer = null;
        this.vertexBuffer = null;
        this.indexBuffer = null;
        this.backgroundTexture = null;
        this.isInitialized = false;
        this.spaces = [];
        this.maxSpaces = 1000; // Maximum number of parking spaces
        this.canvasSize = { width: 800, height: 600 };
        this.backgroundImage = null;
    }

    // Check if WebGPU is supported
    static isSupported() {
        return 'gpu' in navigator;
    }

    // Initialize WebGPU
    async init(canvas) {
        if (!WebGPURenderer.isSupported()) {
            AdminLogs.log('INFO', 'WebGPU not supported, falling back to Fabric.js');
            return false;
        }

        try {
            this.canvas = canvas;
            
            // Get WebGPU adapter and device
            const adapter = await navigator.gpu.requestAdapter({
                powerPreference: 'high-performance'
            });
            
            if (!adapter) {
                AdminLogs.log('WARNING', 'WebGPU adapter not available');
                return false;
            }

            this.device = await adapter.requestDevice();
            
            // Setup canvas context
            this.context = canvas.getContext('webgpu');
            const canvasFormat = navigator.gpu.getPreferredCanvasFormat();
            
            this.context.configure({
                device: this.device,
                format: canvasFormat,
                alphaMode: 'premultiplied'
            });

            // Create render pipeline
            await this.createRenderPipeline(canvasFormat);
            
            // Create buffers
            this.createBuffers();
            
            this.isInitialized = true;
            AdminLogs.log('INFO', 'WebGPU renderer initialized successfully');
            return true;
        } catch (error) {
            AdminLogs.log('ERROR', 'Failed to initialize WebGPU:', error);
            return false;
        }
    }

    // Create the render pipeline with shaders
    async createRenderPipeline(format) {
        const vertexShaderSource = `
            struct Uniforms {
                viewProjectionMatrix: mat4x4<f32>,
                canvasSize: vec2<f32>,
                backgroundSize: vec2<f32>,
                backgroundScale: vec2<f32>,
            }

            struct SpaceData {
                position: vec2<f32>,
                size: vec2<f32>,
                color: vec4<f32>,
                isBooked: f32,
                spaceNumber: f32,
                padding: vec2<f32>,
            }

            struct VertexInput {
                @location(0) position: vec2<f32>,
                @location(1) texCoord: vec2<f32>,
            }

            struct VertexOutput {
                @builtin(position) position: vec4<f32>,
                @location(0) texCoord: vec2<f32>,
                @location(1) spaceColor: vec4<f32>,
                @location(2) spacePos: vec2<f32>,
                @location(3) spaceSize: vec2<f32>,
                @location(4) isBooked: f32,
            }

            @group(0) @binding(0) var<uniform> uniforms: Uniforms;
            @group(0) @binding(1) var<storage, read> spaceData: array<SpaceData>;

            @vertex
            fn vs_main(input: VertexInput, @builtin(instance_index) instanceIndex: u32) -> VertexOutput {
                var output: VertexOutput;
                
                let space = spaceData[instanceIndex];
                let worldPos = input.position * space.size + space.position;
                
                // Convert to normalized device coordinates
                let ndcPos = (worldPos / uniforms.canvasSize) * 2.0 - 1.0;
                output.position = vec4<f32>(ndcPos.x, -ndcPos.y, 0.0, 1.0);
                
                output.texCoord = input.texCoord;
                output.spaceColor = space.color;
                output.spacePos = space.position;
                output.spaceSize = space.size;
                output.isBooked = space.isBooked;
                
                return output;
            }
        `;

        const fragmentShaderSource = `
            struct FragmentInput {
                @location(0) texCoord: vec2<f32>,
                @location(1) spaceColor: vec4<f32>,
                @location(2) spacePos: vec2<f32>,
                @location(3) spaceSize: vec2<f32>,
                @location(4) isBooked: f32,
            }

            @group(0) @binding(2) var backgroundSampler: sampler;
            @group(0) @binding(3) var backgroundTexture: texture_2d<f32>;

            @fragment
            fn fs_main(input: FragmentInput) -> @location(0) vec4<f32> {
                // Sample background if available
                let bgColor = textureSample(backgroundTexture, backgroundSampler, input.texCoord);
                
                // Create parking space with border
                let borderWidth = 2.0;
                let spaceCenter = input.spaceSize * 0.5;
                let localPos = input.texCoord * input.spaceSize;
                
                let distToEdge = min(
                    min(localPos.x, input.spaceSize.x - localPos.x),
                    min(localPos.y, input.spaceSize.y - localPos.y)
                );
                
                var spaceColor = input.spaceColor;
                
                // Red for booked spaces
                if (input.isBooked > 0.5) {
                    spaceColor = vec4<f32>(0.8, 0.2, 0.2, 0.8);
                }
                
                // Add border
                if (distToEdge < borderWidth) {
                    spaceColor = vec4<f32>(0.0, 0.0, 0.0, 1.0); // Black border
                }
                
                // Blend with background
                let alpha = spaceColor.a;
                return vec4<f32>(
                    mix(bgColor.rgb, spaceColor.rgb, alpha),
                    max(bgColor.a, alpha)
                );
            }
        `;

        const vertexShaderModule = this.device.createShaderModule({
            code: vertexShaderSource
        });

        const fragmentShaderModule = this.device.createShaderModule({
            code: fragmentShaderSource
        });

        // Create bind group layout
        const bindGroupLayout = this.device.createBindGroupLayout({
            entries: [
                {
                    binding: 0,
                    visibility: GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT,
                    buffer: { type: 'uniform' }
                },
                {
                    binding: 1,
                    visibility: GPUShaderStage.VERTEX,
                    buffer: { type: 'read-only-storage' }
                },
                {
                    binding: 2,
                    visibility: GPUShaderStage.FRAGMENT,
                    sampler: {}
                },
                {
                    binding: 3,
                    visibility: GPUShaderStage.FRAGMENT,
                    texture: {}
                }
            ]
        });

        // Create pipeline layout
        const pipelineLayout = this.device.createPipelineLayout({
            bindGroupLayouts: [bindGroupLayout]
        });

        // Create render pipeline
        this.pipeline = this.device.createRenderPipeline({
            layout: pipelineLayout,
            vertex: {
                module: vertexShaderModule,
                entryPoint: 'vs_main',
                buffers: [
                    {
                        arrayStride: 4 * 4, // 2 floats for position + 2 floats for texCoord
                        attributes: [
                            {
                                format: 'float32x2',
                                offset: 0,
                                shaderLocation: 0 // position
                            },
                            {
                                format: 'float32x2',
                                offset: 2 * 4,
                                shaderLocation: 1 // texCoord
                            }
                        ]
                    }
                ]
            },
            fragment: {
                module: fragmentShaderModule,
                entryPoint: 'fs_main',
                targets: [
                    {
                        format: format,
                        blend: {
                            color: {
                                srcFactor: 'src-alpha',
                                dstFactor: 'one-minus-src-alpha'
                            },
                            alpha: {
                                srcFactor: 'one',
                                dstFactor: 'one-minus-src-alpha'
                            }
                        }
                    }
                ]
            },
            primitive: {
                topology: 'triangle-list'
            }
        });

        this.bindGroupLayout = bindGroupLayout;
    }

    // Create buffers for vertices, uniforms, and space data
    createBuffers() {
        // Vertex buffer for a quad (two triangles)
        const vertices = new Float32Array([
            0.0, 0.0,  0.0, 0.0, // Bottom-left
            1.0, 0.0,  1.0, 0.0, // Bottom-right
            0.0, 1.0,  0.0, 1.0, // Top-left
            1.0, 1.0,  1.0, 1.0, // Top-right
        ]);

        const indices = new Uint16Array([
            0, 1, 2,  // First triangle
            2, 1, 3   // Second triangle
        ]);

        this.vertexBuffer = this.device.createBuffer({
            size: vertices.byteLength,
            usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST
        });
        this.device.queue.writeBuffer(this.vertexBuffer, 0, vertices);

        this.indexBuffer = this.device.createBuffer({
            size: indices.byteLength,
            usage: GPUBufferUsage.INDEX | GPUBufferUsage.COPY_DST
        });
        this.device.queue.writeBuffer(this.indexBuffer, 0, indices);

        // Uniform buffer
        this.uniformBuffer = this.device.createBuffer({
            size: 80, // mat4x4 (64 bytes) + vec2 + vec2 + vec2 (12 bytes) + padding
            usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST
        });

        // Space data buffer
        const spaceDataSize = this.maxSpaces * 32; // 8 floats per space * 4 bytes per float
        this.spaceDataBuffer = this.device.createBuffer({
            size: spaceDataSize,
            usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST
        });

        // Create default background texture
        this.createDefaultBackgroundTexture();
    }

    // Create a default background texture
    createDefaultBackgroundTexture() {
        const textureSize = 256;
        const data = new Uint8Array(textureSize * textureSize * 4);
        
        // Fill with a light gray pattern
        for (let i = 0; i < data.length; i += 4) {
            data[i] = 240;     // R
            data[i + 1] = 240; // G
            data[i + 2] = 240; // B
            data[i + 3] = 255; // A
        }

        this.backgroundTexture = this.device.createTexture({
            size: [textureSize, textureSize, 1],
            format: 'rgba8unorm',
            usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST
        });

        this.device.queue.writeTexture(
            { texture: this.backgroundTexture },
            data,
            { bytesPerRow: textureSize * 4 },
            [textureSize, textureSize, 1]
        );

        this.createBindGroup();
    }

    // Load background image texture
    async loadBackgroundImage(imageUrl) {
        try {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
                img.src = imageUrl;
            });

            this.backgroundImage = img;

            // Create canvas to extract image data
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            
            const imageData = ctx.getImageData(0, 0, img.width, img.height);

            // Create WebGPU texture
            this.backgroundTexture = this.device.createTexture({
                size: [img.width, img.height, 1],
                format: 'rgba8unorm',
                usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST
            });

            this.device.queue.writeTexture(
                { texture: this.backgroundTexture },
                imageData.data,
                { bytesPerRow: img.width * 4 },
                [img.width, img.height, 1]
            );

            this.createBindGroup();
            AdminLogs.log('DEBUG', 'Background image loaded into WebGPU texture');
        } catch (error) {
            AdminLogs.log('ERROR', 'Failed to load background image:', error);
        }
    }

    // Create bind group for uniforms and textures
    createBindGroup() {
        const sampler = this.device.createSampler({
            magFilter: 'linear',
            minFilter: 'linear'
        });

        this.bindGroup = this.device.createBindGroup({
            layout: this.bindGroupLayout,
            entries: [
                {
                    binding: 0,
                    resource: { buffer: this.uniformBuffer }
                },
                {
                    binding: 1,
                    resource: { buffer: this.spaceDataBuffer }
                },
                {
                    binding: 2,
                    resource: sampler
                },
                {
                    binding: 3,
                    resource: this.backgroundTexture.createView()
                }
            ]
        });
    }

    // Update parking spaces data
    updateSpaces(spaces) {
        this.spaces = spaces.slice(0, this.maxSpaces);
        
        // Convert spaces data to buffer format
        const spaceData = new Float32Array(this.maxSpaces * 8);
        
        for (let i = 0; i < this.spaces.length; i++) {
            const space = this.spaces[i];
            const offset = i * 8;
            
            // Parse color from hex or named color
            const color = this.parseColor(space.color || '#00ff00');
            
            spaceData[offset] = space.position_x || 0;     // position.x
            spaceData[offset + 1] = space.position_y || 0; // position.y
            spaceData[offset + 2] = space.width || 50;     // size.x
            spaceData[offset + 3] = space.height || 30;    // size.y
            spaceData[offset + 4] = color.r;               // color.r
            spaceData[offset + 5] = color.g;               // color.g
            spaceData[offset + 6] = color.b;               // color.b
            spaceData[offset + 7] = color.a;               // color.a (also used for isBooked)
        }

        this.device.queue.writeBuffer(this.spaceDataBuffer, 0, spaceData);
    }

    // Update space availability (which spaces are booked)
    updateAvailability(bookedSpaceIds) {
        if (!this.spaces.length) return;

        const spaceData = new Float32Array(this.spaces.length * 8);
        const bookedSet = new Set(bookedSpaceIds);

        for (let i = 0; i < this.spaces.length; i++) {
            const space = this.spaces[i];
            const offset = i * 8;
            const isBooked = bookedSet.has(space.id) ? 1.0 : 0.0;
            
            const color = this.parseColor(space.color || '#00ff00');
            
            spaceData[offset] = space.position_x || 0;
            spaceData[offset + 1] = space.position_y || 0;
            spaceData[offset + 2] = space.width || 50;
            spaceData[offset + 3] = space.height || 30;
            spaceData[offset + 4] = color.r;
            spaceData[offset + 5] = color.g;
            spaceData[offset + 6] = color.b;
            spaceData[offset + 7] = isBooked; // Use this for booked status
        }

        this.device.queue.writeBuffer(this.spaceDataBuffer, 0, spaceData);
    }

    // Parse color string to RGBA values
    parseColor(colorString) {
        // Handle hex colors
        if (colorString.startsWith('#')) {
            const hex = colorString.slice(1);
            const r = parseInt(hex.slice(0, 2), 16) / 255;
            const g = parseInt(hex.slice(2, 4), 16) / 255;
            const b = parseInt(hex.slice(4, 6), 16) / 255;
            return { r, g, b, a: 0.8 };
        }
        
        // Handle named colors (simplified)
        const namedColors = {
            'red': { r: 1, g: 0, b: 0, a: 0.8 },
            'green': { r: 0, g: 1, b: 0, a: 0.8 },
            'blue': { r: 0, g: 0, b: 1, a: 0.8 },
            'yellow': { r: 1, g: 1, b: 0, a: 0.8 },
            'orange': { r: 1, g: 0.5, b: 0, a: 0.8 }
        };
        
        return namedColors[colorString.toLowerCase()] || { r: 0, g: 1, b: 0, a: 0.8 };
    }

    // Set canvas size
    setSize(width, height) {
        this.canvasSize = { width, height };
        this.canvas.width = width;
        this.canvas.height = height;
        this.updateUniforms();
    }

    // Update uniform buffer with current state
    updateUniforms() {
        const uniforms = new Float32Array(20); // 80 bytes / 4 bytes per float
        
        // Identity matrix for now (could add camera transforms later)
        uniforms[0] = 1; uniforms[1] = 0; uniforms[2] = 0; uniforms[3] = 0;
        uniforms[4] = 0; uniforms[5] = 1; uniforms[6] = 0; uniforms[7] = 0;
        uniforms[8] = 0; uniforms[9] = 0; uniforms[10] = 1; uniforms[11] = 0;
        uniforms[12] = 0; uniforms[13] = 0; uniforms[14] = 0; uniforms[15] = 1;
        
        // Canvas size
        uniforms[16] = this.canvasSize.width;
        uniforms[17] = this.canvasSize.height;
        
        // Background size
        const bgWidth = this.backgroundImage ? this.backgroundImage.width : 256;
        const bgHeight = this.backgroundImage ? this.backgroundImage.height : 256;
        uniforms[18] = bgWidth;
        uniforms[19] = bgHeight;

        this.device.queue.writeBuffer(this.uniformBuffer, 0, uniforms);
    }

    // Render the parking spaces
    render() {
        if (!this.isInitialized || !this.spaces.length) return;

        this.updateUniforms();

        const commandEncoder = this.device.createCommandEncoder();
        const renderPassDescriptor = {
            colorAttachments: [
                {
                    view: this.context.getCurrentTexture().createView(),
                    clearValue: { r: 0.9, g: 0.9, b: 0.9, a: 1.0 },
                    loadOp: 'clear',
                    storeOp: 'store'
                }
            ]
        };

        const passEncoder = commandEncoder.beginRenderPass(renderPassDescriptor);
        passEncoder.setPipeline(this.pipeline);
        passEncoder.setBindGroup(0, this.bindGroup);
        passEncoder.setVertexBuffer(0, this.vertexBuffer);
        passEncoder.setIndexBuffer(this.indexBuffer, 'uint16');
        
        // Draw all spaces as instances
        passEncoder.drawIndexed(6, this.spaces.length, 0, 0, 0);
        
        passEncoder.end();

        this.device.queue.submit([commandEncoder.finish()]);
    }

    // Clean up resources
    destroy() {
        if (this.vertexBuffer) this.vertexBuffer.destroy();
        if (this.indexBuffer) this.indexBuffer.destroy();
        if (this.uniformBuffer) this.uniformBuffer.destroy();
        if (this.spaceDataBuffer) this.spaceDataBuffer.destroy();
        if (this.backgroundTexture) this.backgroundTexture.destroy();
        
        this.isInitialized = false;
    }
}

// Export for use in other modules
window.WebGPURenderer = WebGPURenderer;

AdminLogs.log('INFO', 'WebGPU Renderer module loaded');
