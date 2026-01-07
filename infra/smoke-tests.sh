#!/bin/bash
# Smoke tests for JetSchoolUSA API
# Usage: ./smoke-tests.sh [api-url] [admin-token]

set -e

API_URL="${1:-http://localhost:8787}"
ADMIN_TOKEN="${2:-}"

echo "🧪 Running smoke tests against: ${API_URL}"
echo ""

# Test 1: Health check
echo "1️⃣  Testing health endpoint..."
HEALTH=$(curl -s "${API_URL}/api/health" || echo "ERROR")
if echo "$HEALTH" | grep -q "ok"; then
    echo "   ✅ Health check passed"
else
    echo "   ❌ Health check failed"
    exit 1
fi

# Test 2: Create listing (requires auth token)
if [ -n "$ADMIN_TOKEN" ]; then
    echo "2️⃣  Testing listing creation..."
    LISTING_RESPONSE=$(curl -s -X POST "${API_URL}/api/listings" \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "title": "Test Aircraft",
            "price": 1000000,
            "performance_profile_id": 1,
            "description": "Smoke test listing"
        }' || echo "ERROR")
    
    if echo "$LISTING_RESPONSE" | grep -q "listing"; then
        LISTING_ID=$(echo "$LISTING_RESPONSE" | jq -r '.listing.id' 2>/dev/null || echo "")
        echo "   ✅ Listing created: ID ${LISTING_ID}"
        
        # Test 3: Get listing
        echo "3️⃣  Testing get listing..."
        GET_RESPONSE=$(curl -s "${API_URL}/api/listings/${LISTING_ID}" || echo "ERROR")
        if echo "$GET_RESPONSE" | grep -q "listing"; then
            echo "   ✅ Listing retrieved"
        else
            echo "   ❌ Failed to retrieve listing"
        fi
        
        # Test 4: Upload image (if listing ID exists)
        if [ -n "$LISTING_ID" ]; then
            echo "4️⃣  Testing image upload..."
            # Create a small test image (1x1 pixel PNG)
            echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > /tmp/test.png
            
            UPLOAD_RESPONSE=$(curl -s -X POST "${API_URL}/api/uploads/upload" \
                -H "Authorization: Bearer ${ADMIN_TOKEN}" \
                -F "file=@/tmp/test.png" \
                -F "listing_id=${LISTING_ID}" \
                -F "file_type=image" || echo "ERROR")
            
            if echo "$UPLOAD_RESPONSE" | grep -q "url"; then
                echo "   ✅ Image uploaded"
            else
                echo "   ⚠️  Image upload may have failed (check response)"
            fi
            
            rm -f /tmp/test.png
        fi
        
    else
        echo "   ❌ Listing creation failed"
    fi
else
    echo "2️⃣  Skipping authenticated tests (no token provided)"
fi

# Test 5: Get listings (public)
echo "5️⃣  Testing public listings endpoint..."
LISTINGS=$(curl -s "${API_URL}/api/listings" || echo "ERROR")
if echo "$LISTINGS" | grep -q "listings"; then
    echo "   ✅ Listings endpoint working"
else
    echo "   ⚠️  Listings endpoint may have issues"
fi

echo ""
echo "✅ Smoke tests complete!"

