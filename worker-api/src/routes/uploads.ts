/**
 * Upload routes
 * POST /api/uploads/sign - Returns signed URL or direct upload handler
 */

import { jsonResponse, errorResponse } from '../utils/response';
import type { Env, AuthenticatedRequest } from '../index';

const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_VIDEO_SIZE = 100 * 1024 * 1024; // 100MB

export async function uploadsRouter(
  request: Request,
  env: Env,
  authInfo: AuthenticatedRequest
): Promise<Response> {
  const url = new URL(request.url);
  
  try {
    // POST /api/uploads/sign - Generate signed URL for direct upload
    if (request.method === 'POST' && url.pathname === '/api/uploads/sign') {
      const body = await request.json() as any;
      const { filename, content_type, listing_id, file_type } = body;
      
      if (!filename || !content_type || !file_type) {
        return errorResponse('Missing required fields: filename, content_type, file_type', 400);
      }
      
      // Validate file type
      if (!['image', 'video'].includes(file_type)) {
        return errorResponse('Invalid file_type. Must be "image" or "video"', 400);
      }
      
      // Validate content type
      const allowedImageTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
      const allowedVideoTypes = ['video/mp4', 'video/webm', 'video/quicktime'];
      
      if (file_type === 'image' && !allowedImageTypes.includes(content_type)) {
        return errorResponse('Invalid image type. Allowed: JPEG, PNG, WebP, GIF', 400);
      }
      
      if (file_type === 'video' && !allowedVideoTypes.includes(content_type)) {
        return errorResponse('Invalid video type. Allowed: MP4, WebM, MOV', 400);
      }
      
      // Generate R2 key
      const timestamp = Date.now();
      const extension = filename.split('.').pop() || (file_type === 'image' ? 'jpg' : 'mp4');
      const r2Key = `listings/${listing_id || 'temp'}/${timestamp}_${crypto.randomUUID()}.${extension}`;
      
      // Select appropriate bucket
      const bucket = file_type === 'image' ? env.IMAGES : env.VIDEOS;
      
      // Generate presigned PUT URL
      // Note: R2 doesn't support presigned URLs directly like S3
      // For MVP, we'll return the key and handle upload via worker
      // In production, consider using R2's custom domain with direct upload
      
      const publicUrl = file_type === 'image'
        ? `https://pub-${env.IMAGES.bucketName}.r2.dev/${r2Key}`
        : `https://pub-${env.VIDEOS.bucketName}.r2.dev/${r2Key}`;
      
      return jsonResponse({
        upload_url: publicUrl, // For direct upload via worker
        r2_key: r2Key,
        method: 'PUT',
        headers: {
          'Content-Type': content_type,
        },
      });
    }
    
    // Direct upload handler (alternative approach)
    // POST /api/uploads/upload - Direct upload to R2 via worker
    if (request.method === 'POST' && url.pathname === '/api/uploads/upload') {
      const formData = await request.formData();
      const file = formData.get('file') as File | null;
      const listingId = formData.get('listing_id')?.toString();
      const fileType = formData.get('file_type')?.toString() || 'image';
      
      if (!file) {
        return errorResponse('No file provided', 400);
      }
      
      // Validate file size
      if (fileType === 'image' && file.size > MAX_IMAGE_SIZE) {
        return errorResponse(`Image size exceeds ${MAX_IMAGE_SIZE / 1024 / 1024}MB limit`, 400);
      }
      
      if (fileType === 'video' && file.size > MAX_VIDEO_SIZE) {
        return errorResponse(`Video size exceeds ${MAX_VIDEO_SIZE / 1024 / 1024}MB limit`, 400);
      }
      
      // Generate R2 key
      const timestamp = Date.now();
      const extension = file.name.split('.').pop() || (fileType === 'image' ? 'jpg' : 'mp4');
      const r2Key = `listings/${listingId || 'temp'}/${timestamp}_${crypto.randomUUID()}.${extension}`;
      
      // Upload to R2
      const bucket = fileType === 'image' ? env.IMAGES : env.VIDEOS;
      await bucket.put(r2Key, file.stream(), {
        httpMetadata: {
          contentType: file.type,
        },
        customMetadata: {
          uploadedBy: authInfo.userId || '',
          uploadedAt: timestamp.toString(),
          originalName: file.name,
        },
      });
      
      // If listing_id provided, save to database
      if (listingId && fileType === 'image') {
        // Get current max order
        const maxOrderResult = await env.DB.prepare(
          'SELECT MAX(order) as max_order FROM listing_images WHERE listing_id = ?'
        ).bind(parseInt(listingId)).first<{ max_order: number | null }>();
        
        const nextOrder = (maxOrderResult?.max_order || 0) + 1;
        
        await env.DB.prepare(`
          INSERT INTO listing_images (listing_id, r2_key, order, created_at)
          VALUES (?, ?, ?, unixepoch())
        `).bind(parseInt(listingId), r2Key, nextOrder).run();
      }
      
      const publicUrl = fileType === 'image'
        ? `https://pub-${env.IMAGES.bucketName}.r2.dev/${r2Key}`
        : `https://pub-${env.VIDEOS.bucketName}.r2.dev/${r2Key}`;
      
      return jsonResponse({
        url: publicUrl,
        r2_key: r2Key,
        size: file.size,
        type: file.type,
      });
    }
    
    return errorResponse('Not found', 404);
  } catch (error) {
    console.error('Upload route error:', error);
    return errorResponse(
      error instanceof Error ? error.message : 'Internal server error',
      500
    );
  }
}

function jsonResponse(data: any, headers: HeadersInit = {}, status: number = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  });
}

function errorResponse(message: string, status: number = 400, headers: HeadersInit = {}): Response {
  return jsonResponse({ error: message }, headers, status);
}

