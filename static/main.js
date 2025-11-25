// main.js
const tabs = document.querySelectorAll('.tab');
const linkInput = document.getElementById('linkInput');
const downloadBtn = document.getElementById('downloadBtn');
const statusEl = document.getElementById('status');
const previewArea = document.getElementById('previewArea');
const videoPreview = document.getElementById('videoPreview');

let selectedType = 'photo';
let lastBlob = null;       // store resolved blob
let lastResolvedUrl = '';  // optional header from server
let raw = linkInput.value.trim();


try {
  const u = new URL(raw);
  urlToSend = u.origin + u.pathname;
} catch (e) {
  urlToSend = raw;
}

// Update placeholder when toolbar clicked
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t=>t.classList.remove('active'));
    tab.classList.add('active');
    selectedType = tab.dataset.type;
    linkInput.placeholder = `Enter your ${selectedType} link...`;
    statusEl.textContent = '';
    previewArea.hidden = true;
    lastBlob = null;
    lastResolvedUrl = '';
  });
});

// Download button behavior:
// - First click: POST /download {url} -> receive blob -> show preview and enable download
// - Second click: if blob present, trigger client-side download
downloadBtn.addEventListener('click', async () => {
  const url = linkInput.value.trim();
  if (!url) {
    statusEl.textContent = 'Please paste a link first.';
    return;
  }

  // If we already have a resolved blob, treat click as "download file"
  if (lastBlob) {
    triggerDownload(lastBlob, 'instagram_video.mp4');
    return;
  }

  // Otherwise, try to resolve through backend
  statusEl.textContent = 'Resolving...';
  downloadBtn.disabled = true;

  try {
    // POST to backend endpoint. If your backend is on another host/port change this URL.
    const res = await fetch('/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    if (!res.ok) {
      // try to parse JSON error
      try {
        const err = await res.json();
        statusEl.textContent = err.detail || `Error: ${res.status}`;
      } catch (e) {
        statusEl.textContent = `Server error: ${res.status}`;
      }
      return;
    }

    // read blob
    const blob = await res.blob();
    lastBlob = blob;

    // attempt to use an X-Resolved-Video-URL header (backend may provide it) for streaming preview
    const resolved = res.headers.get('X-Resolved-Video-URL');
    if (resolved) {
      lastResolvedUrl = resolved;
      videoPreview.src = resolved;
    } else {
      // show object URL from blob
      const obj = URL.createObjectURL(blob);
      videoPreview.src = obj;
    }

    previewArea.hidden = false;
    statusEl.textContent = 'Preview ready. Click Download again to save the video.';
  } catch (err) {
    console.error(err);
    // If backend isn't available, show a helpful note
    statusEl.textContent = 'Network error — could not reach backend. Make sure server is running at /download';
  } finally {
    downloadBtn.disabled = false;
  }
});

// helper to download blob
function triggerDownload(blob, filename) {
  const a = document.createElement('a');
  const url = URL.createObjectURL(blob);
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // revoke after a short delay
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
