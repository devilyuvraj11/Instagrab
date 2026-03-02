const tabs = document.querySelectorAll('.tab');
const loader = document.getElementById("status");
const errorBox = document.getElementById("errorBox");
const linkInput = document.getElementById('linkInput');
const downloadBtn = document.getElementById('downloadBtn');
const previewArea = document.getElementById('previewArea');
const videoPreview = document.getElementById('videoPreview');

let isPreviewShown = false;
let downloadedBlob = null;

/* ---------- AUTO FILL URL FROM QUERY ---------- */
const params = new URLSearchParams(window.location.search);
const sharedUrl = params.get("url");

if (sharedUrl && linkInput) {
  linkInput.value = sharedUrl;
}

/* ---------------- PLATFORM DETECT ---------------- */

function isFacebookPage(){
  return window.location.pathname.includes("facebook");
}

function isInstagramPage(){
  return !isFacebookPage();
}

function isInstagramLink(url){
  return /instagram\.com/i.test(url);
}

function isFacebookLink(url){
  return /(facebook\.com|fb\.watch)/i.test(url);
}

function getPreviewSource(){
  return isFacebookPage() ? "facebook" : "instagram";
}

function getDownloadEndpoint(){
  return isFacebookPage() ? "/facebook/download" : "/download";
}

/* ---------------- SAFE RESET ---------------- */

if (previewArea) previewArea.hidden = true;
if (videoPreview) videoPreview.src = '';
if (downloadBtn) downloadBtn.textContent = 'Download';

/* ---------------- TAB SWITCH (SAFE) ---------------- */

if (tabs.length > 0) {
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      if (previewArea) previewArea.hidden = true;
      if (videoPreview) videoPreview.src = '';
      if (loader) loader.hidden = true;
      if (errorBox) errorBox.textContent = '';

      downloadedBlob = null;
      isPreviewShown = false;
      if (downloadBtn) downloadBtn.textContent = 'Download';
    });
  });
}

/* ---------------- DOWNLOAD CLICK ---------------- */

if (downloadBtn) {
downloadBtn.addEventListener('click', async () => {

  const inputUrl = linkInput.value.trim();
  if (errorBox) errorBox.textContent = "";

  if (!inputUrl) {
    errorBox.textContent = "Enter valid link";
    return;
  }

  /* AUTO REDIRECT */
  if (isInstagramPage() && isFacebookLink(inputUrl)) {
    window.location.href = "/facebook?url=" + encodeURIComponent(inputUrl);
    return;
  }

  if (isFacebookPage() && isInstagramLink(inputUrl)) {
    window.location.href = "/instagram?url=" + encodeURIComponent(inputUrl);
    return;
  }

  /* Normalize URL */
  let cleanUrl = inputUrl;
  try {
    const u = new URL(inputUrl);
    cleanUrl = u.origin + u.pathname;
  } catch {}

  /* SECOND CLICK → DOWNLOAD */
  if (isPreviewShown && downloadedBlob) {
    triggerDownload(downloadedBlob, 'video.mp4');
    return;
  }

  loader.hidden = false;
  downloadBtn.disabled = true;

  try {
    /* ---------- PREVIEW ---------- */
    const previewRes = await fetch(
      `/preview?url=${encodeURIComponent(cleanUrl)}&source=${getPreviewSource()}`
    );

    const contentType = previewRes.headers.get("content-type");
    let previewData = null;

    if (contentType && contentType.includes("application/json")) {
      previewData = await previewRes.json();
    }

    if (!previewRes.ok || !previewData || !previewData.resolved_url) {
      throw new Error(previewData?.detail || "Enter valid link");
    }

    videoPreview.src = previewData.resolved_url;
    previewArea.hidden = false;
    isPreviewShown = true;
    downloadBtn.textContent = "Download Video";

    /* ---------- DOWNLOAD ---------- */
    const dlRes = await fetch(getDownloadEndpoint(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: cleanUrl })
    });

    if (!dlRes.ok) {
      const ct = dlRes.headers.get("content-type");
      let errMsg = "Download failed";

      if (ct && ct.includes("application/json")) {
        const err = await dlRes.json();
        errMsg = err.detail || errMsg;
      }
      throw new Error(errMsg);
    }

    downloadedBlob = await dlRes.blob();

  } catch (err) {
    errorBox.textContent = err.message || "Something went wrong";
  } finally {
    loader.hidden = true;
    downloadBtn.disabled = false;
  }
});
}

/* ---------------- DOWNLOAD FILE ---------------- */

function triggerDownload(blob, filename) {
  const a = document.createElement('a');
  const url = URL.createObjectURL(blob);
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
