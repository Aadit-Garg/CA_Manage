/**
 * Cloudinary Direct Upload Integration
 * Used in Document Upload, Replace, and Bulk Upload forms.
 */

document.addEventListener('DOMContentLoaded', () => {
    initCloudinaryUploads();
});
document.addEventListener('turbo:load', () => {
    initCloudinaryUploads();
});

async function initCloudinaryUploads() {
    const uploadBtn = document.getElementById('cloudinary-upload-btn');
    if (!uploadBtn) return;

    // Prevent double initialization
    if (uploadBtn.dataset.cloudinaryInitialized === 'true') return;
    uploadBtn.dataset.cloudinaryInitialized = 'true';

    // Fetch signature
    try {
        const response = await fetch('/api/cloudinary/signature');
        const sigData = await response.json();
        
        if (sigData.error) {
            console.error('Cloudinary signature error:', sigData.error);
            showToast('Failed to initialize uploader. Please refresh.', 'danger');
            return;
        }

        const widget = cloudinary.createUploadWidget({
            cloudName: sigData.cloud_name,
            apiKey: sigData.api_key,
            uploadSignatureTimestamp: sigData.timestamp,
            uploadSignature: sigData.signature,
            folder: sigData.folder,
            resourceType: 'raw', // Important for PDFs
            clientAllowedFormats: ['pdf'],
            maxFileSize: 25000000, // 25MB
            sources: ['local', 'google_drive'],
            multiple: uploadBtn.dataset.multiple === 'true',
            theme: 'minimal'
        }, (error, result) => {
            const isBulk = uploadBtn.dataset.multiple === 'true';

            if (!error && result && result.event === "success") {
                console.log('Upload successful:', result.info);
                
                if (!isBulk) {
                    // Single file upload
                    document.getElementById('cloudinary_url').value = result.info.secure_url;
                    document.getElementById('cloudinary_public_id').value = result.info.public_id;
                    document.getElementById('original_filename').value = result.info.original_filename + '.pdf';
                    document.getElementById('file_size').value = result.info.bytes;
                    
                    // Show success state
                    uploadBtn.innerHTML = '<i class="bi bi-check-circle-fill"></i> Uploaded: ' + result.info.original_filename;
                    uploadBtn.classList.remove('btn-outline-primary');
                    uploadBtn.classList.add('btn-success', 'text-white');
                    
                    // Auto-fill title if empty
                    const titleEl = document.getElementById('title');
                    if (titleEl && !titleEl.value) {
                        titleEl.value = result.info.original_filename;
                    }
                } else {
                    // Bulk upload (store array of results)
                    const hiddenDataEl = document.getElementById('uploaded_files_data');
                    let currentData = [];
                    if (hiddenDataEl.value) {
                        try { currentData = JSON.parse(hiddenDataEl.value); } catch(e){}
                    }
                    
                    currentData.push({
                        cloudinary_url: result.info.secure_url,
                        cloudinary_public_id: result.info.public_id,
                        original_filename: result.info.original_filename + '.pdf',
                        file_size: result.info.bytes
                    });
                    
                    hiddenDataEl.value = JSON.stringify(currentData);
                    uploadBtn.innerHTML = `<i class="bi bi-check-circle-fill"></i> ${currentData.length} Files Ready`;
                    uploadBtn.classList.remove('btn-outline-primary');
                    uploadBtn.classList.add('btn-success', 'text-white');
                }
            } else if (!error && result && result.event === "close") {
                if (isBulk && typeof window.startBulkAnalysis === 'function') {
                    const hiddenDataEl = document.getElementById('uploaded_files_data');
                    if (hiddenDataEl && hiddenDataEl.value) {
                        try {
                            const data = JSON.parse(hiddenDataEl.value);
                            if (data.length > 0) {
                                window.startBulkAnalysis(data);
                            }
                        } catch (e) { console.error('Bulk analysis error', e); }
                    }
                }
            }
        });

        uploadBtn.addEventListener('click', (e) => {
            e.preventDefault();
            widget.open();
        });

    } catch (err) {
        console.error('Failed to init Cloudinary:', err);
    }
}
