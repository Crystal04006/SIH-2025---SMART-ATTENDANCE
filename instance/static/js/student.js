document.addEventListener('DOMContentLoaded', async () => {
    // --- Universal Theme Toggle Logic ---
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        const body = document.body;
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') {
            body.classList.add('light-mode');
            themeToggle.textContent = '🌙';
        } else {
            themeToggle.textContent = '☀️';
        }

        themeToggle.addEventListener('click', () => {
            body.classList.toggle('light-mode');
            if (body.classList.contains('light-mode')) {
                localStorage.setItem('theme', 'light');
                themeToggle.textContent = '🌙';
            } else {
                localStorage.setItem('theme', 'dark');
                themeToggle.textContent = '☀️';
            }
        });
    }

    // --- AI Model Loading ---
    const MODEL_URL = 'https://cdn.jsdelivr.net/gh/justadudewhohacks/face-api.js@0.22.2/weights';
    let modelsLoaded = false;
    async function loadModels() {
        if (!modelsLoaded) {
            await Promise.all([
                faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
                faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
                faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL)
            ]);
            modelsLoaded = true;
        }
    }

    // --- FACE ENROLLMENT LOGIC ---
    const enrollButton = document.getElementById('enroll-button');
    if (enrollButton) {
        const video = document.getElementById('video');
        const statusMessage = document.getElementById('status-message');

        statusMessage.textContent = 'Loading AI models...';
        await loadModels();
        statusMessage.textContent = 'Starting camera...';

        navigator.mediaDevices.getUserMedia({ video: {} })
            .then(stream => {
                video.srcObject = stream;
                statusMessage.textContent = 'Camera started. Please position your face in the circle.';
            })
            .catch(err => {
                statusMessage.textContent = 'Error: Could not access camera. Please check permissions.';
                statusMessage.style.color = 'var(--danger)';
            });
        
        video.addEventListener('play', () => {
            setInterval(async () => {
                if(enrollButton.disabled) return;
                const detections = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions());
                if (detections) {
                    statusMessage.textContent = 'Face detected! Ready to capture.';
                    statusMessage.style.color = 'var(--accent-primary)';
                    enrollButton.style.display = 'block';
                } else {
                    statusMessage.textContent = 'No face detected. Please look at the camera.';
                    enrollButton.style.display = 'none';
                }
            }, 500);
        });

        enrollButton.addEventListener('click', async () => {
            statusMessage.textContent = 'Capturing face... Please hold still.';
            enrollButton.disabled = true;
            const detection = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceDescriptor();
            
            if (detection) {
                const descriptor = Array.from(detection.descriptor);
                fetch('/api/save-face', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ descriptor: descriptor })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        statusMessage.textContent = 'Enrollment successful! Redirecting...';
                        statusMessage.style.color = 'var(--success)';
                        setTimeout(() => { window.location.href = '/student/dashboard'; }, 2000);
                    } else {
                        statusMessage.textContent = 'Enrollment failed. Please try again.';
                        statusMessage.style.color = 'var(--danger)';
                        enrollButton.disabled = false;
                    }
                });
            } else {
                statusMessage.textContent = 'Could not capture face clearly. Please try again.';
                statusMessage.style.color = 'var(--danger)';
                enrollButton.disabled = false;
            }
        });
    }

    // --- STUDENT DASHBOARD & VERIFICATION LOGIC ---
    const scannerContainer = document.getElementById('qr-reader');
    if (scannerContainer) {
        const resultContainer = document.getElementById('scan-result');
        let lastScanTime = 0;
        let qrScanner;

        function onScanSuccess(decodedText, decodedResult) {
            const now = Date.now();
            if (now - lastScanTime < 5000) return;
            lastScanTime = now;
            
            resultContainer.textContent = 'QR Code detected. Preparing face verification...';
            qrScanner.clear();
            
            document.getElementById('qr-section').style.display = 'none';
            document.getElementById('face-verification-section').style.display = 'block';
            startFaceVerification(decodedText);
        }

        qrScanner = new Html5QrcodeScanner("qr-reader", { fps: 10, qrbox: { width: 250, height: 250 } }, false);
        qrScanner.render(onScanSuccess, () => {});

        async function startFaceVerification(qrData) {
            const verificationVideo = document.getElementById('verification-video');
            const verificationStatus = document.getElementById('verification-status');
            
            verificationStatus.textContent = 'Loading AI models...';
            await loadModels();
            verificationStatus.textContent = 'Starting camera...';

            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: {} });
                verificationVideo.srcObject = stream;

                verificationStatus.textContent = 'Getting enrolled face data...';
                const response = await fetch('/api/get-face-data');
                const data = await response.json();
                
                if (!data.descriptor) {
                    verificationStatus.textContent = 'Error: No enrolled face data found for your account.';
                    verificationStatus.style.color = 'var(--danger)';
                    return;
                }
                const enrolledDescriptor = new Float32Array(data.descriptor);
                
                verificationStatus.textContent = 'Verifying... Please look at the camera.';
                
                const verificationInterval = setInterval(async () => {
                    const detection = await faceapi.detectSingleFace(verificationVideo, new faceapi.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceDescriptor();
                    
                    if (detection) {
                        const faceMatcher = new faceapi.FaceMatcher([enrolledDescriptor]);
                        const bestMatch = faceMatcher.findBestMatch(detection.descriptor);
                        
                        if (bestMatch.label === 'person 1' && bestMatch.distance < 0.5) {
                            clearInterval(verificationInterval);
                            verificationStatus.textContent = 'Face verified! Submitting attendance...';
                            verificationStatus.style.color = 'var(--success)';
                            
                            // Send all data to the backend
                            fetch('/api/mark-attendance', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ scanned_data: qrData })
                            })
                            .then(res => res.json())
                            .then(finalData => {
                                verificationStatus.textContent = finalData.message;
                                if(finalData.success) {
                                    setTimeout(() => window.location.reload(), 2000);
                                }
                            });
                        } else {
                             verificationStatus.textContent = 'Verification Failed. Face does not match.';
                             verificationStatus.style.color = 'var(--danger)';
                        }
                    } else {
                         verificationStatus.textContent = 'Please keep your face visible in the camera.';
                    }
                }, 1000);

            } catch (err) {
                 verificationStatus.textContent = 'Error: Could not access camera.';
                 verificationStatus.style.color = 'var(--danger)';
            }
        }
    }
});

