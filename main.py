from flask import Flask, render_template, request, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
import uuid
import secrets
from datetime import datetime
import hashlib

# Load environment variables
load_dotenv()

# Import our agents with error handling
try:
    from agents.document_processor import DocumentProcessor
    from agents.summarizer import Summarizer
    from agents.qa_agent import QAAgent
    print("✅ Successfully imported all agent modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all agent modules exist in the 'agents' directory")

# Use dummy metrics service for local deployment (no CloudWatch)
class DummyMetrics:
    def track_content_processed(self, *args, **kwargs): pass
    def track_question_asked(self, *args, **kwargs): pass
    def track_media_transcription(self, *args, **kwargs): pass
    def track_voice_usage(self, *args, **kwargs): pass
    def track_batch_processing(self, *args, **kwargs): pass
    def track_embedding_operations(self, *args, **kwargs): pass
    def track_error(self, *args, **kwargs): pass
    def track_session_activity(self, *args, **kwargs): pass

metrics_service = DummyMetrics()
print("ℹ️  Metrics tracking disabled (local mode)")

# Create Flask app with explicit static folder configuration
app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static')

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

# Session configuration for better persistence
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 24 * 60 * 60  # 24 hours

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/audio', exist_ok=True)
os.makedirs('data', exist_ok=True)  # Ensure data directory for vector stores exists

# Check if we can write to the data directory (important for EFS)
try:
    test_file = 'data/test_write_permissions.tmp'
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    print("✅ Data directory is writable")
except Exception as e:
    print(f"❌ Data directory write test failed: {e}")
    print(f"📁 Data directory permissions: {oct(os.stat('data').st_mode)[-3:]}")
    print(f"📂 Current working directory: {os.getcwd()}")
    print(f"👤 Process user: {os.getuid()}")

# Initialize agents with proper error handling
doc_processor = None
summarizer = None
qa_agent = None

try:
    doc_processor = DocumentProcessor()
    print("✅ DocumentProcessor initialized")
except Exception as e:
    print(f"❌ Error initializing DocumentProcessor: {e}")

try:
    summarizer = Summarizer()
    print("✅ Summarizer initialized")
except Exception as e:
    print(f"❌ Error initializing Summarizer: {e}")

try:
    qa_agent = QAAgent()
    print("✅ QAAgent initialized")
except Exception as e:
    print(f"❌ Error initializing QAAgent: {e}")

# Check if all required agents are available (except qa_agent which is now session-based)
all_agents_ready = all([doc_processor, summarizer])
if all_agents_ready:
    print("✅ All core agents initialized successfully")
else:
    print("⚠️  Some core agents failed to initialize - some features may not work")

def create_text_document_title(session_qa, text):
    """Create a smart title for text documents"""
    user_id = get_user_identifier()
    
    # Count existing text documents for this user
    text_doc_count = 0
    if hasattr(session_qa.vector_store, 'metadata') and session_qa.vector_store.metadata:
        for metadata in session_qa.vector_store.metadata:
            if (metadata.get('user_id') == user_id and 
                metadata.get('doc_title', '').startswith('Text Entry')):
                text_doc_count += 1
    
    # Create title with preview
    text_preview = text.strip()[:50]
    if len(text.strip()) > 50:
        text_preview += "..."
    
    # Remove newlines and clean up preview
    text_preview = ' '.join(text_preview.split())
    
    title = f"Text Entry #{text_doc_count + 1}: {text_preview}"
    return title

def get_user_identifier():
    """Get user ID for local single-user deployment"""
    # Simplified for local single-user mode
    # Always returns the same ID since this is a local deployment
    user_id = "local_user"

    if 'user_id' not in session:
        session['user_id'] = user_id
        session.permanent = True
        print(f"👤 User ID: {user_id} (local mode)")

    return user_id

# Session-based QA agent management
def get_session_qa_agent():
    """Get or create a QA agent for the current session"""
    try:
        print(f"🔍 =========================")
        print(f"🔍 GET_SESSION_QA_AGENT DEBUG START")
        print(f"🔍 =========================")
        
        # Make session permanent for better persistence
        session.permanent = True
        
        if 'session_id' not in session:
            session['session_id'] = secrets.token_hex(8)
            session['created_at'] = str(datetime.now())
            print(f"🆔 Created new session: {session['session_id']}")
        else:
            print(f"🔄 Using existing session: {session['session_id']}")
        
        session_id = session['session_id']
        print(f"🔍 DEBUG: Session ID: {session_id}")
        print(f"🔍 DEBUG: Session created: {session.get('created_at', 'Unknown')}")
        print(f"🔍 DEBUG: Session keys: {list(session.keys())}")
        
        # Check data directory and permissions
        data_dir = "data"
        print(f"🔍 DEBUG: Checking data directory: {data_dir}")
        if not os.path.exists(data_dir):
            print(f"📁 Creating data directory: {data_dir}")
            os.makedirs(data_dir, exist_ok=True)
        
        # Test write permissions
        test_file = os.path.join(data_dir, f"test_write_{session_id}.tmp")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print(f"✅ Data directory write permissions: OK")
        except Exception as write_error:
            print(f"❌ Data directory write test failed: {write_error}")
        
        # Import here to avoid circular imports
        from agents.qa_agent import QAAgent
        
        # Get user identifier for multi-user isolation
        user_id = get_user_identifier()
        print(f"🔍 DEBUG: User ID: {user_id}")
        
        # Use shared multi-user vector store in production, session-based for local development
        flask_env = os.getenv('FLASK_ENV', 'development')
        print(f"🔍 DEBUG: Flask environment: {flask_env}")
        
        if flask_env == 'production':
            print(f"🏭 Production mode: Using shared multi-user vector store")
            qa = QAAgent(session_id="shared", user_id=user_id)  # Shared store with user isolation
        else:
            print(f"🏠 Development mode: Using session-based vector store")
            qa = QAAgent(session_id=session_id, user_id=user_id)  # Session-specific for development
            
        status = qa.get_status()
        print(f"✅ QA Agent ready for session: {session_id} (mode: {flask_env})")
        print(f"📊 QA Agent Status: {status}")
        
        # Store session info for debugging
        session['last_qa_access'] = str(datetime.now())
        
        return qa
    except Exception as e:
        print(f"❌ Error creating session QA agent: {e}")
        import traceback
        traceback.print_exc()
        return None

