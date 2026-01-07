import { Env } from '../index';
import { jsonResponse, errorResponse, unauthorizedResponse } from '../utils/response';
import { validateImage, validateVideo, generateMediaKey, generateImageVariants } from '../utils/media';

const MAX_IMAGE_SIZE = 2 * 1024 * 1024; // 2MB
const MAX_VIDEO_SIZE = 100 * 1024 * 1024; // 100MB (will compress to ~60MB)
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
const ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/quicktime'];

export async function uploadRouter(
    request: Request,
    env: Env,
    userId: string | null
): Promise<Response> {
    if (!userId) {
        return unauthorizedResponse();
    }

    const url = new URL(request.url);
    const method = request.method;

    try {
        // POST /api/upload/image - Upload and optimize image to R2
        if (method === 'POST' && url.pathname === '/api/upload/image') {
            const formData = await request.formData();
            const file = formData.get('file') as File | null;
            const listingId = formData.get('listing_id')?.toString();
            const index = parseInt(formData.get('index')?.toString() || '0');

            if (!file) {
                return errorResponse('No file provided');
            }

            // Validate image
            const validation = validateImage(file);
            if (!validation.valid) {
                return errorResponse(validation.error || 'Invalid image');
            }

            const listingIdNum = listingId ? parseInt(listingId) : null;

            // Read file data
            const fileData = await file.arrayBuffer();

            // Generate image variants (thumbnail, medium, large, original)
            // For MVP, we'll upload original and add optimization later
            const variants = await generateImageVariants(fileData);

            // Upload variants to R2
            const uploadedVariants: Record<string, { url: string; r2_key: string; size: number }> = {};

            // Upload original
            const originalKey = generateMediaKey(listingIdNum || 0, 'image', index);
            await env.IMAGES.put(originalKey, variants.original, {
                httpMetadata: { contentType: 'image/webp' },
                customMetadata: {
                    originalName: file.name,
                    uploadedBy: userId,
                    uploadedAt: Date.now().toString(),
                    variant: 'original',
                },
            });
            uploadedVariants.original = {
                url: `https://pub-${env.IMAGES.bucketName}.r2.dev/${originalKey}`,
                r2_key: originalKey,
                size: variants.original.byteLength,
            };

            // Upload thumbnail
            const thumbnailKey = generateMediaKey(listingIdNum || 0, 'image', index, 'thumb');
            await env.IMAGES.put(thumbnailKey, variants.thumbnail, {
                httpMetadata: { contentType: 'image/webp' },
                customMetadata: { variant: 'thumbnail' },
            });
            uploadedVariants.thumbnail = {
                url: `https://pub-${env.IMAGES.bucketName}.r2.dev/${thumbnailKey}`,
                r2_key: thumbnailKey,
                size: variants.thumbnail.byteLength,
            };

            // Upload medium
            const mediumKey = generateMediaKey(listingIdNum || 0, 'image', index, 'medium');
            await env.IMAGES.put(mediumKey, variants.medium, {
                httpMetadata: { contentType: 'image/webp' },
                customMetadata: { variant: 'medium' },
            });
            uploadedVariants.medium = {
                url: `https://pub-${env.IMAGES.bucketName}.r2.dev/${mediumKey}`,
                r2_key: mediumKey,
                size: variants.medium.byteLength,
            };

            // Upload large
            const largeKey = generateMediaKey(listingIdNum || 0, 'image', index, 'large');
            await env.IMAGES.put(largeKey, variants.large, {
                httpMetadata: { contentType: 'image/webp' },
                customMetadata: { variant: 'large' },
            });
            uploadedVariants.large = {
                url: `https://pub-${env.IMAGES.bucketName}.r2.dev/${largeKey}`,
                r2_key: largeKey,
                size: variants.large.byteLength,
            };

            // If listing_id provided, save to database
            if (listingIdNum) {
                // Get current max display_order
                const maxOrder = await env.DB.prepare(`
          SELECT MAX(display_order) as max_order FROM listing_images WHERE listing_id = ?
        `).bind(listingIdNum).first<{ max_order: number | null }>();

                // Save original URL to database (use medium for display)
                await env.DB.prepare(`
          INSERT INTO listing_images (listing_id, image_url, r2_key, display_order, created_at)
          VALUES (?, ?, ?, ?, unixepoch())
        `).bind(listingIdNum, uploadedVariants.medium.url, originalKey, (maxOrder?.max_order || 0) + 1).run();
            }

            return jsonResponse({
                variants: uploadedVariants,
                original: {
                    name: file.name,
                    size: file.size,
                    type: file.type,
                },
            });
        }

        // POST /api/upload/video - Upload video to R2
        if (method === 'POST' && url.pathname === '/api/upload/video') {
            const formData = await request.formData();
            const file = formData.get('file') as File | null;
            const listingId = formData.get('listing_id')?.toString();

            if (!file) {
                return errorResponse('No file provided');
            }

            // Validate video
            const validation = validateVideo(file);
            if (!validation.valid) {
                return errorResponse(validation.error || 'Invalid video');
            }

            const listingIdNum = listingId ? parseInt(listingId) : null;

            // For MVP, upload video as-is (compression can be added later with Cloudflare Stream)
            const videoKey = generateMediaKey(listingIdNum || 0, 'video', 0);

            // Upload to R2
            await env.VIDEOS.put(videoKey, file.stream(), {
                httpMetadata: {
                    contentType: file.type,
                },
                customMetadata: {
                    originalName: file.name,
                    uploadedBy: userId,
                    uploadedAt: Date.now().toString(),
                },
            });

            const videoUrl = `https://pub-${env.VIDEOS.bucketName}.r2.dev/${videoKey}`;

            return jsonResponse({
                url: videoUrl,
                r2_key: videoKey,
                size: file.size,
                type: file.type,
                // Note: For production, consider using Cloudflare Stream for video processing
                // and transcoding
            });
        }

        // DELETE /api/upload/image/:r2_key - Delete image from R2
        if (method === 'DELETE' && url.pathname.startsWith('/api/upload/image/')) {
            const r2Key = decodeURIComponent(url.pathname.split('/api/upload/image/')[1]);

            // Check if image belongs to a listing owned by user
            const image = await env.DB.prepare(`
        SELECT li.*, l.owner_id
        FROM listing_images li
        JOIN listings l ON li.listing_id = l.id
        WHERE li.r2_key = ?
      `).bind(r2Key).first<{ owner_id: string | null }>();

            if (image && image.owner_id !== userId) {
                return errorResponse('Forbidden', 403);
            }

            // Delete from R2
            await env.IMAGES.delete(r2Key);

            // Delete from database if exists
            if (image) {
                await env.DB.prepare('DELETE FROM listing_images WHERE r2_key = ?').bind(r2Key).run();
            }

            return jsonResponse({ message: 'Image deleted' });
        }

        return errorResponse('Method not allowed', 405);
    } catch (error) {
        console.error('Upload route error:', error);
        return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
    }
}

