(function () {
    const SHAPES = {
        card: { label: 'Listing photo', ratio: 1, outW: 1600, outH: 1600 },
        page: { label: 'Listing photo', ratio: 1, outW: 1600, outH: 1600 }
    };

    let root = null;
    let busy = Promise.resolve();
    let session = null;

    function ensure() {
        if (root) return root;
        const style = document.createElement('style');
        style.textContent = [
            '.photo-crop { position: fixed; inset: 0; z-index: 1200; background: rgba(0,0,0,0.82); overflow: auto; color: #f4f4f4; font-family: Rajdhani, sans-serif; }',
            '.photo-crop[hidden] { display: none; }',
            '.photo-crop__sheet { max-width: 860px; margin: 1.5rem auto 2rem; padding: 1.25rem; background: #141414; border: 1px solid #2e2e2e; border-radius: 16px; }',
            '.photo-crop h2 { margin: 0 0 0.35rem; color: #fff; font-size: 1.7rem; }',
            '.photo-crop p { margin: 0 0 0.9rem; color: #d0d0d0; }',
            '.photo-crop__shapes, .photo-crop__actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }',
            '.photo-crop__shapes { margin-bottom: 0.9rem; }',
            '.photo-crop button { border: 1px solid #444; background: #1c1c1c; color: #fff; border-radius: 8px; padding: 0.45rem 0.8rem; font-weight: 700; cursor: pointer; }',
            '.photo-crop button.is-on { background: #F05545; border-color: #F05545; }',
            '.photo-crop__use { background: #F05545; border-color: #F05545; }',
            '.photo-crop__frame { position: relative; width: min(100%, 420px); aspect-ratio: 1; margin: 0 auto 0.9rem; overflow: hidden; background: #0c0c0c; border-radius: 12px; touch-action: none; cursor: grab; }',
            '.photo-crop__frame img { position: absolute; left: 0; top: 0; max-width: none; user-select: none; pointer-events: none; }',
            '.photo-crop label { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }',
            '.photo-crop input[type=range] { flex: 1; }',
            '.photo-crop__previews { display: grid; grid-template-columns: 1.4fr 1fr; gap: 0.9rem; margin-bottom: 1rem; }',
            '.photo-crop__previews strong { display: block; margin-bottom: 0.35rem; color: #fff; }',
            '.photo-crop__card, .photo-crop__hero { background: #1a1a1a; border-radius: 12px; overflow: hidden; border: 1px solid #2e2e2e; }',
            '.photo-crop__card canvas, .photo-crop__hero canvas { display: block; width: 100%; height: auto; background: #111; }',
            '.photo-crop__card p { margin: 0; padding: 0.55rem 0.7rem 0.7rem; color: #F05545; font-weight: 800; font-size: 1.15rem; }',
            '@media (max-width: 700px) { .photo-crop__previews { grid-template-columns: 1fr; } }'
        ].join('');
        document.head.appendChild(style);
        root = document.createElement('div');
        root.className = 'photo-crop';
        root.hidden = true;
        root.innerHTML = ''
            + '<div class="photo-crop__sheet">'
            + '<h2>Fit this photo</h2>'
            + '<p>Drag the photo and use the slider. Listings use a square photo, and the frames below are what people see.</p>'
            + '<div class="photo-crop__frame"><img alt=""></div>'
            + '<label>Zoom <input type="range" min="1" max="3" step="0.01" value="1"></label>'
            + '<div class="photo-crop__previews">'
            + '<div><strong>On the marketplace</strong><div class="photo-crop__card"><canvas></canvas><p>Your aircraft</p></div></div>'
            + '<div><strong>On the listing page</strong><div class="photo-crop__hero"><canvas></canvas></div></div>'
            + '</div>'
            + '<div class="photo-crop__actions">'
            + '<button type="button" class="photo-crop__use" data-crop-use>Use this photo</button>'
            + '<button type="button" data-crop-cancel>Cancel</button>'
            + '</div>'
            + '</div>';
        document.body.appendChild(root);
        root.querySelector('[data-crop-cancel]').addEventListener('click', function () { finish(null); });
        root.querySelector('[data-crop-use]').addEventListener('click', function () {
            exportPhoto().then(function (result) { finish(result); });
        });
        root.querySelector('input[type=range]').addEventListener('input', function (event) {
            if (!session) return;
            setZoom(Number(event.target.value));
        });
        const frame = root.querySelector('.photo-crop__frame');
        frame.addEventListener('pointerdown', function (event) {
            if (!session) return;
            session.drag = { x: event.clientX, y: event.clientY, ox: session.offsetX, oy: session.offsetY };
            frame.setPointerCapture(event.pointerId);
        });
        frame.addEventListener('pointermove', function (event) {
            if (!session || !session.drag) return;
            session.offsetX = session.drag.ox + (event.clientX - session.drag.x);
            session.offsetY = session.drag.oy + (event.clientY - session.drag.y);
            apply();
        });
        frame.addEventListener('pointerup', function () { if (session) session.drag = null; });
        frame.addEventListener('pointercancel', function () { if (session) session.drag = null; });
        root.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') finish(null);
        });
        return root;
    }

    function frameBox() {
        return root.querySelector('.photo-crop__frame').getBoundingClientRect();
    }

    function coverBase(box) {
        return Math.max(box.width / session.image.naturalWidth, box.height / session.image.naturalHeight);
    }

    function paintShape() {
        root.querySelector('.photo-crop__frame').style.aspectRatio = '1';
    }

    function center() {
        const box = frameBox();
        const scale = coverBase(box) * session.zoom;
        session.offsetX = (box.width - session.image.naturalWidth * scale) / 2;
        session.offsetY = (box.height - session.image.naturalHeight * scale) / 2;
    }

    function setZoom(next) {
        const box = frameBox();
        const base = coverBase(box);
        const oldScale = base * session.zoom;
        const cx = box.width / 2;
        const cy = box.height / 2;
        const ix = (cx - session.offsetX) / oldScale;
        const iy = (cy - session.offsetY) / oldScale;
        session.zoom = next;
        const scale = base * next;
        session.offsetX = cx - ix * scale;
        session.offsetY = cy - iy * scale;
        apply();
    }

    function clamp(box, scale) {
        const dw = session.image.naturalWidth * scale;
        const dh = session.image.naturalHeight * scale;
        session.offsetX = Math.min(0, Math.max(box.width - dw, session.offsetX));
        session.offsetY = Math.min(0, Math.max(box.height - dh, session.offsetY));
    }

    function cropCanvas(width, height) {
        const box = frameBox();
        const scale = coverBase(box) * session.zoom;
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#111';
        ctx.fillRect(0, 0, width, height);
        const sx = -session.offsetX / scale;
        const sy = -session.offsetY / scale;
        const sw = box.width / scale;
        const sh = box.height / scale;
        ctx.drawImage(session.image, sx, sy, sw, sh, 0, 0, width, height);
        return canvas;
    }

    function apply() {
        const box = frameBox();
        if (!box.width || !box.height) return;
        const scale = coverBase(box) * session.zoom;
        clamp(box, scale);
        const img = root.querySelector('.photo-crop__frame img');
        img.style.width = (session.image.naturalWidth * scale) + 'px';
        img.style.height = (session.image.naturalHeight * scale) + 'px';
        img.style.left = session.offsetX + 'px';
        img.style.top = session.offsetY + 'px';
        const exact = cropCanvas(480, 480);
        const card = root.querySelector('.photo-crop__card canvas');
        const hero = root.querySelector('.photo-crop__hero canvas');
        card.width = 360;
        card.height = 360;
        hero.width = 360;
        hero.height = 360;
        card.getContext('2d').drawImage(exact, 0, 0, card.width, card.height);
        hero.getContext('2d').drawImage(exact, 0, 0, hero.width, hero.height);
    }

    function exportPhoto() {
        if (!session) return Promise.resolve(null);
        const shape = SHAPES[session.shape];
        const canvas = cropCanvas(shape.outW, shape.outH);
        const sourceFile = session.sourceFile;
        return new Promise(function (resolve) {
            canvas.toBlob(function (blob) {
                if (!blob) {
                    resolve(null);
                    return;
                }
                const file = new File([blob], 'listing-photo.jpg', { type: 'image/jpeg' });
                resolve({ file: file, url: URL.createObjectURL(blob), sourceFile: sourceFile });
            }, 'image/jpeg', 0.92);
        });
    }

    function finish(result) {
        const done = session && session.resolve;
        const sourceUrl = session && session.sourceUrl;
        if (root) root.hidden = true;
        session = null;
        if (sourceUrl) URL.revokeObjectURL(sourceUrl);
        if (done) done(result || null);
    }

    function openFile(file) {
        ensure();
        return new Promise(function (resolve) {
            const url = URL.createObjectURL(file);
            const image = new Image();
            image.onload = function () {
                session = {
                    image: image,
                    sourceFile: file,
                    sourceUrl: url,
                    shape: 'card',
                    zoom: 1,
                    offsetX: 0,
                    offsetY: 0,
                    drag: null,
                    resolve: resolve
                };
                root.hidden = false;
                root.querySelector('input[type=range]').value = '1';
                root.querySelector('.photo-crop__frame img').src = url;
                paintShape();
                requestAnimationFrame(function () {
                    center();
                    apply();
                });
            };
            image.onerror = function () {
                URL.revokeObjectURL(url);
                resolve(null);
            };
            image.src = url;
        });
    }

    window.JetPhotoCrop = {
        open: function (file) {
            const run = busy.then(function () { return openFile(file); });
            busy = run.then(function () { return null; }, function () { return null; });
            return run;
        },
        openUrl: function (url) {
            return fetch(url, { credentials: 'same-origin' }).then(function (response) {
                if (!response.ok) throw new Error('photo');
                return response.blob();
            }).then(function (blob) {
                const type = blob.type && blob.type.indexOf('image/') === 0 ? blob.type : 'image/jpeg';
                return window.JetPhotoCrop.open(new File([blob], 'photo.jpg', { type: type }));
            }).catch(function () { return null; });
        }
    };
})();
