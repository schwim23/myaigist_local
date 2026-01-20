class MyAIGist {
    constructor() {
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recordingTimer = null;
        this.startTime = null;
        this.currentRecordingBlob = null;
        this.selectedSummaryLevel = 'standard'; // Default to standard
        this.selectedVoice = 'nova'; // Default voice
        this.selectedInputs = []; // Unified input system (text and files)
        this.userDocuments = []; // Track user's uploaded documents
        
        // Analytics counters
        this.questionsAsked = 0;
        this.summariesGenerated = 0;
        this.isVoiceTranscribed = false; // Track if current question was voice transcribed

        // Bind methods (extra safety against "not a function" if something rebinds context)
        this.processContent = this.processContent.bind(this);
        this.askQuestion = this.askQuestion.bind(this);
        this.uploadMultipleFiles = this.uploadMultipleFiles.bind(this);
        this.deleteDocument = this.deleteDocument.bind(this);

        this.init();
    }

    init() {
        console.log('🚀 Initializing MyAIGist...');
        
        // Track application initialization
        this.trackEvent('app_initialized', {
            user_agent: navigator.userAgent,
            screen_resolution: `${screen.width}x${screen.height}`,
            viewport_size: `${window.innerWidth}x${window.innerHeight}`,
            language: navigator.language,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            device_memory: navigator.deviceMemory || 'unknown',
            connection_type: navigator.connection?.effectiveType || 'unknown',
            has_localStorage: typeof(Storage) !== 'undefined',
            has_webAudio: !!(window.AudioContext || window.webkitAudioContext),
            has_mediaRecorder: !!window.MediaRecorder,
            has_getUserMedia: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
        });

        this.setupEventListeners();
        this.setupTabs();
        this.setupSummaryLevels();
        this.setupVoiceSelection();
        this.setupFileShelf();
        this.setupMultiFileUpload();
        this.loadUserDocuments();

        // Track engagement timing
        this.startTime = Date.now();
        this.setupEngagementTracking();

        // Debug: list methods to ensure processContent exists
        const protoMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(this));
        console.log('🧩 Methods on instance:', protoMethods);
    }

    setupEngagementTracking() {
        // Track user engagement patterns
        let engagementStartTime = Date.now();
        let isActive = true;
        
        // Track page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.trackUserEngagement('page_hidden', {
                    time_active: Date.now() - engagementStartTime
                });
                isActive = false;
            } else {
                engagementStartTime = Date.now();
                isActive = true;
                this.trackUserEngagement('page_visible');
            }
        });

        // Track user inactivity
        let inactivityTimer;
        const resetInactivityTimer = () => {
            clearTimeout(inactivityTimer);
            inactivityTimer = setTimeout(() => {
                if (isActive) {
                    this.trackUserEngagement('user_inactive', {
                        inactive_duration: 30000 // 30 seconds
                    });
                }
            }, 30000);
        };

        // Reset timer on user interactions
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, resetInactivityTimer, true);
        });

        // Track page unload
        window.addEventListener('beforeunload', () => {
            this.trackEvent('session_ended', {
                session_duration: Date.now() - this.startTime,
                total_questions_asked: this.questionsAsked || 0,
                total_summaries_generated: this.summariesGenerated || 0
            });
        });
    }

    // Google Analytics event tracking helper with enhanced parameters
    trackEvent(eventName, parameters = {}) {
        if (typeof window.gtag === 'function') {
            // Add common parameters to all events
            const enhancedParams = {
                ...parameters,
                timestamp: new Date().toISOString(),
                page_location: window.location.href,
                user_agent: navigator.userAgent.includes('Mobile') ? 'mobile' : 'desktop'
            };
            
            window.gtag('event', eventName, enhancedParams);
            console.log('📊 GA Event tracked:', eventName, enhancedParams);
        }
    }

    // Track page interactions and user engagement
    trackUserEngagement(action, details = {}) {
        this.trackEvent('user_engagement', {
            engagement_type: action,
            ...details
        });
    }

    // Track feature usage with detailed parameters
    trackFeatureUsage(feature, action, details = {}) {
        this.trackEvent('feature_usage', {
            feature_name: feature,
            action: action,
            ...details
        });
    }

    // Track errors and issues
    trackError(errorType, errorMessage, context = {}) {
        this.trackEvent('app_error', {
            error_type: errorType,
            error_message: errorMessage,
            error_context: JSON.stringify(context)
        });
    }

    setupEventListeners() {
        // Content processing
        const processBtn = document.getElementById('process-btn');
        if (processBtn) {
            processBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.processContent();
            });
        }

        // Q&A
        const askBtn = document.getElementById('ask-btn');
        if (askBtn) {
            askBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.askQuestion();
            });
        }

        // Microphone button
        const micBtn = document.getElementById('mic-btn');
        if (micBtn) {
            micBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('🎤 Mic button clicked, isRecording:', this.isRecording);
                this.toggleRecording();
            });
        }

        // Transcribe recorded audio
        const transcribeBtn = document.getElementById('transcribe-btn');
        if (transcribeBtn) {
            transcribeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.transcribeRecording();
            });
        }

        // Re-record button
        const rerecordBtn = document.getElementById('re-record-btn');
        if (rerecordBtn) {
            rerecordBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.startNewRecording();
            });
        }

        // Enter key for questions
        const questionInput = document.getElementById('question-text');
        if (questionInput) {
            questionInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.askQuestion();
                }
            });
        }

        // ✅ Unified input system handling
        const addTextBtn = document.getElementById('add-text-btn');
        if (addTextBtn) {
            addTextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showTextInputModal();
            });
        }

        const addUrlBtn = document.getElementById('add-url-btn');
        if (addUrlBtn) {
            addUrlBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showUrlInputModal();
            });
        }

        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileSelection(Array.from(e.target.files));
                e.target.value = ''; // Reset input for re-selection
            });
        }

        const mediaInput = document.getElementById('media-input');
        if (mediaInput) {
            mediaInput.addEventListener('change', (e) => {
                this.handleMediaSelection(Array.from(e.target.files));
                e.target.value = ''; // Reset input for re-selection
            });
        }

        // Summary action buttons
        const copySummaryBtn = document.getElementById('copy-summary-btn');
        if (copySummaryBtn) {
            copySummaryBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.copySummaryToClipboard();
            });
        }

        const emailSummaryBtn = document.getElementById('email-summary-btn');
        if (emailSummaryBtn) {
            emailSummaryBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.emailSummary();
            });
        }
    }

    setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabPanels = document.querySelectorAll('.tab-panel');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.dataset.tab;

                tabBtns.forEach(b => b.classList.remove('active'));
                tabPanels.forEach(p => p.classList.remove('active'));

                btn.classList.add('active');
                const panel = document.getElementById(`${tabName}-tab`);
                if (panel) panel.classList.add('active');
            });
        });
    }

    setupSummaryLevels() {
        const summaryBtns = document.querySelectorAll('.summary-btn');

        summaryBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const level = btn.dataset.level;
                console.log('📋 Summary level selected:', level);

                // Update selected level
                this.selectedSummaryLevel = level;

                // Update UI
                summaryBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const levelNames = { quick: 'Quick', standard: 'Standard', detailed: 'Detailed' };
                this.showStatus(`Summary level set to: ${levelNames[level]}`, 'success');
            });
        });
    }

    setupVoiceSelection() {
        const voiceSelect = document.getElementById('voice-select');
        if (voiceSelect) {
            voiceSelect.addEventListener('change', () => {
                this.selectedVoice = voiceSelect.value;
                console.log('🔊 Voice selected:', this.selectedVoice);
            });
        }
    }

    // ===== Recording methods (unchanged) =====
    async toggleRecording() {
        console.log('🔄 Toggle recording called, current state:', this.isRecording);
        if (this.isRecording) this.stopRecording();
        else await this.startRecording();
    }

    async startRecording() {
        console.log('▶️ Starting recording...');
        this.recordingStartTime = Date.now();
        
        // Track recording initiation
        this.trackFeatureUsage('voice_recording', 'started', {
            device_type: navigator.userAgent.includes('Mobile') ? 'mobile' : 'desktop'
        });
        
        try {
            this.hidePlaybackSection();

            // Check if we're on HTTPS or localhost (required for getUserMedia)
            const isSecureContext = window.isSecureContext || location.protocol === 'https:' || location.hostname === 'localhost';
            if (!isSecureContext) {
                throw new Error('Microphone recording requires HTTPS connection. Please use HTTPS or localhost.');
            }

            // Check if getUserMedia is available
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Microphone recording is not supported in this browser.');
            }

            console.log('🎤 Requesting microphone access...');
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { sampleRate: 44100, channelCount: 1, echoCancellation: true, noiseSuppression: true }
            });
            console.log('✅ Microphone access granted');

            this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });

            this.audioChunks = [];
            this.startTime = Date.now();

            this.mediaRecorder.ondataavailable = (event) => {
                console.log('📦 Audio data available:', event.data.size, 'bytes');
                if (event.data.size > 0) this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = () => {
                console.log('⏹️ MediaRecorder stopped');
                this.handleRecordingStop(stream);
            };

            this.mediaRecorder.onerror = (event) => {
                console.error('❌ MediaRecorder error:', event.error);
                this.showStatus('Recording error: ' + event.error, 'error');
                this.resetRecordingState();
            };

            this.mediaRecorder.start(1000);
            this.isRecording = true;

            this.updateMicButton();
            this.showRecordingStatus();
            this.startTimer();

            console.log('✅ Recording started successfully');

        } catch (error) {
            console.error('❌ Error starting recording:', error);
            let errorMessage = 'Could not access microphone. ';
            
            if (error.message.includes('HTTPS')) {
                errorMessage = '🔒 Microphone recording requires a secure HTTPS connection. Please use HTTPS or localhost to access this feature.';
            } else if (error.name === 'NotAllowedError') {
                errorMessage += 'Please allow microphone access and try again.';
            } else if (error.name === 'NotFoundError') {
                errorMessage += 'No microphone found.';
            } else if (error.message.includes('not supported')) {
                errorMessage = 'Microphone recording is not supported in this browser.';
            } else {
                errorMessage += error.message;
            }

            this.showStatus(errorMessage, 'error');
            this.resetRecordingState();
        }
    }

    stopRecording() {
        console.log('⏹️ Stopping recording...');
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') this.mediaRecorder.stop();
        this.isRecording = false;
        this.updateMicButton();
        this.hideRecordingStatus();
        
        // Track recording completion
        const recordingDuration = this.recordingStartTime ? Date.now() - this.recordingStartTime : 0;
        this.trackFeatureUsage('voice_recording', 'stopped', {
            recording_duration: recordingDuration,
            recording_length_category: recordingDuration < 10000 ? 'short' : recordingDuration < 30000 ? 'medium' : 'long'
        });
        this.stopTimer();
    }

    handleRecordingStop(stream) {
        console.log('🎬 Handling recording stop...');
        stream.getTracks().forEach(track => track.stop());

        if (this.audioChunks.length === 0) {
            console.warn('⚠️ No audio chunks recorded');
            this.showStatus('No audio was recorded. Please try again.', 'error');
            this.resetRecordingState();
            return;
        }

        this.currentRecordingBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        console.log('📦 Created audio blob:', this.currentRecordingBlob.size, 'bytes');

        if (this.currentRecordingBlob.size === 0) {
            console.warn('⚠️ Empty audio blob');
            this.showStatus('Recording was empty. Please try again.', 'error');
            this.resetRecordingState();
            return;
        }

        this.showPlaybackSection();
        this.resetRecordingState();
        console.log('✅ Recording completed successfully');
    }

    showPlaybackSection() {
        const playbackSection = document.getElementById('playback-section');
        const audioElement = document.getElementById('recorded-audio');

        if (this.currentRecordingBlob) {
            const audioUrl = URL.createObjectURL(this.currentRecordingBlob);
            audioElement.src = audioUrl;
            playbackSection.classList.remove('hidden');
            console.log('🎵 Showing playback section');
        }
    }

    hidePlaybackSection() {
        const playbackSection = document.getElementById('playback-section');
        const audioElement = document.getElementById('recorded-audio');

        if (audioElement.src) {
            URL.revokeObjectURL(audioElement.src);
            audioElement.src = '';
        }

        playbackSection.classList.add('hidden');
        this.currentRecordingBlob = null;
        console.log('🚫 Hidden playback section');
    }

    updateMicButton() {
        const micBtn = document.getElementById('mic-btn');
        if (!micBtn) return;
        const micText = micBtn.querySelector('.mic-text');

        if (this.isRecording) {
            micBtn.classList.add('recording');
            if (micText) micText.textContent = 'Stop';
            micBtn.title = 'Click to stop recording';
        } else {
            micBtn.classList.remove('recording');
            if (micText) micText.textContent = 'Speak';
            micBtn.title = 'Click to start recording';
        }
    }

    showRecordingStatus() {
        const el = document.getElementById('recording-status');
        if (el) el.classList.remove('hidden');
    }

    hideRecordingStatus() {
        const el = document.getElementById('recording-status');
        if (el) el.classList.add('hidden');
    }

    startTimer() {
        const timerElement = document.querySelector('.recording-timer');
        this.recordingTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            if (timerElement) timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    stopTimer() {
        if (this.recordingTimer) {
            clearInterval(this.recordingTimer);
            this.recordingTimer = null;
        }
    }

    resetRecordingState() {
        this.isRecording = false;
        this.updateMicButton();
        this.hideRecordingStatus();
        this.stopTimer();
    }

    startNewRecording() {
        this.hidePlaybackSection();
        this.startRecording();
    }

    async transcribeRecording() {
        if (!this.currentRecordingBlob) {
            this.showStatus('No recording available to transcribe', 'error');
            this.trackError('voice_transcription_error', 'No recording available');
            return;
        }

        console.log('📝 Starting transcription...');
        const transcriptionStartTime = Date.now();

        try {
            this.showStatus('Transcribing your question...', 'loading');

            const formData = new FormData();
            formData.append('file', this.currentRecordingBlob, 'question.webm');

            const response = await fetch('/api/transcribe-audio', {
                method: 'POST',
                body: formData
            });

            console.log('📡 Transcription response status:', response.status);

            if (!response.ok) {
                let errorMessage = `Transcription failed (${response.status})`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (_) {}
                throw new Error(errorMessage);
            }

            const result = await response.json();

            if (result.success && result.text) {
                const q = document.getElementById('question-text');
                if (q) q.value = result.text;
                this.hidePlaybackSection();
                this.showStatus('✅ Question transcribed! You can edit it or ask directly.', 'success');
                console.log('✅ Transcription successful:', result.text);
                
                // Mark that this question was voice transcribed for later analytics
                this.isVoiceTranscribed = true;
                
                // Track successful transcription
                this.trackEvent('voice_transcribed', {
                    transcription_duration: Date.now() - transcriptionStartTime,
                    transcribed_text_length: result.text.length,
                    recording_size_bytes: this.currentRecordingBlob.size,
                    transcription_quality: result.text.length > 20 ? 'good' : 'short'
                });
                
                this.trackFeatureUsage('voice_transcription', 'success', {
                    text_length: result.text.length
                });
            } else {
                throw new Error(result.error || 'Transcription failed');
            }

        } catch (error) {
            console.error('❌ Transcription error:', error);
            this.showStatus('Transcription failed: ' + error.message, 'error');
            
            // Track transcription errors
            this.trackError('voice_transcription_error', error.message, {
                transcription_duration: Date.now() - transcriptionStartTime,
                recording_size_bytes: this.currentRecordingBlob ? this.currentRecordingBlob.size : 0
            });
        }
    }

    // ===== Content processing =====
    async processContent() {
        // Check if we have inputs
        if (!this.selectedInputs?.length) {
            this.showStatus('❌ Please add some content to analyze', 'error');
            this.trackError('validation_error', 'No content provided for processing');
            return;
        }

        // Track content processing initiation
        const startTime = Date.now();
        const textInputs = this.selectedInputs.filter(input => input.type === 'text');
        const fileInputs = this.selectedInputs.filter(input => input.type === 'file');
        const mediaInputs = this.selectedInputs.filter(input => input.type === 'media');
        const urlInputs = this.selectedInputs.filter(input => input.type === 'url');

        this.trackFeatureUsage('content_processing', 'started', {
            total_inputs: this.selectedInputs.length,
            text_inputs: textInputs.length,
            file_inputs: fileInputs.length,
            media_inputs: mediaInputs.length,
            url_inputs: urlInputs.length,
            summary_level: this.selectedSummaryLevel,
            voice_selected: this.selectedVoice,
            processing_type: this.selectedInputs.length > 1 || fileInputs.length > 0 || mediaInputs.length > 0 || urlInputs.length > 0 ? 'multi_input' : 'single_text'
        });

        const processBtn = document.getElementById('process-btn');
        if (processBtn) {
            processBtn.disabled = true;
            processBtn.innerHTML = '<span class="loading-spinner"></span> Processing...';
        }

        try {
            // If we have multiple inputs or any files or media or URLs, use multi-input processing
            if (this.selectedInputs.length > 1 || fileInputs.length > 0 || mediaInputs.length > 0 || urlInputs.length > 0) {
                return await this.processMultipleInputs();
            }

            // Single text input - use simple text processing
            if (textInputs.length === 1) {
                const requestData = {
                    type: 'text', 
                    text: textInputs[0].content,
                    summary_level: this.selectedSummaryLevel,
                    voice: this.selectedVoice
                };
                
                return this.processSingleContent(requestData, false);
            }

        } catch (error) {
            console.error('❌ Process content error:', error);
            this.showStatus(error.message, 'error');
            
            // Track processing error
            this.trackError('content_processing_error', error.message, {
                total_inputs: this.selectedInputs.length,
                summary_level: this.selectedSummaryLevel,
                processing_duration: Date.now() - startTime
            });
        } finally {
            if (processBtn) {
                processBtn.disabled = false;
                processBtn.innerHTML = '🚀 Analyze Content';
            }
            
            // Track processing completion
            this.trackFeatureUsage('content_processing', 'completed', {
                processing_duration: Date.now() - startTime
            });
        }
    }

    async processSingleContent(requestData, isFormData) {
        const levelNames = { quick: 'Quick', standard: 'Standard', detailed: 'Detailed' };
        this.showStatus(`Processing your content with ${levelNames[this.selectedSummaryLevel]} summary...`, 'loading');

        const response = await fetch('/api/process-content', {
            method: 'POST',
            ...(!isFormData && {
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(requestData)
            }),
            ...(isFormData && { body: requestData })
        });

        if (!response.ok) {
            const raw = await response.text();
            let msg = `Processing failed (${response.status})`;
            try {
                const err = JSON.parse(raw);
                msg = err.error || msg;
            } catch (_) {
                msg = `${msg}: ${raw}`;
            }
            throw new Error(msg);
        }

        const result = await response.json();

        if (result.success) {
            // Increment counter
            this.summariesGenerated++;
            
            // Track successful summary generation
            this.trackEvent('content_summarized', {
                content_type: 'single_text',
                summary_level: this.selectedSummaryLevel,
                text_length: requestData.text ? requestData.text.length : 0,
                summary_length: result.summary ? result.summary.length : 0,
                has_qa_stored: result.qa_stored || false,
                embedding_stats: result.embedding_stats || null,
                summary_number: this.summariesGenerated
            });

            // Phase 1: Show summary immediately
            this.showSummary(result.summary, null, this.selectedSummaryLevel);
            this.showQASection();
            this.showStatus(`Content processed successfully! You can now ask questions.`, 'success');
            
            // Phase 2: Generate audio in background
            if (result.summary && result.summary.trim().length > 10) {
                setTimeout(async () => {
                    try {
                        const audioLoading = document.getElementById('audio-loading');
                        if (audioLoading) audioLoading.classList.remove('hidden');
                        await this.generateAudioInBackground(result.summary, this.selectedVoice);
                    } catch (audioError) {
                        console.error('❌ Audio generation failed:', audioError);
                        const audioLoading = document.getElementById('audio-loading');
                        if (audioLoading) {
                            audioLoading.classList.add('hidden');
                            audioLoading.style.display = 'none';
                        }
                    }
                }, 1000);
            }

            // Clear inputs and refresh
            this.clearAllInputs();
            if (result.qa_stored) {
                setTimeout(() => this.loadUserDocuments(), 1000);
            }
        } else {
            throw new Error(result.error || 'Processing failed');
        }
    }

    async processMultipleInputs() {
        // Use the existing multi-file upload logic but adapted for mixed inputs
        console.log('📁 Processing multiple inputs...');
        
        const formData = new FormData();
        const textInputs = this.selectedInputs.filter(input => input.type === 'text');
        const fileInputs = this.selectedInputs.filter(input => input.type === 'file');
        const mediaInputs = this.selectedInputs.filter(input => input.type === 'media');
        const urlInputs = this.selectedInputs.filter(input => input.type === 'url');
        
        // Add regular files
        fileInputs.forEach((input, index) => {
            formData.append('files', input.file);
        });
        
        // Add media files (separate field for backend processing)
        mediaInputs.forEach((input, index) => {
            formData.append('media_files', input.file);
        });
        
        // Add text entries as "virtual files"
        textInputs.forEach((input, index) => {
            const textBlob = new Blob([input.content], { type: 'text/plain' });
            const textFile = new File([textBlob], `${input.title}.txt`, { type: 'text/plain' });
            formData.append('files', textFile);
        });
        
        // Add URLs as separate parameter
        urlInputs.forEach((input, index) => {
            formData.append('urls', input.url);
        });
        
        formData.append('summary_level', this.selectedSummaryLevel);
        formData.append('voice', this.selectedVoice);
        
        const levelNames = { quick: 'Quick', standard: 'Standard', detailed: 'Detailed' };
        this.showStatus(`Processing ${this.selectedInputs.length} input(s) with ${levelNames[this.selectedSummaryLevel]} summary...`, 'loading');

        const response = await fetch('/api/upload-multiple-files', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const raw = await response.text();
            let msg = `Multi-input processing failed (${response.status})`;
            try {
                const err = JSON.parse(raw);
                msg = err.error || msg;
            } catch (_) {
                msg = `${msg}: ${raw}`;
            }
            throw new Error(msg);
        }

        const data = await response.json();
        console.log('✅ Multi-input response:', data);

        if (data.success) {
            // Phase 1: Show summary immediately
            const summaryText = data.combined_summary || 'Content processed successfully';
            this.showSummary(summaryText, null, this.selectedSummaryLevel);
            this.showQASection();
            await this.loadUserDocuments();

            // Increment counter
            this.summariesGenerated++;
            
            // Track detailed multi-input success
            this.trackEvent('multi_content_summarized', {
                total_inputs: this.selectedInputs.length,
                text_inputs: textInputs.length,
                file_inputs: fileInputs.length,
                media_inputs: mediaInputs.length,
                url_inputs: urlInputs.length,
                summary_level: this.selectedSummaryLevel,
                successful_uploads: data.successful_uploads || 0,
                total_files: data.total_files || 0,
                total_media: data.total_media || 0,
                total_urls: data.total_urls || 0,
                combined_summary_length: summaryText.length,
                has_failures: data.results ? data.results.some(r => !r.success) : false,
                summary_number: this.summariesGenerated,
                processing_details: data.results ? {
                    successful_items: data.results.filter(r => r.success).length,
                    failed_items: data.results.filter(r => !r.success).length,
                    file_types: data.results.filter(r => r.type === 'file' && r.success).map(r => r.filename?.split('.').pop()).filter(Boolean),
                    media_types: data.results.filter(r => r.type === 'media' && r.success).map(r => r.media_type).filter(Boolean),
                    avg_text_length: data.results.filter(r => r.success && r.text_length).reduce((sum, r) => sum + r.text_length, 0) / Math.max(1, data.results.filter(r => r.success && r.text_length).length)
                } : null
            });
            
            this.showStatus(`Successfully analyzed ${this.selectedInputs.length} input(s)!`, 'success');
            
            // Phase 2: Generate audio in background
            if (summaryText && summaryText.trim().length > 10) {
                setTimeout(async () => {
                    try {
                        const audioLoading = document.getElementById('audio-loading');
                        if (audioLoading) audioLoading.classList.remove('hidden');
                        await this.generateAudioInBackground(summaryText, data.voice || this.selectedVoice);
                    } catch (audioError) {
                        console.error('❌ Audio generation failed:', audioError);
                        const audioLoading = document.getElementById('audio-loading');
                        if (audioLoading) {
                            audioLoading.classList.add('hidden');
                            audioLoading.style.display = 'none';
                        }
                    }
                }, 1000);
            }
            
            // Clear inputs
            this.clearAllInputs();
        } else {
            // Show more detailed error information
            const errorMsg = data.error || 'Processing failed';
            console.error('❌ Processing failed:', data);
            
            // If there are results with errors, show them
            if (data.results && data.results.length > 0) {
                const failedResults = data.results.filter(r => !r.success);
                if (failedResults.length > 0) {
                    const errorDetails = failedResults.map(r => `${r.filename || r.url || 'Input'}: ${r.error}`).join('; ');
                    throw new Error(`Processing failed: ${errorDetails}`);
                }
            }
            
            throw new Error(errorMsg);
        }
    }

    clearAllInputs() {
        this.selectedInputs = [];
        this.updateInputDisplay();
        
        // Also clear HTML input elements
        const fileInput = document.getElementById('file-input');
        const mediaInput = document.getElementById('media-input');
        if (fileInput) fileInput.value = '';
        if (mediaInput) mediaInput.value = '';
    }

    async askQuestion() {
        const questionText = document.getElementById('question-text')?.value?.trim() || '';
        const askBtn = document.getElementById('ask-btn');
        const startTime = Date.now();

        console.log('🔍 =========================');
        console.log('🔍 DEBUG: askQuestion called');
        console.log('🔍 Question text:', questionText);
        console.log('🔍 Question length:', questionText.length);
        console.log('🔍 =========================');

        if (!questionText) {
            this.showStatus('Please enter a question or record one using the microphone', 'error');
            this.trackError('validation_error', 'No question provided for Q&A');
            return;
        }

        // Track Q&A initiation
        this.trackFeatureUsage('qa_system', 'question_started', {
            question_length: questionText.length,
            question_type: this.isVoiceTranscribed ? 'voice' : 'text',
            has_context: this.userDocuments.length > 0
        });

        if (askBtn) {
            askBtn.disabled = true;
            askBtn.innerHTML = '<span class="loading-spinner"></span> Thinking...';
        }

        try {
            // (same logic as your original for QA readiness + ask flow)
            const response = await fetch('/api/ask-question', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ question: questionText, voice: this.selectedVoice }),
                credentials: 'include'  // Include session cookies
            });

            if (!response.ok) {
                const txt = await response.text();
                let msg = `Request failed with status ${response.status}`;
                try {
                    const err = JSON.parse(txt);
                    msg = err.error || msg;
                } catch (_) {
                    msg = `Server error (${response.status}): ${txt}`;
                }
                throw new Error(msg);
            }

            const result = await response.json();
            if (result.success && result.answer) {
                this.showAnswer(result.answer, result.audio_url);
                
                // Increment counter
                this.questionsAsked++;
                
                // Track detailed Q&A success
                this.trackEvent('question_answered', {
                    question_length: questionText.length,
                    answer_length: result.answer.length,
                    has_audio_response: !!result.audio_url,
                    question_type: this.isVoiceTranscribed ? 'voice' : 'text',
                    response_time: Date.now() - startTime,
                    context_documents: this.userDocuments.length,
                    sources_found: result.sources ? result.sources.length : 0,
                    similarity_scores: result.sources ? result.sources.map(s => s.similarity) : [],
                    question_number: this.questionsAsked
                });

                // Track Q&A feature usage
                this.trackFeatureUsage('qa_system', 'answer_generated', {
                    response_time: Date.now() - startTime,
                    answer_quality: result.answer.length > 50 ? 'detailed' : 'brief'
                });

                const q = document.getElementById('question-text');
                if (q) q.value = '';
                this.showStatus('✅ Question answered successfully!', 'success');
                this.isVoiceTranscribed = false; // Reset voice flag
            } else {
                throw new Error(result.error || 'No answer received');
            }

        } catch (error) {
            console.error('❌ COMPLETE ERROR DETAILS:', error);
            this.showStatus(`❌ ${error.message}`, 'error');
            
            // Track Q&A errors
            this.trackError('qa_error', error.message, {
                question_length: questionText.length,
                question_type: this.isVoiceTranscribed ? 'voice' : 'text',
                response_time: Date.now() - startTime,
                context_documents: this.userDocuments.length
            });
        } finally {
            if (askBtn) {
                askBtn.disabled = false;
                askBtn.innerHTML = 'Ask Question';
            }
            
            // Track Q&A completion
            this.trackFeatureUsage('qa_system', 'completed', {
                total_time: Date.now() - startTime
            });
            
            console.log('🔍 ========================= END DEBUG =========================');
        }
    }

    showSummary(summary, audioUrl, level) {
        const summarySection = document.getElementById('summary-section');
        const summaryText = document.getElementById('summary-text');
        const summaryAudio = document.getElementById('summary-audio');
        const audioLoading = document.getElementById('audio-loading');
        const levelBadge = document.getElementById('summary-level-indicator');

        if (summaryText) summaryText.textContent = summary;
        
        // Handle audio URL - show/hide audio element based on availability
        if (summaryAudio) {
            if (audioUrl) {
                summaryAudio.src = audioUrl;
                summaryAudio.style.display = 'block';
            } else {
                summaryAudio.style.display = 'none';
            }
        }
        
        // Hide audio loading indicator when audio URL is provided
        if (audioLoading) {
            if (audioUrl) {
                audioLoading.classList.add('hidden');
            } else {
                audioLoading.classList.add('hidden'); // Initially hidden, will be shown when audio generation starts
            }
        }

        const levelNames = { quick: 'Quick', standard: 'Standard', detailed: 'Detailed' };
        if (levelBadge) levelBadge.textContent = levelNames[level] || 'Standard';

        // Show action buttons when summary is available
        const summaryActions = document.getElementById('summary-actions');
        if (summaryActions && summary && summary.trim()) {
            summaryActions.classList.remove('hidden');
        }

        if (summarySection) summarySection.classList.remove('hidden');
    }

    showAnswer(answer, audioUrl) {
        const answerText = document.getElementById('answer-text');
        const answerAudio = document.getElementById('answer-audio');

        if (answerText) answerText.textContent = answer;
        if (audioUrl && answerAudio) answerAudio.src = audioUrl;

        const ans = document.getElementById('answer-section');
        if (ans) ans.scrollIntoView({ behavior: 'smooth' });
    }

    showQASection() {
        const el = document.getElementById('qa-section');
        if (el) el.classList.remove('hidden');
    }

    showStatus(message, type) {
        const statusEl = document.getElementById('status');
        if (!statusEl) return;
        statusEl.textContent = message;
        statusEl.className = `status ${type}`;
        statusEl.classList.remove('hidden');

        if (type !== 'loading') {
            setTimeout(() => statusEl.classList.add('hidden'), 5000);
        }
    }

    // File Shelf Management
    setupFileShelf() {
        const shelfToggle = document.getElementById('shelf-toggle');
        const fileShelf = document.getElementById('file-shelf');
        
        if (shelfToggle && fileShelf) {
            shelfToggle.addEventListener('click', () => {
                fileShelf.classList.toggle('minimized');
                shelfToggle.textContent = fileShelf.classList.contains('minimized') ? '▶' : '◀';
            });
        }
    }

    async loadUserDocuments() {
        try {
            const response = await fetch('/api/user-documents');
            const data = await response.json();
            
            if (data.documents) {
                this.userDocuments = data.documents;
                this.updateFileShelf();
            }
        } catch (error) {
            console.error('❌ Error loading user documents:', error);
        }
    }

    updateFileShelf() {
        const fileList = document.getElementById('file-list');
        const fileCountBadge = document.getElementById('file-count-badge');
        
        if (!fileList || !fileCountBadge) return;

        fileCountBadge.textContent = this.userDocuments.length;

        if (this.userDocuments.length === 0) {
            fileList.innerHTML = '<li class="no-files-message">No documents uploaded yet</li>';
            return;
        }

        fileList.innerHTML = this.userDocuments.map(doc => {
            // Determine document type and icon
            const isTextEntry = doc.title.startsWith('Text Entry');
            const docIcon = isTextEntry ? '📝' : '📄';
            const docType = isTextEntry ? 'Text' : 'File';
            
            // Format date nicely
            const uploadDate = new Date(doc.upload_time);
            const formattedDate = uploadDate.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            return `
                <li class="file-item" data-doc-id="${doc.doc_id}">
                    <div class="file-info">
                        <div class="file-name">
                            ${docIcon} ${doc.title}
                        </div>
                        <div class="file-meta">
                            ${docType} • ${formattedDate} • ${doc.chunk_count} chunks
                        </div>
                    </div>
                    <button class="file-delete" onclick="window.myAIGist.deleteDocument('${doc.doc_id}')" title="Delete document">
                        ×
                    </button>
                </li>
            `;
        }).join('');
    }

    async deleteDocument(docId) {
        if (!confirm('Are you sure you want to delete this document?')) {
            return;
        }

        try {
            this.showStatus('Deleting document...', 'loading');
            
            const response = await fetch('/api/delete-document', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ doc_id: docId })
            });

            const data = await response.json();

            if (data.success) {
                this.showStatus('Document deleted successfully!', 'success');
                // Remove from local array
                this.userDocuments = this.userDocuments.filter(doc => doc.doc_id !== docId);
                this.updateFileShelf();
                
                // Track deletion event
                this.trackEvent('document_deleted', {
                    doc_id: docId,
                    chunks_removed: data.chunks_removed
                });
            } else {
                throw new Error(data.error || 'Failed to delete document');
            }
        } catch (error) {
            console.error('❌ Delete document error:', error);
            this.showStatus(`Error: ${error.message}`, 'error');
        }
    }

    // File Upload Setup (unified for single or multiple files)
    setupMultiFileUpload() {
        // The file input change handler is now in setupEventListeners()
        // This method is kept for compatibility but doesn't need to do anything
        console.log('✅ File upload system initialized (unified single/multi)');
    }

    // Old methods removed - using unified input system

    async uploadMultipleFiles() {
        try {
            console.log('🚀 Starting multi-file upload...');
            console.log('📁 Selected files:', this.selectedFiles.map(f => f.name));

            if (this.selectedFiles.length === 0) {
                this.showStatus('Please select files first', 'error');
                return false; // Return false to indicate failure
            }

            if (this.selectedFiles.length > 5) {
                this.showStatus('Maximum 5 files allowed', 'error');
                return false;
            }

            // Validate file sizes and types
            for (const file of this.selectedFiles) {
                if (file.size > 50 * 1024 * 1024) { // 50MB limit
                    this.showStatus(`File "${file.name}" is too large (max 50MB)`, 'error');
                    return false;
                }
                
                const allowedTypes = ['.pdf', '.docx', '.txt'];
                const hasValidExtension = allowedTypes.some(ext => 
                    file.name.toLowerCase().endsWith(ext)
                );
                
                if (!hasValidExtension) {
                    this.showStatus(`File "${file.name}" has unsupported format. Allowed: PDF, DOCX, TXT`, 'error');
                    return false;
                }
            }

            this.showStatus(`Processing ${this.selectedFiles.length} document${this.selectedFiles.length > 1 ? 's' : ''}...`, 'loading');

            const formData = new FormData();
            this.selectedFiles.forEach(file => {
                console.log(`📄 Adding file: ${file.name} (${file.size} bytes)`);
                formData.append('files', file);
            });
            formData.append('summary_level', this.selectedSummaryLevel);
            formData.append('voice', this.selectedVoice);

            console.log('📡 Sending multi-file analysis request...');
            
            const response = await fetch('/api/upload-multiple-files', {
                method: 'POST',
                body: formData
            });

            console.log('📡 Response status:', response.status);

            if (!response.ok) {
                let errorDetails = `HTTP ${response.status} ${response.statusText}`;
                
                // Handle specific error types
                if (response.status === 504) {
                    errorDetails = 'Analysis timed out. The files may be too large or the server is busy. Please try with fewer or smaller files.';
                } else if (response.status >= 500) {
                    errorDetails = 'Server error occurred. Please try again in a moment.';
                } else {
                    // Try to get more detailed error info for 4xx errors
                    try {
                        const errorText = await response.text();
                        
                        // Only try JSON parsing if the response looks like JSON
                        if (errorText.trim().startsWith('{') || errorText.trim().startsWith('[')) {
                            try {
                                const errorData = JSON.parse(errorText);
                                errorDetails = errorData.error || errorData.message || errorDetails;
                            } catch (parseError) {
                                console.warn('⚠️ Could not parse error response as JSON, using raw text');
                                // Use a clean excerpt of the HTML error if it's HTML
                                if (errorText.includes('<title>') && errorText.includes('</title>')) {
                                    const titleMatch = errorText.match(/<title>(.*?)<\/title>/);
                                    errorDetails = titleMatch ? titleMatch[1] : errorDetails;
                                } else {
                                    errorDetails = errorText.substring(0, 200) + (errorText.length > 200 ? '...' : '');
                                }
                            }
                        } else if (errorText.includes('<title>') && errorText.includes('</title>')) {
                            // Extract title from HTML error pages
                            const titleMatch = errorText.match(/<title>(.*?)<\/title>/);
                            errorDetails = titleMatch ? titleMatch[1] : errorDetails;
                        } else {
                            // Use a clean excerpt for other response types
                            errorDetails = errorText.substring(0, 200) + (errorText.length > 200 ? '...' : '');
                        }
                    } catch (readError) {
                        console.warn('⚠️ Could not read error response:', readError.message);
                        // Keep the default HTTP status message
                    }
                }
                
                console.error('❌ Upload failed:', errorDetails);
                throw new Error(errorDetails);
            }

            const data = await response.json();
            console.log('✅ Upload response:', data);

            if (data.success) {
                // Phase 1: Show summary immediately for responsive feel
                const summaryText = data.combined_summary || 'Multiple files processed successfully';
                this.showSummary(summaryText, null, this.selectedSummaryLevel); // No audio yet
                
                // Clear selected files
                this.selectedFiles = [];
                this.updateFileDisplay();
                const fileInput = document.getElementById('file-input');
                if (fileInput) fileInput.value = '';

                // Show Q&A section
                this.showQASection();
                
                // Refresh file shelf
                await this.loadUserDocuments();

                // Track successful multi-upload
                this.trackEvent('multi_file_upload', {
                    total_files: data.total_files,
                    successful_uploads: data.successful_uploads,
                    summary_level: this.selectedSummaryLevel
                });
                
                this.showStatus(`Successfully analyzed ${data.successful_uploads} document${data.successful_uploads > 1 ? 's' : ''}!`, 'success');
                
                // Phase 2: Generate audio in background (if there's text to convert)
                console.log('🎵 Checking audio generation conditions:');
                console.log('  - summaryText:', summaryText ? `"${summaryText.substring(0, 100)}..."` : 'null/undefined');
                console.log('  - summaryText length:', summaryText ? summaryText.length : 0);
                console.log('  - voice:', data.voice || this.selectedVoice);
                
                // Always try to generate audio if we have valid summary text
                if (summaryText && summaryText.trim().length > 10) { // Changed condition - just check for meaningful text
                    console.log('✅ Conditions met, calling generateAudioInBackground');
                    setTimeout(async () => {
                        try {
                            // Show audio loading indicator
                            const audioLoading = document.getElementById('audio-loading');
                            if (audioLoading) {
                                audioLoading.classList.remove('hidden');
                            }
                            
                            await this.generateAudioInBackground(summaryText, data.voice || this.selectedVoice);
                        } catch (audioError) {
                            console.error('❌ Audio generation failed with error:', audioError);
                            // Hide loading indicator on error
                            const audioLoading = document.getElementById('audio-loading');
                            if (audioLoading) {
                                audioLoading.classList.add('hidden');
                                audioLoading.style.display = 'none';
                                console.log('❌ Audio loading indicator hidden due to error');
                            }
                        }
                    }, 1000); // Add small delay to ensure UI is ready
                } else {
                    console.log('❌ Audio generation skipped - no meaningful text');
                    console.log('  - summaryText value:', JSON.stringify(summaryText));
                    console.log('  - summaryText type:', typeof summaryText);
                    console.log('  - summaryText length:', summaryText ? summaryText.length : 0);
                }
                
                return true; // Return true to indicate success

            } else {
                throw new Error(data.error || 'Analysis failed');
            }

        } catch (error) {
            console.error('❌ Multi-file upload error:', error);
            this.showStatus(`Analysis error: ${error.message}`, 'error');
            return false; // Return false to indicate failure
        }
    }

    async generateAudioInBackground(text, voice) {
        // Generate audio for text in the background and update UI when ready
        try {
            console.log('🎵 Generating audio in background...');
            
            // Update status to show audio is being generated
            const currentStatus = document.getElementById('status');
            const originalStatus = currentStatus ? currentStatus.textContent : '';
            this.showStatus('Generating audio...', 'loading');
            
            const response = await fetch('/api/generate-audio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, voice })
            });

            if (response.ok) {
                const audioData = await response.json();
                if (audioData.success && audioData.audio_url) {
                    // Update the summary section with audio
                    const summaryAudio = document.getElementById('summary-audio');
                    const audioLoading = document.getElementById('audio-loading');
                    
                    if (summaryAudio) {
                        summaryAudio.src = audioData.audio_url;
                        summaryAudio.style.display = 'block';
                        console.log('✅ Audio generated and added to summary');
                    }
                    
                    // Hide the audio loading indicator
                    if (audioLoading) {
                        audioLoading.classList.add('hidden');
                        audioLoading.style.display = 'none';
                        console.log('✅ Audio loading indicator hidden');
                    }
                }
            } else {
                console.warn('⚠️ Audio generation failed, continuing without audio');
                // Hide loading indicator on failure
                const audioLoading = document.getElementById('audio-loading');
                if (audioLoading) {
                    audioLoading.classList.add('hidden');
                    audioLoading.style.display = 'none';
                    console.log('⚠️ Audio loading indicator hidden due to generation failure');
                }
            }
            
            // Restore original status or clear loading status
            if (originalStatus && !originalStatus.includes('loading')) {
                this.showStatus(originalStatus, 'success');
            } else {
                // Hide status after a short delay if it was just the loading message
                setTimeout(() => {
                    if (currentStatus) currentStatus.classList.add('hidden');
                }, 2000);
            }
            
        } catch (error) {
            console.warn('⚠️ Background audio generation failed:', error.message);
            // Hide loading indicator on error
            const audioLoading = document.getElementById('audio-loading');
            if (audioLoading) {
                audioLoading.classList.add('hidden');
                audioLoading.style.display = 'none';
                console.log('❌ Audio loading indicator hidden due to background generation error');
            }
            // Don't show error to user since audio is optional
        }
    }

    displayMultiFileResults(data) {
        // Show the summary section
        const summarySection = document.getElementById('summary-section');
        const summaryContent = document.getElementById('summary-content');
        const summaryLevelIndicator = document.getElementById('summary-level-indicator');

        if (summarySection && summaryContent && summaryLevelIndicator) {
            summarySection.classList.remove('hidden');
            summaryLevelIndicator.textContent = this.selectedSummaryLevel.charAt(0).toUpperCase() + 
                                              this.selectedSummaryLevel.slice(1);

            // Display combined summary or individual results
            if (data.combined_summary) {
                summaryContent.textContent = data.combined_summary;
            } else {
                // Display individual results
                const resultsText = data.results
                    .filter(r => r.success)
                    .map(r => `📄 ${r.filename}:\n${r.summary}`)
                    .join('\n\n---\n\n');
                summaryContent.textContent = resultsText || 'Upload completed but no summaries generated.';
            }

            // Handle audio if available
            if (data.audio_url) {
                this.handleAudioResponse(data.audio_url);
            }

            // Show failed uploads if any
            const failedUploads = data.results.filter(r => !r.success);
            if (failedUploads.length > 0) {
                const errorMsg = `Some files failed to upload:\n${failedUploads.map(f => `• ${f.filename}: ${f.error}`).join('\n')}`;
                this.showStatus(errorMsg, 'error');
            }
        }

        // Enable Q&A section
        const qaSection = document.getElementById('qa-section');
        if (qaSection) {
            qaSection.classList.remove('hidden');
        }
    }

    // Copy summary to clipboard
    async copySummaryToClipboard() {
        const summaryText = document.getElementById('summary-text');
        if (!summaryText || !summaryText.textContent) {
            this.showStatus('No summary available to copy', 'error');
            return;
        }

        const textToCopy = summaryText.textContent;
        let copySuccess = false;

        try {
            // Try modern clipboard API first (requires HTTPS)
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(textToCopy);
                copySuccess = true;
            } else {
                // Fallback for HTTP environments
                const textArea = document.createElement('textarea');
                textArea.value = textToCopy;
                textArea.style.position = 'fixed';
                textArea.style.left = '-9999px';
                textArea.style.top = '-9999px';
                document.body.appendChild(textArea);
                
                textArea.focus();
                textArea.select();
                
                try {
                    copySuccess = document.execCommand('copy');
                } catch (fallbackErr) {
                    console.error('Fallback copy failed:', fallbackErr);
                }
                
                document.body.removeChild(textArea);
            }

            if (copySuccess) {
                this.showStatus('✅ Summary copied to clipboard!', 'success');
                
                // Track event for analytics
                this.trackEvent('summary_copied', {
                    content_length: textToCopy.length,
                    summary_level: this.selectedSummaryLevel
                });
                
                // Visual feedback on button
                const copyBtn = document.getElementById('copy-summary-btn');
                if (copyBtn) {
                    const originalText = copyBtn.innerHTML;
                    copyBtn.innerHTML = '✅ Copied!';
                    setTimeout(() => {
                        copyBtn.innerHTML = originalText;
                    }, 2000);
                }
            } else {
                throw new Error('Copy operation failed');
            }
        } catch (err) {
            console.error('Failed to copy to clipboard:', err);
            this.showStatus('❌ Failed to copy to clipboard. Please select and copy the text manually.', 'error');
        }
    }

    // Email summary
    emailSummary() {
        const summaryText = document.getElementById('summary-text');
        if (!summaryText || !summaryText.textContent) {
            this.showStatus('No summary available to email', 'error');
            return;
        }

        try {
            const subject = 'MyAIGist Summary: ';
            const body = summaryText.textContent;
            const mailtoLink = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
            
            // Open default email client
            window.location.href = mailtoLink;
            
            // Track event for analytics
            this.trackEvent('summary_emailed', {
                content_length: body.length,
                summary_level: this.selectedSummaryLevel
            });
            
            this.showStatus('✅ Opening email client...', 'success');
        } catch (err) {
            console.error('Failed to open email client:', err);
            this.showStatus('❌ Failed to open email client', 'error');
        }
    }

    // Unified Input System Methods
    showTextInputModal() {
        if (this.selectedInputs.length >= 5) {
            this.showStatus('❌ Maximum 5 inputs allowed', 'error');
            return;
        }

        // Create modal HTML
        const modal = document.createElement('div');
        modal.className = 'text-input-modal';
        modal.innerHTML = `
            <div class="text-input-modal-content">
                <h3>✍️ Add Text Entry</h3>
                <textarea 
                    id="modal-text-input" 
                    placeholder="Enter your text here for AI analysis..."
                    maxlength="10000"
                ></textarea>
                <div class="text-input-modal-actions">
                    <button class="text-input-modal-btn cancel">Cancel</button>
                    <button class="text-input-modal-btn add">Add Text</button>
                </div>
            </div>
        `;

        // Add to body
        document.body.appendChild(modal);

        // Focus textarea
        const textarea = modal.querySelector('#modal-text-input');
        setTimeout(() => textarea.focus(), 100);

        // Handle buttons
        const cancelBtn = modal.querySelector('.cancel');
        const addBtn = modal.querySelector('.add');

        cancelBtn.addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        addBtn.addEventListener('click', () => {
            const text = textarea.value.trim();
            if (!text) {
                this.showStatus('❌ Please enter some text', 'error');
                // Close modal after showing error
                setTimeout(() => {
                    if (document.body.contains(modal)) {
                        document.body.removeChild(modal);
                    }
                }, 2000);
                return;
            }
            if (text.length < 10) {
                this.showStatus('❌ Text must be at least 10 characters', 'error');
                // Close modal after showing error
                setTimeout(() => {
                    if (document.body.contains(modal)) {
                        document.body.removeChild(modal);
                    }
                }, 2000);
                return;
            }

            this.addTextInput(text);
            document.body.removeChild(modal);
        });

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }

    showUrlInputModal() {
        if (this.selectedInputs.length >= 5) {
            this.showStatus('❌ Maximum 5 inputs allowed', 'error');
            return;
        }

        // Create modal HTML
        const modal = document.createElement('div');
        modal.className = 'text-input-modal';
        modal.innerHTML = `
            <div class="text-input-modal-content">
                <h3>🔗 Add Website URL</h3>
                <input 
                    type="url" 
                    id="modal-url-input" 
                    placeholder="https://example.com"
                    style="width: 100%; padding: 12px; border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; background: rgba(255, 255, 255, 0.95); color: #333; font-size: 0.9rem; box-sizing: border-box;"
                />
                <p style="color: rgba(255, 255, 255, 0.8); font-size: 0.85rem; margin: 8px 0 0 0;">
                    Enter a valid website URL to extract and analyze its content
                </p>
                <div class="text-input-modal-actions">
                    <button class="text-input-modal-btn cancel">Cancel</button>
                    <button class="text-input-modal-btn add">Add URL</button>
                </div>
            </div>
        `;

        // Add to body
        document.body.appendChild(modal);

        // Focus input
        const urlInput = modal.querySelector('#modal-url-input');
        setTimeout(() => urlInput.focus(), 100);

        // Handle buttons
        const cancelBtn = modal.querySelector('.cancel');
        const addBtn = modal.querySelector('.add');

        cancelBtn.addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        addBtn.addEventListener('click', () => {
            const url = urlInput.value.trim();
            if (!url) {
                this.showStatus('❌ Please enter a URL', 'error');
                setTimeout(() => {
                    if (document.body.contains(modal)) {
                        document.body.removeChild(modal);
                    }
                }, 2000);
                return;
            }
            
            // Validate URL format
            if (!this.isValidUrl(url)) {
                this.showStatus('❌ Please enter a valid URL (e.g., https://example.com)', 'error');
                setTimeout(() => {
                    if (document.body.contains(modal)) {
                        document.body.removeChild(modal);
                    }
                }, 2000);
                return;
            }

            this.addUrlInput(url);
            document.body.removeChild(modal);
        });

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });

        // Handle Enter key
        urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                addBtn.click();
            }
        });
    }

    addTextInput(text) {
        // Track text input analytics
        this.trackFeatureUsage('text_input', 'added', {
            text_length: text.length,
            word_count: text.split(/\s+/).filter(word => word.length > 0).length,
            character_count: text.length,
            current_input_count: this.selectedInputs.length,
            text_complexity: text.length > 500 ? 'long' : text.length > 100 ? 'medium' : 'short'
        });

        const textInput = {
            id: `text_${Date.now()}`,
            type: 'text',
            content: text,
            title: `Text Entry ${this.selectedInputs.filter(i => i.type === 'text').length + 1}`,
            preview: text.substring(0, 100) + (text.length > 100 ? '...' : ''),
            size: text.length
        };

        this.selectedInputs.push(textInput);
        this.updateInputDisplay();
        this.showStatus('✅ Text entry added!', 'success');
    }

    isValidUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
        } catch (_) {
            return false;
        }
    }

    addUrlInput(url) {
        // Track URL input analytics
        this.trackFeatureUsage('url_input', 'added', {
            url_length: url.length,
            domain: this.getDomainFromUrl(url),
            url_type: url.includes('youtube.') ? 'video' : 
                     url.includes('wikipedia.') ? 'encyclopedia' :
                     url.includes('github.') ? 'repository' :
                     url.includes('stackoverflow.') ? 'qa_site' :
                     url.includes('reddit.') ? 'social' : 'general',
            is_https: url.startsWith('https://'),
            current_input_count: this.selectedInputs.length,
            has_path: new URL(url).pathname !== '/',
            has_query: new URL(url).search !== ''
        });

        const urlInput = {
            id: `url_${Date.now()}`,
            type: 'url',
            url: url,
            title: this.getDomainFromUrl(url),
            preview: `Website content from: ${url}`,
            size: url.length
        };

        this.selectedInputs.push(urlInput);
        this.updateInputDisplay();
        this.showStatus('✅ Website URL added!', 'success');
    }

    getDomainFromUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname.replace('www.', '');
        } catch (_) {
            return 'Website';
        }
    }

    handleFileSelection(files) {
        if (files.length === 0) return;

        const remainingSlots = 5 - this.selectedInputs.length;
        if (files.length > remainingSlots) {
            this.showStatus(`❌ Can only add ${remainingSlots} more item(s). Maximum 5 inputs allowed.`, 'error');
            this.trackError('file_selection_error', 'Maximum inputs exceeded', {
                attempted_files: files.length,
                remaining_slots: remainingSlots
            });
            return;
        }

        // Track file selection analytics
        const fileTypes = files.map(f => f.name.split('.').pop().toLowerCase()).filter(Boolean);
        const totalSize = files.reduce((sum, f) => sum + f.size, 0);
        
        this.trackFeatureUsage('file_upload', 'selected', {
            file_count: files.length,
            file_types: fileTypes,
            total_size_bytes: totalSize,
            avg_size_bytes: totalSize / files.length,
            largest_file_bytes: Math.max(...files.map(f => f.size)),
            current_input_count: this.selectedInputs.length
        });

        files.forEach(file => {
            const fileInput = {
                id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                type: 'file',
                file: file,
                title: file.name,
                preview: `${file.type || 'Unknown type'} • ${this.formatFileSize(file.size)}`,
                size: file.size
            };

            this.selectedInputs.push(fileInput);
        });

        this.updateInputDisplay();
        this.showStatus(`✅ Added ${files.length} file(s)!`, 'success');
    }

    handleMediaSelection(files) {
        if (files.length === 0) return;

        const remainingSlots = 5 - this.selectedInputs.length;
        if (files.length > remainingSlots) {
            this.showStatus(`❌ Can only add ${remainingSlots} more item(s). Maximum 5 inputs allowed.`, 'error');
            this.trackError('media_selection_error', 'Maximum inputs exceeded', {
                attempted_files: files.length,
                remaining_slots: remainingSlots
            });
            return;
        }

        // Track media selection analytics
        const fileTypes = files.map(f => f.name.split('.').pop().toLowerCase()).filter(Boolean);
        const totalSize = files.reduce((sum, f) => sum + f.size, 0);
        const mediaTypes = fileTypes.map(type => {
            const audioFormats = ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg', 'wma', 'mpga'];
            return audioFormats.includes(type) ? 'audio' : 'video';
        });
        
        this.trackFeatureUsage('media_upload', 'selected', {
            file_count: files.length,
            file_types: fileTypes,
            media_types: mediaTypes,
            audio_files: mediaTypes.filter(t => t === 'audio').length,
            video_files: mediaTypes.filter(t => t === 'video').length,
            total_size_bytes: totalSize,
            avg_size_mb: (totalSize / files.length) / (1024 * 1024),
            over_25mb_limit: files.some(f => f.size > 25 * 1024 * 1024),
            current_input_count: this.selectedInputs.length
        });

        // Define supported media formats
        const audioFormats = ['.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma', '.mpga'];
        const videoFormats = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v', '.3gp', '.mpeg', '.mpg'];
        const allMediaFormats = [...audioFormats, ...videoFormats];

        // Filter and validate media files
        const validMediaFiles = files.filter(file => {
            const extension = '.' + file.name.split('.').pop().toLowerCase();
            const isSupported = allMediaFormats.includes(extension);
            
            if (!isSupported) {
                this.showStatus(`❌ Unsupported media format: ${file.name}`, 'error');
                return false;
            }
            
            // Check file size (25MB limit for Whisper)
            if (file.size > 25 * 1024 * 1024) {
                this.showStatus(`❌ File too large: ${file.name} (max 25MB)`, 'error');
                return false;
            }
            
            return true;
        });

        if (validMediaFiles.length === 0) return;

        validMediaFiles.forEach(file => {
            const extension = '.' + file.name.split('.').pop().toLowerCase();
            const isVideo = videoFormats.includes(extension);
            
            const mediaInput = {
                id: `media_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                type: 'media',
                file: file,
                title: file.name,
                preview: `${isVideo ? '🎥 Video' : '🎵 Audio'} • ${this.formatFileSize(file.size)} • Will be transcribed`,
                size: file.size,
                mediaType: isVideo ? 'video' : 'audio'
            };

            this.selectedInputs.push(mediaInput);
        });

        this.updateInputDisplay();
        this.showStatus(`✅ Added ${validMediaFiles.length} media file(s) for transcription!`, 'success');
    }

    removeInput(inputId) {
        this.selectedInputs = this.selectedInputs.filter(input => input.id !== inputId);
        this.updateInputDisplay();
        this.showStatus('✅ Input removed', 'success');
    }

    updateInputDisplay() {
        const inputsList = document.getElementById('selected-inputs-list');
        const inputsContainer = document.getElementById('selected-inputs');
        const addTextBtn = document.getElementById('add-text-btn');
        const fileInputLabel = document.querySelector('.file-input-label');

        if (!inputsList) return;

        // Update button states
        const isMaxReached = this.selectedInputs.length >= 5;
        if (addTextBtn) {
            addTextBtn.disabled = isMaxReached;
            addTextBtn.title = isMaxReached ? 'Maximum 5 inputs reached' : 'Add text entry';
        }
        if (fileInputLabel) {
            if (isMaxReached) {
                fileInputLabel.style.opacity = '0.5';
                fileInputLabel.style.cursor = 'not-allowed';
                fileInputLabel.title = 'Maximum 5 inputs reached';
            } else {
                fileInputLabel.style.opacity = '1';
                fileInputLabel.style.cursor = 'pointer';
                fileInputLabel.title = 'Add document(s)';
            }
        }

        // Show/hide container and warning
        if (this.selectedInputs.length === 0) {
            inputsContainer.style.display = 'none';
            this.removeWarning();
        } else {
            inputsContainer.style.display = 'block';
            
            inputsList.innerHTML = this.selectedInputs.map(input => `
                <div class="input-item" data-id="${input.id}">
                    <div class="input-item-icon">
                        ${input.type === 'text' ? '📝' : 
                          input.type === 'url' ? '🔗' : 
                          input.type === 'media' ? (input.mediaType === 'video' ? '🎥' : '🎵') : 
                          '📄'}
                    </div>
                    <div class="input-item-content">
                        <div class="input-item-header">
                            <h4 class="input-item-title">${this.escapeHtml(input.title)}</h4>
                            <span class="input-item-type">${input.type.toUpperCase()}</span>
                        </div>
                        <p class="input-item-preview">${this.escapeHtml(input.preview)}</p>
                        ${input.type === 'text' ? 
                            `<div class="input-item-meta">${input.size} characters</div>` :
                            input.type === 'url' ?
                            `<div class="input-item-meta">Website • ${input.url}</div>` :
                            `<div class="input-item-meta">${this.formatFileSize(input.size)}</div>`
                        }
                    </div>
                    <button class="input-item-remove" onclick="window.myAIGist.removeInput('${input.id}')" title="Remove">×</button>
                </div>
            `).join('');

            // Show warning when approaching limit
            if (this.selectedInputs.length >= 4) {
                this.showWarning();
            } else {
                this.removeWarning();
            }
        }
    }

    showWarning() {
        const existingWarning = document.querySelector('.input-limit-warning');
        const inputsContainer = document.getElementById('selected-inputs');
        
        if (existingWarning) {
            // Update existing warning with current count
            existingWarning.textContent = `${5 - this.selectedInputs.length} input slot(s) remaining`;
            return;
        }

        const warning = document.createElement('div');
        warning.className = 'input-limit-warning';
        warning.textContent = `${5 - this.selectedInputs.length} input slot(s) remaining`;
        
        inputsContainer.appendChild(warning);
    }

    removeWarning() {
        const warning = document.querySelector('.input-limit-warning');
        if (warning) warning.remove();
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('📱 DOM loaded, initializing MyAIGist...');
    window.myAIGist = new MyAIGist();
});
