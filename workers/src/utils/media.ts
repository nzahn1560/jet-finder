// Media optimization utilities for R2
// Handles image resizing, WebP conversion, and video compression

export interface ImageOptions {
    width?: number;
    height?: number;
    quality?: number;
    format?: 'webp' | 'jpeg' | 'png';
}

// Resize and convert image to WebP using Cloudflare Images API or Workers
// For MVP, we'll use a simpler approach with image processing
export async function optimizeImage(
    imageData: ArrayBuffer,
    options: ImageOptions = {}
): Promise<ArrayBuffer> {
    // Default options
    const {
        width = 1920,
        height = 1920,
        quality = 85,
        format = 'webp',
    } = options;

    // For Cloudflare Workers, we can use Cloudflare Images API
    // Or use a WASM-based image processing library
    // For MVP, we'll return the original and add optimization later

    // TODO: Implement actual image processing using:
    // - Cloudflare Images API (recommended for production)
    // - Or a WASM library like sharp-wasm

    // Placeholder: return original for now
    return imageData;
}

// Generate optimized image variants
export async function generateImageVariants(imageData: ArrayBuffer): Promise<{
    original: ArrayBuffer;
    thumbnail: ArrayBuffer;
    medium: ArrayBuffer;
    large: ArrayBuffer;
}> {
    return {
        original: imageData,
        thumbnail: await optimizeImage(imageData, { width: 300, height: 300, quality: 80 }),
        medium: await optimizeImage(imageData, { width: 800, height: 800, quality: 85 }),
        large: await optimizeImage(imageData, { width: 1920, height: 1920, quality: 90 }),
    };
}

// Validate image file
export function validateImage(file: File): { valid: boolean; error?: string } {
    const maxSize = 2 * 1024 * 1024; // 2MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

    if (!allowedTypes.includes(file.type)) {
        return { valid: false, error: 'Invalid image type. Only JPEG, PNG, WebP, and GIF are allowed.' };
    }

    if (file.size > maxSize) {
        return { valid: false, error: `Image size exceeds ${maxSize / 1024 / 1024}MB limit.` };
    }

    return { valid: true };
}

// Validate video file
export function validateVideo(file: File): { valid: boolean; error?: string } {
    const maxSize = 100 * 1024 * 1024; // 100MB (will compress to ~60MB)
    const allowedTypes = ['video/mp4', 'video/webm', 'video/quicktime'];

    if (!allowedTypes.includes(file.type)) {
        return { valid: false, error: 'Invalid video type. Only MP4, WebM, and MOV are allowed.' };
    }

    if (file.size > maxSize) {
        return { valid: false, error: `Video size exceeds ${maxSize / 1024 / 1024}MB limit.` };
    }

    return { valid: true };
}

// Generate R2 key for media
export function generateMediaKey(listingId: number, type: 'image' | 'video', index: number, variant?: string): string {
    const timestamp = Date.now();
    const variantSuffix = variant ? `_${variant}` : '';
    const folder = type === 'image' ? 'images' : 'videos';
    return `listings/${listingId}/${folder}/${timestamp}_${index}${variantSuffix}.${type === 'image' ? 'webp' : 'mp4'}`;
}