def cleanup_old_sessions(max_age_hours=24):
    """Clean up old session vector store files"""
    try:
        import glob
        import time
        
        data_dir = 'data'
        if not os.path.exists(data_dir):
            return
            
        pattern = os.path.join(data_dir, 'vector_store_*.pkl')
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for file_path in glob.glob(pattern):
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    print(f"🧹 Cleaned up old session file: {file_path}")
                except OSError as e:
                    print(f"⚠️  Failed to cleanup {file_path}: {e}")
                    
    except Exception as e:
        print(f"❌ Error in session cleanup: {e}")

# Clean up old sessions on startup
cleanup_old_sessions()

@app.route('/')
def index():
    """Serve the main application page"""
    print("📄 Serving index.html")
    return render_template('index.html')

@app.route('/about')
def about():
    """Serve the about page"""
    print("ℹ️  Serving about.html")
    return render_template('about.html')

@app.route('/terms')
def terms():
    """Serve the Terms of Service page"""
    print("📜 Serving terms.html")
    return render_template('terms.html')

# Favicon route
@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Static file route (explicit)
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files explicitly"""
    print(f"📁 Serving static file: {filename}")
    return send_from_directory('static', filename)

@app.route('/api/process-content', methods=['POST'])
def process_content():
    """Process uploaded content and return summary - TEXT AND DOCUMENTS ONLY"""
    print(f"🔄 Processing content request: {request.content_type}")
    start_time = datetime.now()
    
    # Check if summarizer is available
    if not summarizer:
        return jsonify({'error': 'Summarizer not available. Please check server logs.'}), 500
    
    try:
        summary_level = 'standard'  # Default level
        
        if request.is_json:
            # Handle JSON request (text input)
            data = request.get_json()
            content_type = data.get('type')
            summary_level = data.get('summary_level', 'standard')
            voice = data.get('voice', 'nova')
            
            print(f"📝 Processing text content with {summary_level} summary")
            
            if content_type == 'text':
                text = data.get('text')
                if not text:
                    return jsonify({'error': 'No text provided'}), 400
                
                print(f"📄 Text length: {len(text)} characters")
                
                # Process text with specified summary level
                summary = summarizer.summarize(text, detail_level=summary_level)
                
                # Generate audio if transcriber is available
                audio_url = None
                if transcriber:
                    try:
                        audio_url = transcriber.text_to_speech(summary, voice=voice)
                        print(f"🔊 Generated audio with {voice} voice: {audio_url}")
                    except Exception as e:
                        print(f"⚠️  Audio generation failed: {e}")
                
                # Store for QA with session-based agent - WITH ENHANCED DEBUGGING
                qa_success = False
                session_qa = get_session_qa_agent()
                if session_qa:
                    try:
                        print(f"🔍 CONTENT PROCESSING DEBUG:")
                        print(f"🆔 Session ID: {session.get('session_id')}")
                        print(f"📁 Vector store path: {session_qa.vector_store.persist_path}")
                        print(f"💾 Storing text for Q&A (length: {len(text)})")
                        
                        # Create a smart title for text documents
                        text_title = create_text_document_title(session_qa, text)
                        qa_success = session_qa.add_document(text, text_title)
                        print(f"✅ QA storage result: {qa_success}")
                        
                        # Vector store automatically saves after adding documents
                        print("✅ Document processed and vectors stored")
                        
                        # Verify storage worked
                        status = session_qa.get_status()
                        print(f"📊 QA Status after storage: {status}")
                        
                        # Verify file was actually saved
                        if os.path.exists(session_qa.vector_store.persist_path):
                            file_size = os.path.getsize(session_qa.vector_store.persist_path)
                            print(f"📦 Vector store file saved: {file_size} bytes")
                        else:
                            print(f"⚠️ Vector store file NOT found at: {session_qa.vector_store.persist_path}")
                        
                    except Exception as e:
                        print(f"❌ QA storage failed: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Track CloudWatch metrics for text processing
                processing_time = (datetime.now() - start_time).total_seconds()
                metrics_service.track_content_processed('text', summary_level, processing_time, True)
                
                return jsonify({
                    'summary': summary,
                    'audio_url': audio_url,
                    'summary_level': summary_level,
                    'qa_stored': qa_success,
                    'success': True
                })
        else:
            # Handle file upload - DOCUMENTS ONLY
            file = request.files.get('file')
            content_type = request.form.get('type')
            summary_level = request.form.get('summary_level', 'standard')
            voice = request.form.get('voice', 'nova')
            
            print(f"📄 Processing {content_type} file: {file.filename if file else 'None'} with {summary_level} summary")
            
            if not file:
                return jsonify({'error': 'No file uploaded'}), 400
            
            # Only allow document files - NO AUDIO
            if content_type != 'file':
                return jsonify({'error': 'Only document files are supported'}), 400
            
            # Check if document processor is available
            if not doc_processor:
                return jsonify({'error': 'Document processor not available. Please check server logs.'}), 500
            
            # Save uploaded file
            filename = secure_filename(file.filename)
            file_id = str(uuid.uuid4())
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
            file.save(file_path)
            
            try:
                # Extract text from document
                print(f"📖 Extracting text from: {filename}")
                text = doc_processor.extract_text(file_path)
                
                if not text:
                    return jsonify({'error': 'Could not extract text from the uploaded file'}), 400
                
                print(f"📄 Extracted text length: {len(text)} characters")
                
                # Generate summary with specified level
                summary = summarizer.summarize(text, detail_level=summary_level)
                
                # Generate audio if transcriber is available
                audio_url = None
                if transcriber:
                    try:
                        audio_url = transcriber.text_to_speech(summary, voice=voice)
                        print(f"🔊 Generated audio with {voice} voice: {audio_url}")
                    except Exception as e:
                        print(f"⚠️  Audio generation failed: {e}")
                
                # Store for QA with session-based agent - WITH ENHANCED DEBUGGING
                qa_success = False
                session_qa = get_session_qa_agent()
                if session_qa:
                    try:
                        print(f"🔍 FILE PROCESSING DEBUG:")
                        print(f"🆔 Session ID: {session.get('session_id')}")
                        print(f"📁 Vector store path: {session_qa.vector_store.persist_path}")
                        print(f"💾 Storing document '{filename}' for Q&A (length: {len(text)})")
                        
                        qa_success = session_qa.add_document(text, filename)
                        print(f"✅ QA storage result: {qa_success}")
                        
                        # Vector store automatically saves after adding documents
                        print("✅ Document processed and vectors stored")
                        
                        # Verify storage worked
                        status = session_qa.get_status()
                        print(f"📊 QA Status after storage: {status}")
                        
                        # Verify file was actually saved
                        if os.path.exists(session_qa.vector_store.persist_path):
                            file_size = os.path.getsize(session_qa.vector_store.persist_path)
                            print(f"📦 Vector store file saved: {file_size} bytes")
                        else:
                            print(f"⚠️ Vector store file NOT found at: {session_qa.vector_store.persist_path}")
                        
                    except Exception as e:
                        print(f"❌ QA storage failed: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Track CloudWatch metrics for file processing
                processing_time = (datetime.now() - start_time).total_seconds()
                metrics_service.track_content_processed('file', summary_level, processing_time, True)
                
                return jsonify({
                    'summary': summary,
                    'audio_url': audio_url,
                    'summary_level': summary_level,
                    'qa_stored': qa_success,
                    'success': True
                })
                
            finally:
                # Clean up uploaded file
                if os.path.exists(file_path):
                    os.remove(file_path)
    
    except Exception as e:
        print(f"❌ Error processing content: {e}")
        import traceback
        traceback.print_exc()
        
        # Track error in CloudWatch
        metrics_service.track_error('ContentProcessing', 'process_content', 'Error')
        
        return jsonify({'error': str(e)}), 500

@app.route('/api/ask-question', methods=['POST'])
def ask_question():
    """Handle Q&A requests"""
    print(f"🔍 =========================")
    print(f"🔍 ASK QUESTION DEBUG START")
    print(f"🔍 =========================")
    start_time = datetime.now()
    
    try:
        print(f"🔍 DEBUG: Request method: {request.method}")
        print(f"🔍 DEBUG: Request content type: {request.content_type}")
        
        # Get session-based QA agent
        print(f"🔍 DEBUG: Getting session QA agent...")
        session_qa = get_session_qa_agent()
        print(f"🔍 DEBUG: Session QA agent result: {session_qa is not None}")
        
        if not session_qa:
            print(f"❌ DEBUG: No session QA agent available!")
            return jsonify({'error': 'Q&A agent not available. Please check server logs.'}), 500
        
        print(f"✅ DEBUG: Session QA agent ready")
        
        # DEBUG: Check if QA agent has any documents
        print(f"🔍 DEBUG: QA agent has {len(session_qa.documents)} documents")
        if session_qa.documents:
            for i, doc in enumerate(session_qa.documents):
                print(f"  📄 Document {i+1}: {doc.get('title', 'No title')} ({doc.get('type', 'unknown type')})")
                print(f"    📝 Text length: {len(doc.get('text', ''))}")
                if doc.get('type') == 'url':
                    print(f"    🔗 URL: {doc.get('url', 'No URL')}")
        else:
            print(f"❌ DEBUG: No documents found in QA agent!")
            print(f"🔍 DEBUG: This explains why Q&A returns 'not specified'")
        
    except Exception as init_error:
        print(f"❌ DEBUG: Error in ask_question initialization: {init_error}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Initialization error: {str(init_error)}'}), 500
    
    try:
        data = request.get_json()
        question = data.get('question')
        voice = data.get('voice', 'nova')  # Default voice for Q&A audio
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        print(f"❓ Processing question: {question[:50]}...")
        print(f"🆔 Session ID: {session.get('session_id', 'None')}")
        print(f"📁 Vector store path: {session_qa.vector_store.persist_path}")
        
        # Debug QA agent status before answering
        status = session_qa.get_status()
        print(f"📊 QA Agent Status: {status}")
        
        # Check if vector store file exists on disk
        import os
        vector_file_exists = os.path.exists(session_qa.vector_store.persist_path)
        print(f"💾 Vector store file exists: {vector_file_exists}")
        if vector_file_exists:
            file_size = os.path.getsize(session_qa.vector_store.persist_path)
            print(f"📦 Vector store file size: {file_size} bytes")
        
        # Enhanced debugging - try to reload if no vectors in memory
        if not status.get('ready_for_questions', False):
            print("⚠️ No documents detected, attempting diagnosis...")
            
            # Try to reload the vector store
            try:
                print("🔄 Reloading vector store from disk...")
                session_qa.vector_store.load()
                status_after_reload = session_qa.get_status()
                print(f"📊 Status after reload: {status_after_reload}")
                
                if status_after_reload.get('ready_for_questions', False):
                    print("✅ Successfully reloaded vectors!")
                    status = status_after_reload
                else:
                    print("❌ Still no vectors after reload")
                    return jsonify({
                        'error': 'No documents available for Q&A. Please upload a document first.',
                        'debug_info': {
                            'session_id': session.get('session_id'),
                            'vector_store_path': str(session_qa.vector_store.persist_path),
                            'file_exists': vector_file_exists,
                            'file_size': file_size if vector_file_exists else 0,
                            'documents_in_memory': len(session_qa.documents),
                            'vectors_in_memory': len(session_qa.vector_store.vectors),
                            'status_before_reload': status,
                            'status_after_reload': status_after_reload
                        }
                    }), 400
                    
            except Exception as reload_error:
                print(f"❌ Error reloading vector store: {reload_error}")
                return jsonify({
                    'error': 'No documents available for Q&A. Please upload a document first.',
                    'reload_error': str(reload_error),
                    'debug_info': {
                        'session_id': session.get('session_id'),
                        'vector_store_path': str(session_qa.vector_store.persist_path),
                        'file_exists': vector_file_exists
                    }
                }), 400
        
        # Get answer from QA agent
        answer = session_qa.answer_question(question)
        
        # Generate audio for answer if transcriber is available
        audio_url = None
        if transcriber:
            try:
                audio_url = transcriber.text_to_speech(answer, voice=voice)
                print(f"🔊 Generated audio for answer with {voice} voice: {audio_url}")
            except Exception as e:
                print(f"⚠️  Audio generation failed: {e}")
        
        # Track CloudWatch metrics for Q&A
        response_time = (datetime.now() - start_time).total_seconds()
        has_context = len(session_qa.documents) > 0 if session_qa else False
        metrics_service.track_question_asked(len(question), response_time, has_context, True)
        
        return jsonify({
            'answer': answer,
            'audio_url': audio_url,
            'qa_status': status,
            'success': True
        })
        
    except Exception as e:
        print(f"❌ Error answering question: {e}")
        import traceback
        traceback.print_exc()
        
        # Track error in CloudWatch
        metrics_service.track_error('QuestionAnswering', 'ask_question', 'Error')
        
        return jsonify({'error': str(e)}), 500

@app.route('/api/transcribe-audio', methods=['POST'])
def transcribe_audio_question():
    """Transcribe uploaded audio for questions ONLY (live recording from Q&A)"""
    start_time = datetime.now()
    
    # Check if transcriber is available
    if not transcriber:
        return jsonify({'error': 'Transcriber not available. Please check server logs.'}), 500
    
    try:
        file = request.files.get('file')
        if not file or not file.filename:
            return jsonify({'error': 'No audio file uploaded'}), 400
        
        print(f"🎤 Transcribing question audio: {file.filename}")
        
        # Use the transcriber's built-in method for handling uploaded files
        transcribed_text = transcriber.transcribe(file)
        
        # Check if transcription was successful
        if transcribed_text.startswith("Error"):
            return jsonify({'error': transcribed_text}), 500
        
        if not transcribed_text or len(transcribed_text.strip()) < 2:
            return jsonify({'error': 'Could not transcribe audio. Please try speaking more clearly.'}), 400
        
        # Track CloudWatch metrics for voice transcription
        transcription_time = (datetime.now() - start_time).total_seconds()
        metrics_service.track_voice_usage('recording', transcription_time, True)
        
        return jsonify({
            'text': transcribed_text,
            'success': True
        })
                
    except Exception as e:
        print(f"❌ Error transcribing audio: {e}")
        
        # Track error in CloudWatch
        metrics_service.track_error('VoiceTranscription', 'transcribe_audio', 'Error')
        
        return jsonify({'error': f'Transcription failed: {str(e)}'}), 500

# Debug and health check routes
@app.route('/debug')
def debug():
    """Debug route to check file structure and agent status"""
    import glob
    
    files = {
        'templates': glob.glob('templates/*'),
        'static_css': glob.glob('static/css/*'),
        'static_js': glob.glob('static/js/*'),
        'static_images': glob.glob('static/images/*'),
        'agents': glob.glob('agents/*')
    }
    
    agent_status = {
        'document_processor': doc_processor is not None,
        'summarizer': summarizer is not None,
        'transcriber': transcriber is not None,
        'qa_agent_session_based': True,  # Always True since we create on-demand
        'all_agents_ready': all_agents_ready
    }
    
    env_status = {
        'openai_api_key_set': bool(os.getenv('OPENAI_API_KEY')),
        'upload_folder_exists': os.path.exists(app.config['UPLOAD_FOLDER']),
        'static_audio_exists': os.path.exists('static/audio')
    }
    
    # QA Agent specific debugging
    qa_status = {}
    if qa_agent:
        try:
            qa_status = session_qa.get_status()
        except Exception as e:
            qa_status = {'error': str(e)}
    
    return jsonify({
        'files': files,
        'agents': agent_status,
        'environment': env_status,
        'qa_status': qa_status,
        'available_summary_levels': summarizer.get_available_levels() if summarizer else None
    })

@app.route('/api/qa-debug', methods=['GET'])
def qa_debug():
    """Specific debugging endpoint for Q&A functionality"""
    session_qa = get_session_qa_agent()
    if not session_qa:
        return jsonify({'error': 'QA agent not initialized'}), 500
    
    try:
        status = session_qa.get_status()
        
        # Check file system
        vector_file_exists = os.path.exists(session_qa.vector_store.persist_path)
        file_size = os.path.getsize(session_qa.vector_store.persist_path) if vector_file_exists else 0
        
        return jsonify({
            'session_info': {
                'session_id': session.get('session_id'),
                'created_at': session.get('created_at'),
                'last_qa_access': session.get('last_qa_access'),
                'session_keys': list(session.keys())
            },
            'qa_agent_status': status,
            'ready_for_questions': status.get('ready_for_questions', False),
            'documents_loaded': status.get('documents_count', 0),
            'chunks_available': status.get('chunks_count', 0),
            'vector_store_info': {
                'path': str(session_qa.vector_store.persist_path),
                'file_exists': vector_file_exists,
                'file_size': file_size,
                'vectors_in_memory': len(session_qa.vector_store.vectors),
                'documents_in_memory': len(session_qa.documents)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-documents', methods=['GET'])
def get_user_documents():
    """Get list of documents for current user"""
    try:
        session_qa = get_session_qa_agent()
        if not session_qa:
            return jsonify({'error': 'QA agent not initialized'}), 500
        
        user_id = get_user_identifier()
        
        # Get user's documents from vector store metadata
        user_docs = {}
        if hasattr(session_qa.vector_store, 'metadata') and session_qa.vector_store.metadata:
            for metadata in session_qa.vector_store.metadata:
                if metadata.get('user_id') == user_id:
                    doc_id = metadata.get('doc_id')
                    if doc_id and doc_id not in user_docs:
                        user_docs[doc_id] = {
                            'doc_id': doc_id,
                            'title': metadata.get('doc_title', 'Untitled'),
                            'upload_time': metadata.get('upload_time'),
                            'chunk_count': 0
                        }
                    if doc_id in user_docs:
                        user_docs[doc_id]['chunk_count'] += 1
        
        documents = list(user_docs.values())
        # Sort by upload time (most recent first)
        documents.sort(key=lambda x: x.get('upload_time', ''), reverse=True)
        
        return jsonify({
            'documents': documents,
            'total_count': len(documents),
            'user_id': user_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-document', methods=['DELETE'])
def delete_document():
    """Delete a specific document for current user"""
    try:
        data = request.get_json()
        doc_id = data.get('doc_id')
        
        if not doc_id:
            return jsonify({'error': 'doc_id is required'}), 400
        
        session_qa = get_session_qa_agent()
        if not session_qa:
            return jsonify({'error': 'QA agent not initialized'}), 500
        
        user_id = get_user_identifier()
        
        # Load vector store to ensure we have latest data
        if not hasattr(session_qa.vector_store, 'vectors') or not session_qa.vector_store.vectors:
            session_qa.vector_store.load()
        
        # Check if document belongs to current user and exists
        doc_exists = False
        chunk_count = 0
        if hasattr(session_qa.vector_store, 'metadata'):
            for metadata in session_qa.vector_store.metadata:
                if (metadata.get('user_id') == user_id and 
                    metadata.get('doc_id') == doc_id):
                    doc_exists = True
                    chunk_count += 1
        
        if not doc_exists:
            return jsonify({'error': 'Document not found or access denied'}), 404
        
        # Remove document using existing method
        session_qa._remove_document_by_id(doc_id)
        session_qa.vector_store.save()
        
        print(f"🗑️ Deleted document {doc_id} for user {user_id} ({chunk_count} chunks removed)")
        
        return jsonify({
            'success': True,
            'message': f'Document deleted successfully',
            'doc_id': doc_id,
            'chunks_removed': chunk_count
        })
        
    except Exception as e:
        print(f"❌ Error deleting document: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-multiple-files', methods=['POST'])
def upload_multiple_files():
    """Process multiple files and URLs with optimized batch processing"""
    start_time = datetime.now()
    
    try:
        # Get files, media files, and URLs
        files = request.files.getlist('files') if 'files' in request.files else []
        media_files = request.files.getlist('media_files') if 'media_files' in request.files else []
        urls = request.form.getlist('urls') if 'urls' in request.form else []
        
        # Remove empty entries
        files = [f for f in files if f.filename != '']
        media_files = [f for f in media_files if f.filename != '']
        urls = [u for u in urls if u.strip()]
        
        total_inputs = len(files) + len(media_files) + len(urls)
        
        if total_inputs == 0:
            return jsonify({'error': 'No files or URLs provided'}), 400
        
        # Check input count limit
        if total_inputs > 5:
            return jsonify({'error': 'Maximum 5 inputs allowed per upload'}), 400
        
        # Get optional parameters
        summary_level = request.form.get('summary_level', 'standard')
        voice = request.form.get('voice', 'nova')
        
        session_qa = get_session_qa_agent()
        user_id = get_user_identifier()
        
        # Phase 1: Extract and validate all inputs (files, media files, and URLs)
        print(f"📄 Phase 1: Processing {len(files)} files, {len(media_files)} media files, and {len(urls)} URLs...")
        input_data = []
        
        # Process files
        for file in files:
            if file.filename == '':
                continue
                
            filename = secure_filename(file.filename)
            
            # Check file type
            allowed_extensions = {'.pdf', '.docx', '.txt'}
            file_ext = os.path.splitext(filename.lower())[1]
            if file_ext not in allowed_extensions:
                input_data.append({
                    'type': 'file',
                    'filename': filename,
                    'success': False,
                    'error': 'File type not allowed. Supported: PDF, DOCX, TXT'
                })
                continue
            
            try:
                # Save and extract text
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}_{filename}")
                file.save(file_path)
                text = doc_processor.extract_text(file_path)
                os.remove(file_path)
                
                if not text or len(text.strip()) < 10:
                    input_data.append({
                        'type': 'file',
                        'filename': filename,
                        'success': False,
                        'error': 'Could not extract text from file'
                    })
                    continue
                
                input_data.append({
                    'type': 'file',
                    'filename': filename,
                    'text': text,
                    'success': True
                })
                
            except Exception as e:
                input_data.append({
                    'type': 'file',
                    'filename': filename,
                    'success': False,
                    'error': str(e)
                })
        
        # Process media files (audio/video)
        for media_file in media_files:
            if media_file.filename == '':
                continue
                
            filename = secure_filename(media_file.filename)
            
            # Check if it's a supported media format
            if not transcriber.is_media_file(filename):
                input_data.append({
                    'type': 'media',
                    'filename': filename,
                    'success': False,
                    'error': 'Media type not supported. Supported: Audio (MP3, WAV, M4A, etc.) and Video (MP4, AVI, MOV, etc.)'
                })
                continue
                
            # Check file size (25MB limit for Whisper)
            if hasattr(media_file, 'content_length') and media_file.content_length:
                file_size = media_file.content_length
            else:
                # Fallback: save temporarily to check size
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4()}_{filename}")
                media_file.save(temp_path)
                file_size = os.path.getsize(temp_path)
                os.remove(temp_path)
                media_file.seek(0)  # Reset file pointer
                
            if file_size > 25 * 1024 * 1024:  # 25MB
                input_data.append({
                    'type': 'media',
                    'filename': filename,
                    'success': False,
                    'error': 'Media file too large. Maximum size is 25MB for transcription.'
                })
                continue
            
            try:
                print(f"🎬 Transcribing media file: {filename}")
                
                # Transcribe the media file
                transcribed_text = transcriber.transcribe(media_file)
                
                if not transcribed_text or len(transcribed_text.strip()) < 10:
                    input_data.append({
                        'type': 'media',
                        'filename': filename,
                        'success': False,
                        'error': 'Could not transcribe media file or no speech detected'
                    })
                    continue
                
                # Determine if it's audio or video for better labeling
                file_ext = os.path.splitext(filename.lower())[1]
                video_formats = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v', '.3gp', '.mpeg', '.mpg']
                media_type = 'video' if file_ext in video_formats else 'audio'
                
                input_data.append({
                    'type': 'media',
                    'filename': filename,
                    'media_type': media_type,
                    'text': transcribed_text,
                    'success': True
                })
                
                print(f"✅ Successfully transcribed {media_type}: {filename} ({len(transcribed_text)} characters)")
                
            except Exception as e:
                input_data.append({
                    'type': 'media',
                    'filename': filename,
                    'success': False,
                    'error': f'Error transcribing media: {str(e)}'
                })
        
        # URL processing disabled for local-only deployment
        if urls:
            print("⚠️  URL processing is disabled in local mode")
            for url in urls:
                input_data.append({
                    'type': 'url',
                    'url': url,
                    'title': url,
                    'success': False,
                    'error': 'URL processing is disabled in local mode'
                })
        
        # Filter successful extractions
        valid_inputs = [input_item for input_item in input_data if input_item.get('success', False)]
        if not valid_inputs:
            return jsonify({
                'success': False,
                'results': input_data,
                'successful_uploads': 0,
                'total_inputs': len(input_data),
                'error': 'No inputs could be processed'
            })
        
        file_count = len([i for i in valid_inputs if i['type'] == 'file'])
        media_count = len([i for i in valid_inputs if i['type'] == 'media']) 
        url_count = len([i for i in valid_inputs if i['type'] == 'url'])
        print(f"✅ Successfully extracted text from {len(valid_inputs)} inputs ({file_count} files, {media_count} media files, {url_count} URLs)")
        
        # Phase 2: Generate individual summaries only for single input or as fallback
        if len(valid_inputs) == 1:
            print("📋 Phase 2: Generating summary for single input...")
            input_entry = valid_inputs[0]
            try:
                summary = summarizer.summarize(input_entry['text'], detail_level=summary_level)
                input_entry['summary'] = summary
            except Exception as e:
                input_name = input_entry.get('filename', input_entry.get('title', input_entry.get('url', 'Unknown')))
                print(f"⚠️ Summary generation failed for {input_name}: {e}")
                input_entry['summary'] = f"Summary generation failed: {str(e)}"
        else:
            print(f"📋 Phase 2: Skipping individual summaries for multi-input upload (will generate unified summary)")
            # For multi-input, we'll generate individual summaries only if unified summary fails
            for input_entry in valid_inputs:
                input_entry['summary'] = None  # Will be generated later if needed
        
        # Phase 3: Optimized batch document storage
        print("🔄 Phase 3: Batch storing documents for Q&A...")
        successful_uploads = 0
        
        if session_qa:
            # Load existing vector store once
            if not hasattr(session_qa.vector_store, 'vectors') or not session_qa.vector_store.vectors:
                session_qa.vector_store.load()
            
            # Clean up user documents once
            session_qa._cleanup_user_documents()
            
            # Collect all chunks from all documents for batch embedding
            all_chunks = []
            chunk_metadata = []
            
            for input_entry in valid_inputs:
                try:
                    # Clean and chunk text
                    cleaned_text = session_qa._clean_text(input_entry['text'])
                    chunks = session_qa._chunk_text(cleaned_text)
                    
                    if chunks:
                        doc_id = str(uuid.uuid4())
                        upload_time = datetime.now().isoformat()
                        
                        # Determine title based on input type
                        if input_entry['type'] == 'file':
                            title = input_entry['filename']
                        elif input_entry['type'] == 'url':
                            title = input_entry['title']
                        elif input_entry['type'] == 'media':
                            title = input_entry['filename']
                        else:
                            title = 'Unknown'
                        
                        # Add document to session
                        document = {
                            'doc_id': doc_id,
                            'user_id': user_id,
                            'text': cleaned_text,
                            'title': title,
                            'type': input_entry['type'],
                            'chunks': chunks,
                            'upload_time': upload_time
                        }
                        
                        # Add type-specific metadata
                        if input_entry['type'] == 'url':
                            document['url'] = input_entry['url']
                        
                        session_qa.documents.append(document)
                        
                        # Collect chunks for batch processing
                        for chunk_index, chunk in enumerate(chunks):
                            all_chunks.append(chunk)
                            chunk_metadata.append({
                                'user_id': user_id,
                                'doc_id': doc_id,
                                'chunk_index': chunk_index,
                                'title': title,
                                'doc_title': title,
                                'type': input_entry['type'],
                                'upload_time': upload_time,
                                'text': chunk[:100] + '...' if len(chunk) > 100 else chunk
                            })
                        
                        input_entry['qa_stored'] = True
                        input_entry['doc_id'] = doc_id
                        successful_uploads += 1
                    else:
                        input_entry['qa_stored'] = False
                        
                except Exception as e:
                    input_name = input_entry.get('filename', input_entry.get('title', input_entry.get('url', 'Unknown')))
                    print(f"❌ Error processing {input_name}: {e}")
                    input_entry['qa_stored'] = False
            
            # Batch create embeddings for all chunks at once
            if all_chunks:
                print(f"🚀 Creating embeddings for {len(all_chunks)} chunks in batch...")
                embeddings = session_qa.vector_store.embedder.create_embeddings_batch(all_chunks)
                
                # Add vectors to store with metadata
                for i, (embedding, metadata) in enumerate(zip(embeddings, chunk_metadata)):
                    if embedding:
                        vector = __import__('numpy').array(embedding, dtype=__import__('numpy').float32)
                        vector_id = f"vec_{len(session_qa.vector_store.vectors)}"
                        metadata_with_id = {'id': vector_id, 'text': all_chunks[i], **metadata}
                        
                        session_qa.vector_store.vectors.append(vector)
                        session_qa.vector_store.metadata.append(metadata_with_id)
                
                # Set dimension on first embedding
                if session_qa.vector_store.dimension is None and embeddings:
                    for emb in embeddings:
                        if emb:
                            session_qa.vector_store.dimension = len(emb)
                            break
                
                # Save vector store once
                session_qa.vector_store.save()
                print(f"✅ Batch processing complete: {len(all_chunks)} chunks processed")
        
        # Update results for all inputs
        results = []
        for input_entry in input_data:
            if input_entry.get('success', False):
                result = {
                    'success': True,
                    'type': input_entry['type'],
                    'summary': input_entry.get('summary', 'Summary not available'),
                    'text_length': len(input_entry.get('text', '')),
                    'qa_stored': input_entry.get('qa_stored', False)
                }
                
                # Add type-specific fields
                if input_entry['type'] == 'file':
                    result['filename'] = input_entry['filename']
                elif input_entry['type'] == 'url':
                    result['url'] = input_entry['url']
                    result['title'] = input_entry['title']
                elif input_entry['type'] == 'media':
                    result['filename'] = input_entry['filename']
                    result['media_type'] = input_entry.get('media_type', 'unknown')
                
                results.append(result)
            else:
                error_result = {
                    'success': False,
                    'type': input_entry['type'],
                    'error': input_entry.get('error', 'Unknown error')
                }
                
                # Add type-specific fields for errors
                if input_entry['type'] == 'file':
                    error_result['filename'] = input_entry['filename']
                elif input_entry['type'] == 'url':
                    error_result['url'] = input_entry.get('url', '')
                elif input_entry['type'] == 'media':
                    error_result['filename'] = input_entry.get('filename', '')
                
                results.append(error_result)
        
        # Generate unified summary from all source texts (not individual summaries)
        combined_summary = None
        if successful_uploads > 1:
            # Collect all source texts for unified summarization
            source_texts = []
            successful_inputs = []
            
            for input_entry in valid_inputs:
                if input_entry.get('qa_stored', False):
                    source_texts.append(input_entry['text'])
                    if input_entry['type'] == 'file':
                        successful_inputs.append(input_entry['filename'])
                    elif input_entry['type'] == 'url':
                        successful_inputs.append(input_entry['title'])
                    elif input_entry['type'] == 'media':
                        successful_inputs.append(input_entry['filename'])
            
            if source_texts:
                # Create a unified document from all sources
                input_types = []
                file_count = len([i for i in valid_inputs if i['type'] == 'file' and i.get('qa_stored', False)])
                media_count = len([i for i in valid_inputs if i['type'] == 'media' and i.get('qa_stored', False)])
                url_count = len([i for i in valid_inputs if i['type'] == 'url' and i.get('qa_stored', False)])
                
                if file_count > 0:
                    input_types.append(f"{file_count} files")
                if media_count > 0:
                    input_types.append(f"{media_count} media files")
                if url_count > 0:
                    input_types.append(f"{url_count} URLs")
                input_types_str = " and ".join(input_types)
                
                unified_text = f"Combined analysis of {len(successful_inputs)} inputs ({input_types_str}): {', '.join(successful_inputs)}\n\n"
                
                # Add each input with a clear separator and title
                for i, (input_name, text) in enumerate(zip(successful_inputs, source_texts), 1):
                    unified_text += f"=== Input {i}: {input_name} ===\n\n{text}\n\n"
                
                print(f"🔄 Generating unified summary from {len(source_texts)} source inputs")
                try:
                    # Generate a single unified summary from all combined texts
                    combined_summary = summarizer.summarize(unified_text, detail_level=summary_level)
                except Exception as e:
                    print(f"⚠️ Unified summary generation failed: {e}")
                    print(f"🔄 Fallback: Generating individual summaries...")
                    
                    # Generate individual summaries as fallback
                    individual_summaries = []
                    for input_entry in valid_inputs:
                        if input_entry.get('qa_stored', False):
                            if input_entry['type'] == 'file':
                                input_name = input_entry['filename']
                            elif input_entry['type'] == 'url':
                                input_name = input_entry['title']
                            elif input_entry['type'] == 'media':
                                input_name = input_entry['filename']
                            else:
                                input_name = 'Unknown'
                            try:
                                summary = summarizer.summarize(input_entry['text'], detail_level=summary_level)
                                individual_summaries.append(f"**{input_name}**: {summary}")
                            except Exception as summary_error:
                                print(f"⚠️ Individual summary failed for {input_name}: {summary_error}")
                                individual_summaries.append(f"**{input_name}**: Summary generation failed")
                    
                    if individual_summaries:
                        combined_text = "\n\n".join(individual_summaries)
                        combined_summary = f"Analysis of {successful_uploads} inputs:\n\n" + combined_text
        elif successful_uploads == 1:
            # Single file - use its individual summary
            for result in results:
                if result['success'] and 'summary' in result:
                    combined_summary = result['summary']
                    break
        
        # Return response immediately with summary, audio will be generated separately
        # Track CloudWatch metrics for batch processing
        processing_time = (datetime.now() - start_time).total_seconds()
        content_types = [item['type'] for item in input_data]
        batch_size = len(input_data)
        metrics_service.track_batch_processing(batch_size, processing_time, content_types, successful_uploads)
        
        return jsonify({
            'success': successful_uploads > 0,
            'results': results,
            'successful_uploads': successful_uploads,
            'total_inputs': len(input_data),
            'total_files': len([f for f in input_data if f.get('type') == 'file']),
            'total_media': len([f for f in input_data if f.get('type') == 'media']),
            'total_urls': len([f for f in input_data if f.get('type') == 'url']),
            'combined_summary': combined_summary,
            'audio_url': None,  # Will be generated separately
            'user_id': user_id,
            'voice': voice  # Include voice for audio generation
        })
        
    except Exception as e:
        print(f"❌ Error in multi-file upload: {e}")
        import traceback
        traceback.print_exc()
        
        # Track error in CloudWatch
        metrics_service.track_error('BatchProcessing', 'upload_multiple_files', 'Error')
        
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio():
    """Generate audio for text content (used for progressive UI updates)"""
    start_time = datetime.now()
    
    try:
        if not transcriber:
            return jsonify({'error': 'Text-to-speech not available'}), 500
        
        data = request.get_json()
        text = data.get('text')
        voice = data.get('voice', 'nova')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        print(f"🔊 Generating audio for text ({len(text)} chars) with voice: {voice}")
        
        try:
            audio_url = transcriber.text_to_speech(text, voice=voice)
            
            # Track CloudWatch metrics for TTS
            tts_time = (datetime.now() - start_time).total_seconds()
            metrics_service.track_voice_usage('tts', tts_time, True)
            
            return jsonify({
                'success': True,
                'audio_url': audio_url
            })
        except Exception as tts_error:
            print(f"⚠️ TTS generation failed: {tts_error}")
            
            # Track TTS error in CloudWatch
            metrics_service.track_error('TextToSpeech', 'generate_audio', 'Error')
            
            return jsonify({
                'success': False,
                'error': f'Audio generation failed: {str(tts_error)}'
            }), 500
            
    except Exception as e:
        print(f"❌ Error in audio generation: {e}")
        
        # Track general error in CloudWatch
        metrics_service.track_error('TextToSpeech', 'generate_audio', 'Error')
        
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-question', methods=['POST'])
def test_question():
    """Test endpoint for Q&A debugging"""
    session_qa = get_session_qa_agent()
    if not session_qa:
        return jsonify({'error': 'QA agent not initialized'}), 500
    
    try:
        # Test with a simple question
        test_answer = session_qa.answer_question("What is this document about?")
        status = session_qa.get_status()
        
        return jsonify({
            'test_answer': test_answer,
            'qa_status': status,
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/full-test', methods=['POST'])
def full_test():
    """Comprehensive test of the entire Q&A pipeline"""
    try:
        test_text = "This is a test document about artificial intelligence and machine learning. AI systems can process natural language and help with various tasks. Machine learning algorithms learn from data to make predictions."
        
        results = {
            'step1_summarizer': False,
            'step2_qa_storage': False,
            'step3_qa_retrieval': False,
            'step4_qa_answer': False,
            'errors': []
        }
        
        # Step 1: Test summarizer
        if summarizer:
            try:
                summary = summarizer.summarize(test_text, detail_level='quick')
                results['step1_summarizer'] = True
                results['summary'] = summary[:100] + "..."
            except Exception as e:
                results['errors'].append(f"Summarizer error: {e}")
        
        # Step 2: Test QA storage
        if qa_agent:
            try:
                stored = session_qa.add_document(test_text, "Test Document")
                results['step2_qa_storage'] = stored
                results['qa_status_after_storage'] = session_qa.get_status()
            except Exception as e:
                results['errors'].append(f"QA storage error: {e}")
        
        # Step 3: Test QA retrieval
        if qa_agent:
            try:
                context = session_qa._get_relevant_context("What is this about?")
                results['step3_qa_retrieval'] = len(context) > 0
                results['context_length'] = len(context)
            except Exception as e:
                results['errors'].append(f"QA retrieval error: {e}")
        
        # Step 4: Test full Q&A
        if qa_agent:
            try:
                answer = session_qa.answer_question("What is this document about?")
                results['step4_qa_answer'] = not answer.startswith("Error") and not answer.startswith("No documents")
                results['test_answer'] = answer[:200] + "..."
            except Exception as e:
                results['errors'].append(f"QA answer error: {e}")
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/clear-documents', methods=['POST'])
def clear_documents():
    """Clear all stored documents from Q&A agent"""
    session_qa = get_session_qa_agent()
    if not session_qa:
        return jsonify({'error': 'QA agent not available'}), 500
    
    try:
        session_qa.clear_documents()
        return jsonify({
            'success': True,
            'message': 'All documents cleared',
            'qa_status': session_qa.get_status()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rebuild-vectors', methods=['POST'])
def rebuild_vectors():
    """Force rebuild QA agent vectors"""
    session_qa = get_session_qa_agent()
    if not session_qa:
        return jsonify({'error': 'QA agent not available'}), 500
    
    try:
        print("ℹ️ Checking vector store status...")
        
        # No need to rebuild vectors - using new vector store with automatic persistence
        print("ℹ️ Vector store uses automatic persistence - no manual rebuild needed")
        status = session_qa.get_status()
        
        print(f"✅ Vector store status: {status}")
        
        return jsonify({
            'success': True,
            'message': 'Vector store uses automatic persistence - no rebuild needed',
            'qa_status': status
        })
    except Exception as e:
        print(f"❌ Error rebuilding vectors: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup-audio', methods=['POST'])
def cleanup_audio():
    """Clean up old audio files"""
    if not transcriber:
        return jsonify({'error': 'Transcriber not available'}), 500
    
    try:
        transcriber.cleanup_old_files()
        return jsonify({'success': True, 'message': 'Audio cleanup completed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transcriber-debug', methods=['GET'])
def transcriber_debug():
    """Debug endpoint for transcriber functionality"""
    if not transcriber:
        return jsonify({'error': 'Transcriber not initialized'}), 500
    
    try:
        return jsonify({
            'transcriber_ready': True,
            'supported_formats': transcriber.get_supported_formats(),
            'available_voices': transcriber.get_available_voices(),
            'audio_directory_exists': transcriber.audio_dir.exists(),
            'audio_files_count': len(list(transcriber.audio_dir.glob('*.mp3')))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup-sessions', methods=['POST'])
def cleanup_sessions():
    """Clean up old session files"""
    try:
        cleanup_old_sessions()
        return jsonify({'success': True, 'message': 'Session cleanup completed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy' if all_agents_ready else 'degraded',
        'agents_ready': all_agents_ready,
        'openai_configured': bool(os.getenv('OPENAI_API_KEY')),
        'session_based_qa': True
    })

if __name__ == '__main__':
    print("🚀 Starting MyAIGist server...")
    print("📁 Static folder:", app.static_folder)
    print("🌐 Visit: http://localhost:8000")
    print("🔧 Debug info: http://localhost:8000/debug")
    print("💚 Health check: http://localhost:8000/health")
    print("📋 Summary levels: Quick, Standard (default), Detailed")
    print("📄 Supported content: Text input, PDF/DOCX/TXT documents")
    print("🎤 Voice features: Live recording for Q&A questions only")
    print(f"🤖 OpenAI API configured: {bool(os.getenv('OPENAI_API_KEY'))}")
    print(f"🔧 All agents ready: {all_agents_ready}")
    
    app.run(debug=True, host='0.0.0.0', port=8000)