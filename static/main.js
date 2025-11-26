const tabs = document.querySelectorAll('.tab');
const linkInput = document.getElementById('linkInput');
const downloadBtn = document.getElementById('downloadBtn');
const statusEl = document.getElementById('status');
const previewArea = document.getElementById('previewArea');
const videoPreview = document.getElementById('videoPreview');

let selectedType = 'photo';
let lastBlob = null;
let lastResolvedUrl = '';

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
    // ensure focused input on mobile
    linkInput.focus();
  });
});

async function resolveForPreview(url) {
  try {
    const res = await fetch(`/preview?url=${encodeURIComponent(url)}`);
    if (!res.ok) {
      const err = await res.json().catch(()=>({detail:'Preview failed'}));
      statusEl.textContent = err.detail || 'Preview error';
      return null;
    }
    const json = await res.json();
    return json;
  } catch (e) {
    statusEl.textContent = 'Network error while previewing';
    return null;
  }
}

downloadBtn.addEventListener('click', async () => {
  const raw = linkInput.value.trim();
  if (!raw) { statusEl.textContent = 'Please paste a link first.'; return; }

  // normalize URL to drop query params
  let urlToSend = raw;
  try {
    const u = new URL(raw);
    urlToSend = u.origin + u.pathname;
  } catch (e) { urlToSend = raw; }

  // if we already have a blob, treat this as "download"
  if (lastBlob) {
    triggerDownload(lastBlob, 'instagram_video.mp4');
    return;
  }

  statusEl.textContent = 'Resolving preview...';
  downloadBtn.disabled = true;

  const preview = await resolveForPreview(urlToSend);
  if (!preview) { downloadBtn.disabled = false; return; }

  if (preview.resolved_url) {
    lastResolvedUrl = preview.resolved_url;
    // set video src (use direct cdn url) — this works well on most devices
    videoPreview.src = preview.resolved_url;
    previewArea.hidden = false;
    statusEl.textContent = 'Preview ready. Click Download again to save the video.';
    downloadBtn.disabled = false;

    // Background prefetch the blob (optional)
    try {
      const dlRes = await fetch('/download', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({url: urlToSend})
      });
      if (!dlRes.ok) {
        const err = await dlRes.json().catch(()=>({detail:'Download failed'}));
        statusEl.textContent = err.detail || 'Download error';
        downloadBtn.disabled = false;
        return;
      }
      const blob = await dlRes.blob();
      lastBlob = blob;
      statusEl.textContent = 'Ready to save: click Download again.';
    } catch (e) {
      console.warn('background prefetch failed', e);
    } finally {
      downloadBtn.disabled = false;
    }
  } else {
    statusEl.textContent = 'Preview not available';
    downloadBtn.disabled = false;
  }
});

function triggerDownload(blob, filename) {
  const a = document.createElement('a');
  const url = URL.createObjectURL(blob);
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),2000);
}
