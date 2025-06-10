import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import os
import smtplib
import base64
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import cloudinary
import cloudinary.uploader
from config import OLLAMA_CONFIG, APP_CONFIG
import re
import validators
from supabase_client import SupabaseClient

# Ensure directories exist
os.makedirs(APP_CONFIG['data_dir'], exist_ok=True)

# Ollama client
def get_ai_response(prompt, system_msg=""):
    try:
        payload = {
            "model": OLLAMA_CONFIG['model'],
            "prompt": prompt,
            "system": system_msg,
            "stream": False,
            "options": {"temperature": 0.7, "max_tokens": 300}
        }
        response = requests.post(
            f"{OLLAMA_CONFIG['base_url']}/api/generate",
            json=payload,
            timeout=30
        )
        return response.json().get("response", "Sorry, I couldn't process that.")
    except Exception as e:
        return f"Connection error: {str(e)}. Make sure Ollama is running!"

# Data storage functions
def save_candidate(data):
    try:
        if os.path.exists(APP_CONFIG['candidates_file']):
            with open(APP_CONFIG['candidates_file'], 'r') as f:
                candidates = json.load(f)
        else:
            candidates = []
        
        data['timestamp'] = datetime.now().isoformat()
        data['has_video_responses'] = bool(data.get('video_responses'))
        candidates.append(data)
        
        with open(APP_CONFIG['candidates_file'], 'w') as f:
            json.dump(candidates, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False

# Validation functions
def is_valid_email(email):
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

# New validation function
def validate_loom_url(url):
    """Validate if URL is a valid Loom share link"""
    
    if not url:
        return False
        
    # Loom URL patterns
    # Use the validators library first for general URL validation
    if not validators.url(url):
        return False
        
    # Then check for specific Loom patterns
    loom_patterns = [
        r'https://www\.loom\.com/share/[a-zA-Z0-9]+',
        r'https://loom\.com/share/[a-zA-Z0-9]+',
        r'https://www\.loom\.com/embed/[a-zA-Z0-9]+',
        r'https://loom\.com/embed/[a-zA-Z0-9]+', # Added loom.com/embed pattern
    ]
    
    return any(re.match(pattern, url.strip()) for pattern in loom_patterns)

# Email notification function
def send_email_notification(candidate_email, candidate_name):
    print(f"Attempting to send email to {candidate_email}")
    try:
        print("Connecting to SMTP server...")
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        print("Starting TLS...")
        server.starttls() # Secure the connection
        print("Logging in...")
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        print("Login successful. Creating message...")
        
        message = MIMEMultipart()
        message["From"] = EMAIL_CONFIG['sender_email']
        message["To"] = candidate_email
        message["Subject"] = "Application Submitted - TalentScout"

        body = f"""
Dear {candidate_name},

Thank you for completing your application with TalentScout!

Your application has been successfully submitted and our team will review it shortly.

Next Steps:
- Our technical team will review your responses
- You will be notified within 2-3 business days
- If selected, we'll schedule a follow-up interview

Thank you for your interest in joining our team!

Best regards,
TalentScout Team
"""

        message.attach(MIMEText(body, "plain"))

        text = message.as_string()
        server.sendmail(EMAIL_CONFIG['sender_email'], candidate_email, text)
        print("Email sent successfully!")
        server.quit()

        print("SMTP connection closed.")
        return True
    except Exception as e:
        print(f"Error details: {e}") # Ensure error details are printed
        st.error(f"Email notification failed: {e}")
        return False

# Initialize Supabase client
if 'supabase_client' not in st.session_state:
    st.session_state.supabase_client = SupabaseClient()

def save_candidate_hybrid(data):
    """Save to both Supabase and JSON"""
    result = st.session_state.supabase_client.save_candidate(data)
    
    if result["success"]:
        if "fallback" in result:
            st.warning(f"⚠️ Saved locally (Supabase error: {result['error']})")
        else:
            st.success("✅ Data saved to cloud successfully!")
        return True
    else:
        st.error(f"❌ Error saving data: {result['error']}")
        return False

# Main Streamlit App
def main():
    st.set_page_config(
        page_title="TalentScout Hiring Assistant",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #2E86AB, #A23B72);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .question-container {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        border-left: 4px solid #2E86AB;
    }
    .recording-status {
        background: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .stTextInput > div > div > input {
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown(
        '<div class="main-header"><h1>🎯 TalentScout Hiring Assistant</h1><p>Complete Technical Assessment with Video Responses</p></div>',
        unsafe_allow_html=True
    )
    
    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 0
        st.session_state.candidate_data = {}
        st.session_state.questions_list = []
        st.session_state.email_sent = False
    
    # Conversation flow
    if st.session_state.step == 0:
        show_welcome()
    elif st.session_state.step == 1:
        collect_basic_info()
    elif st.session_state.step == 2:
        collect_tech_stack()
    elif st.session_state.step == 3:
        generate_questions()
    elif st.session_state.step == 4:
        show_completion()

def show_welcome():
    st.markdown("#### Welcome! 👋", unsafe_allow_html=True)
    st.write("I'm here to help TalentScout learn more about your technical background and skills.")
    st.write("This will take about 10-15 minutes. You'll need to:")
    st.write("- Share your technical background")
    st.write("- Answer technical questions")
    st.write("- Record video responses (screen + webcam)")
    
    if st.button("Yes, let's begin!", type="primary"):
        st.session_state.step = 1
        st.rerun()

def collect_basic_info():
    st.markdown("#### Basic Information 📝", unsafe_allow_html=True)
    
    with st.form("basic_info"):
        name = st.text_input("Full Name *")
        email = st.text_input("Email Address *")
        phone = st.text_input("Phone Number")
        experience = st.selectbox(
            "Years of Experience *",
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "10+"]
        )
        position = st.text_input("Desired Position *")
        location = st.text_input("Current Location")
        
        submitted = st.form_submit_button("Next Step")
        
        if submitted:
            errors = []
            if not name.strip():
                errors.append("Name is required")
            if not email.strip():
                errors.append("Email is required")
            elif not is_valid_email(email):
                errors.append("Please enter a valid email")
            if not position.strip():
                errors.append("Desired position is required")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.session_state.candidate_data.update({
                    'name': name.strip(),
                    'email': email.strip(),
                    'phone': phone.strip(),
                    'experience': experience,
                    'position': position.strip(),
                    'location': location.strip()
                })
                st.session_state.step = 2
                st.rerun()

def collect_tech_stack():
    st.write("#### Technical Skills 🛠️", unsafe_allow_html=True)
    st.write("Select all technologies you're proficient in:")

    with st.form("tech_stack"):
        # Programming Languages (Expanded)
        languages = st.multiselect(
            "Programming Languages",
            [
                "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C",
                "Go", "Rust", "PHP", "Ruby", "Swift", "Kotlin", "Scala",
                "R", "MATLAB", "Perl", "Haskell", "Lua", "Dart", "Elixir",
                "Clojure", "F#", "VB.NET", "COBOL", "Fortran", "Assembly", "Other"
            ]
        )

        # Frontend Frameworks & Libraries
        frontend = st.multiselect(
            "Frontend Frameworks & Libraries",
            [
                "React", "Angular", "Vue.js", "Svelte", "Next.js", "Nuxt.js",
                "Gatsby", "Ember.js", "Backbone.js", "jQuery", "Bootstrap",
                "Tailwind CSS", "Material-UI", "Ant Design", "Chakra UI",
                "Styled Components", "SASS/SCSS", "Less", "Other"
            ]
        )

        # Backend Frameworks
        backend = st.multiselect(
            "Backend Frameworks",
            [
                "Django", "Flask", "FastAPI", "Express.js", "Node.js", "Spring Boot",
                "Spring MVC", "Laravel", "CodeIgniter", "Ruby on Rails", "ASP.NET",
                ".NET Core", "Gin", "Echo", "Fiber", "Actix", "Rocket", "Other"
            ]
        )

        # Databases (Expanded)
        databases = st.multiselect(
            "Databases",
            [
                # Relational
                "MySQL", "PostgreSQL", "SQLite", "Oracle", "SQL Server", "MariaDB",
                # NoSQL Document
                "MongoDB", "CouchDB", "Amazon DocumentDB",
                # Key-Value
                "Redis", "Amazon DynamoDB", "Riak",
                # Column-Family
                "Cassandra", "HBase",
                # Graph
                "Neo4j", "Amazon Neptune", "ArangoDB",
                # Time Series
                "InfluxDB", "TimescaleDB",
                # Other
                "Elasticsearch", "Solr", "Other"
            ]
        )

        # Cloud Platforms
        cloud_platforms = st.multiselect(
            "Cloud Platforms",
            [
                "Amazon Web Services (AWS)", "Microsoft Azure", "Google Cloud Platform (GCP)",
                "IBM Cloud", "Oracle Cloud", "Alibaba Cloud", "DigitalOcean",
                "Linode", "Vultr", "Heroku", "Vercel", "Netlify", "Railway",
                "PlanetScale", "Supabase", "Firebase", "Other"
            ]
        )

        # DevOps & Tools
        devops_tools = st.multiselect(
            "DevOps & Development Tools",
            [
                # Version Control
                "Git", "GitHub", "GitLab", "Bitbucket", "SVN",
                # CI/CD
                "Jenkins", "GitHub Actions", "GitLab CI", "CircleCI", "Travis CI",
                "Azure Pipelines", "TeamCity",
                # Containerization
                "Docker", "Kubernetes", "Docker Compose", "Podman",
                # Infrastructure
                "Terraform", "Ansible", "Chef", "Puppet", "CloudFormation",
                # Monitoring
                "Prometheus", "Grafana", "New Relic", "Datadog", "Splunk",
                "Other"
            ]
        )

        # Mobile Development
        mobile = st.multiselect(
            "Mobile Development",
            [
                "React Native", "Flutter", "Xamarin", "Ionic", "Cordova/PhoneGap",
                "iOS (Swift/Objective-C)", "Android (Java/Kotlin)", "Unity",
                "Unreal Engine", "Other"
            ]
        )

        # Data Science & Analytics
        data_science = st.multiselect(
            "Data Science & Analytics",
            [
                "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch", "Keras",
                "Apache Spark", "Hadoop", "Jupyter", "R Studio", "Tableau",
                "Power BI", "Looker", "Apache Airflow", "Apache Kafka", "Other"
            ]
        )

        # Testing Frameworks
        testing = st.multiselect(
            "Testing Frameworks & Tools",
            [
                "Jest", "Mocha", "Chai", "Cypress", "Selenium", "Playwright",
                "Puppeteer", "JUnit", "TestNG", "PyTest", "Unittest", "RSpec",
                "PHPUnit", "Postman", "Insomnia", "Other"
            ]
        )

        # CMS & E-commerce
        cms_ecommerce = st.multiselect(
            "CMS & E-commerce Platforms",
            [
                "WordPress", "Drupal", "Joomla", "Shopify", "WooCommerce",
                "Magento", "PrestaShop", "Squarespace", "Wix", "Webflow", "Other"
            ]
        )

        # Other Specializations
        other_tech = st.multiselect(
            "Other Technologies & Specializations",
            [
                "Machine Learning", "Artificial Intelligence", "Blockchain",
                "Cryptocurrency", "IoT", "AR/VR", "Game Development",
                "Cybersecurity", "Network Administration", "System Administration",
                "Technical Writing", "UI/UX Design", "Product Management", "Other"
            ]
        )

        # Additional Skills Text Area
        additional_skills = st.text_area(
            "Additional Skills & Technologies",
            placeholder="Please specify any other technologies, certifications, or skills not listed above...",
            help="Include specific versions, certifications, or specialized tools you work with"
        )

        submitted = st.form_submit_button("Generate Interview Questions", type="primary")

        if submitted:
            # Collect all selected technologies (This might be too much for prompt, will summarize in generate_enhanced_questions)
            # Storing all selected for potential future use or detailed saving if needed.
            all_selected_list = []
            if languages: all_selected_list.extend(languages)
            if frontend: all_selected_list.extend(frontend)
            if backend: all_selected_list.extend(backend)
            if databases: all_selected_list.extend(databases)
            if cloud_platforms: all_selected_list.extend(cloud_platforms)
            if devops_tools: all_selected_list.extend(devops_tools)
            if mobile: all_selected_list.extend(mobile)
            if data_science: all_selected_list.extend(data_science)
            if testing: all_selected_list.extend(testing)
            if cms_ecommerce: all_selected_list.extend(cms_ecommerce)
            if other_tech: all_selected_list.extend(other_tech)

            if not all_selected_list and not additional_skills.strip():
                st.error("Please select at least one technology or add details in Additional Skills")
            else:
                st.session_state.candidate_data.update({
                    'programming_languages': languages,
                    'frontend_frameworks': frontend,
                    'backend_frameworks': backend,
                    'databases': databases,
                    'cloud_platforms': cloud_platforms,
                    'devops_tools': devops_tools,
                    'mobile_development': mobile,
                    'data_science': data_science,
                    'testing_frameworks': testing,
                    'cms_ecommerce': cms_ecommerce,
                    'other_technologies': other_tech,
                    'additional_skills': additional_skills.strip(),
                    'all_selected_tech_list': all_selected_list # Storing all selected in a list as well
                })
                st.session_state.step = 3
                st.rerun()

def generate_enhanced_questions():
    candidate = st.session_state.candidate_data
    experience_level = candidate.get('experience', 0) # Get experience safely
    
    # Determine experience category
    if experience_level in [0, 1, 2]:
        exp_category = "junior"
        exp_descriptor = "entry-level"
    elif experience_level in [3, 4, 5, 6]:
        exp_category = "mid-level"
        exp_descriptor = "intermediate"
    else:
        exp_category = "senior"
        exp_descriptor = "experienced"
    
    # Create comprehensive tech stack summary
    tech_summary = []
    if candidate.get('programming_languages'):
        tech_summary.append(f"Programming Languages: {', '.join(candidate['programming_languages'])}")
    if candidate.get('frontend_frameworks'):
        tech_summary.append(f"Frontend Frameworks: {', '.join(candidate['frontend_frameworks'])}")
    if candidate.get('backend_frameworks'):
        tech_summary.append(f"Backend Frameworks: {', '.join(candidate['backend_frameworks'])}")
    if candidate.get('databases'):
        tech_summary.append(f"Databases: {', '.join(candidate['databases'])}")
    if candidate.get('cloud_platforms'):
        tech_summary.append(f"Cloud Platforms: {', '.join(candidate['cloud_platforms'])}")
    if candidate.get('devops_tools'):
        tech_summary.append(f"DevOps & Development Tools: {', '.join(candidate['devops_tools'])}")
    if candidate.get('mobile_development'):
        tech_summary.append(f"Mobile Development: {', '.join(candidate['mobile_development'])}")
    if candidate.get('data_science'):
        tech_summary.append(f"Data Science & Analytics: {', '.join(candidate['data_science'])}")
    if candidate.get('testing_frameworks'):
        tech_summary.append(f"Testing Frameworks & Tools: {', '.join(candidate['testing_frameworks'])}")
    if candidate.get('cms_ecommerce'):
        tech_summary.append(f"CMS & E-commerce Platforms: {', '.join(candidate['cms_ecommerce'])}")
    if candidate.get('other_technologies'):
        tech_summary.append(f"Other Technologies & Specializations: {', '.join(candidate['other_technologies'])}")
    
    tech_stack_text = "; ".join(tech_summary) if tech_summary else "no specific technical skills mentioned"
    
    # Ensure position is available
    position = candidate.get('position', 'developer')

    prompt = f"""You are a senior technical interviewer conducting a video interview for a {exp_descriptor} {position} position.

Candidate Profile:
- Experience: {experience_level} years
- Technical Skills: {tech_stack_text}
- Position: {position}

Generate 4-5 realistic technical interview questions that:
1. Sound like actual interview questions a hiring manager would ask
2. Are appropriate for {exp_category} level experience
3. Focus on their declared technologies (if any)
4. **Include a mix of conceptual, system design, and practical coding challenges.**
5. Include helpful hints for video recording (NOT answer hints)

For each question, provide:
- The main interview question (numbered)
- 2 recording hints that help structure their video response
- Expected response time (1-3 minutes)

Format example:
**Question 1: [Actual interview question here]**
🎥 *Recording Hint 1: Start by explaining your approach or logic*
🎥 *Recording Hint 2: Walk through a code example or diagram if applicable*
📹 *Recommended response time: 2-3 minutes*

Make questions conversational and realistic - as if you're sitting across from them in an interview. Avoid asking if they have clarifying questions.
"""

    system_prompt = f"""You are an experienced technical interviewer who has conducted hundreds of interviews. Your questions should:
- Sound natural and conversational
- Test real-world application, not just theory
- Be appropriate for {exp_category} developers
- Help candidates showcase their experience
- Be clear and specific
- Focus on practical scenarios they might face in a {position} role.
- Ensure recording hints are non-technical guidance on structuring the video answer (e.g., explain thinking, walk through code/diagram).
- Do NOT include phrases like 'Do you have any clarifying questions?' or 'Feel free to ask questions'.
- **Include a variety of question types: theoretical, problem-solving, system design, and coding tasks.**
"""

    return get_ai_response(prompt, system_prompt)

def generate_questions():
    st.markdown("#### Technical Interview Questions 🎯", unsafe_allow_html=True)
    
    candidate = st.session_state.candidate_data
    
    # Generate questions if not already generated and stored
    if 'generated_questions' not in st.session_state:
        with st.spinner("Generating personalized interview questions..."):
            st.session_state.generated_questions = generate_enhanced_questions()
    
    # Display questions in the original format (single block)
    st.write("### 📹 Video Interview Questions")
    # Combine the intro message and Loom instructions in one block
    st.info(
        """
        Please record your answers using Loom and paste the share link below for each question.

        **How to record your video responses with Loom:**

        1.  **Install Loom:** If you don't have it, download and install the [Loom desktop app](https://www.loom.com/download) or the [Loom Chrome extension](https://chrome.google.com/webstore/detail/loom-for-chrome/liecbddmkavbmhnnpiaecnbeabiiekmc).
        2.  **Start Recording:** Open Loom and choose if you want to record your screen, webcam, or both. Make sure your microphone is selected.
        3.  **Record Your Answer:** When you're ready, click 'Start Recording' and answer the question displayed above.
        4.  **Finish and Copy Link:** Once you're done, click the stop button. Loom will automatically open a page with your video. Click 'Copy Link'.
        5.  **Paste Link:** Paste the copied share link into the input box corresponding to the question below.
        """
    )
    
    # Remove the separate Loom instructions and the duplicate question block display
    # st.markdown("**How to record your video responses with Loom:**") # Removed
    # st.markdown("") # Removed
    # st.markdown("1.  **Install Loom:** ...") # Removed
    # st.markdown("2.  **Start Recording:** ...") # Removed
    # st.markdown("3.  **Record Your Answer:** ...") # Removed
    # st.markdown("4.  **Finish and Copy Link:** ...") # Removed
    # st.markdown("5.  **Paste Link:** ...") # Removed
    # st.markdown("") # Removed
    st.markdown("--- ") # Keep the separator before the questions start
    # st.write(st.session_state.generated_questions) # Removed the duplicate display of the full text block
    # st.markdown("--- ") # Removed the separator after the duplicate text block

    # Loom video URL input (Separate section as before)
    # st.write("### 📎 Submit Your Video Responses") # Removed - not needed with per-question inputs

    # Initialize video_responses in session state if not exists
    if 'video_responses' not in st.session_state:
        st.session_state.video_responses = {}

    # Parse the generated questions to create input fields
    questions_text = st.session_state.generated_questions
    # Simple parsing assuming format like: **Question 1: ...**
    question_blocks = questions_text.split('**Question ')[1:] # Split into blocks per question
    num_questions = len(question_blocks)

    # Create form for video responses (using a form for grouped submission)
    with st.form("video_responses_form"):
        # st.write("Paste your Loom video links below, corresponding to each question above:") # Remove this introductory line
        
        for i in range(num_questions):
            question_num = i + 1
            # Get the full question block text
            full_question_block = "**Question " + question_blocks[i].strip()
            
            # --- Start: Parse and Display Question and Hints ---
            lines = full_question_block.split('\n')
            main_question = ""
            hints_list = []
            recommended_time = ""

            # Parse the main question, hints, and recommended time
            question_found = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue # Skip empty lines

                # Find the line that contains the main question title
                if line.startswith(f'**Question {question_num}:'):
                     # Extract text after the colon for the main question
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        main_question = parts[1].strip()
                        # Remove leading '**' if present
                        if main_question.startswith('**'):
                            main_question = main_question[2:].strip()
                        # Remove trailing '**' if present (AI might include it)
                        if main_question.endswith('**'):
                            main_question = main_question[:-2].strip()
                    question_found = True
                elif question_found:
                    # After finding the question, look for hints and recommended time
                    hint_text_match = re.match(r'🎥 \*([^\*]+?)\*', line)
                    time_match = re.match(r'📹 \*([^\*]+?)\*', line)

                    if hint_text_match:
                        hints_list.append(hint_text_match.group(1).strip())
                    elif time_match:
                         recommended_time = time_match.group(1).strip()

            # Display the question title clearly, separating number and actual question
            st.markdown(f"<h4>Question {question_num}:</h4>", unsafe_allow_html=True)
            # Display the main question with a larger font size
            st.markdown(f"<div style='font-size: 1.5rem; font-weight: bold;'>{main_question}</div>", unsafe_allow_html=True)

            # Display hints in a list with smaller font
            if hints_list or recommended_time:
                # Add some padding below the question for better spacing
                st.markdown("<div style='margin-top: 10px; font-size: small;'>", unsafe_allow_html=True)
                if hints_list:
                    st.markdown("**Hints:**")
                    for hint in hints_list:
                        st.markdown(f"- {hint}")
                if recommended_time:
                    st.markdown(f"**Recommended Time:** {recommended_time}")
                st.markdown("</div>", unsafe_allow_html=True)
            # --- End: Parse and Display Question and Hints ---

            # Retrieve existing value for pre-filling
            current_loom_link = st.session_state.video_responses.get(f"question_{question_num}", {}).get('loom_url', '')

            # Loom link input right after the question/hints (Q&A style)
            # Added a small top margin for spacing
            loom_link = st.text_input(
                "Paste your Loom video link here:", # Simplified label
                key=f"loom_q{question_num}", # Unique key for each input
                value=current_loom_link, # Pre-fill with existing value
                placeholder="https://www.loom.com/share/your-video-id",
                # help=f"Record your answer for Question {question_num} and paste the share link here" # Removed redundant help
                label_visibility="collapsed" # Hide the default label, using markdown above
            )
            
            # Add back the validation message display logic which might have been removed
            if loom_link:
                if validate_loom_url(loom_link):
                    st.success(f"✅ Valid Loom link for Question {question_num}")
                    # Store valid link with question text and timestamp - ensure we store the parsed question and hints here
                    # Storing the full block is okay, but let's ensure the parsed details are available if needed later
                    st.session_state.video_responses[f"question_{question_num}"] = {
                        "question": main_question, # Store just the main question text
                        "hints": hints_list, # Store parsed hints
                        "recommended_time": recommended_time, # Store parsed recommended time
                        "full_text": full_question_block, # Keep the full generated block as well for completeness
                        "loom_url": loom_link,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                     # Remove if invalid (in case user corrects it later)
                    if f"question_{question_num}" in st.session_state.video_responses:
                        del st.session_state.video_responses[f"question_{question_num}"]
                    st.error(f"❌ Invalid Loom URL format for Question {question_num}. Please enter a valid Loom share or embed link.")
            # If link is empty, ensure it's not stored and remove any previous validation message
            elif f"question_{question_num}" in st.session_state.video_responses:
                del st.session_state.video_responses[f"question_{question_num}"]
                # Also clear the validation message if it was previously shown
                # This is a bit tricky with Streamlit's reruns, but clearing the state entry helps.

            # Add a separator after each question block for clarity
            st.markdown("--- ")
       
        # Submit button for the form
        submitted = st.form_submit_button("Submit All Responses", type="primary")
        
        # Handle form submission validation and saving
        if submitted:
            # Check if the number of VALIDATED video responses matches the number of questions
            if len(st.session_state.video_responses) < num_questions:
                st.error("Please provide valid Loom video links for all questions before submitting.")
            else:
                # Prepare data for saving (now directly update session state first)
                st.session_state.candidate_data.update({
                    'video_responses': st.session_state.video_responses, # Add video responses to session state
                    'generated_questions_full_text': st.session_state.generated_questions # Add full question text to session state for display
                })

                # Remove the temporary 'generated_questions' if not needed in saved data (it's now in full_text)
                if 'generated_questions' in st.session_state.candidate_data:
                    del st.session_state.candidate_data['generated_questions']

                # Call the new hybrid save function
                if save_candidate_hybrid(st.session_state.candidate_data): # Save the updated session state data
                    # st.success("Application data saved!") # Message handled in save_candidate_hybrid
                    
                    # Move to the completion step
                    st.session_state.step = 4 
                    st.rerun()

    # [Keep existing "Start Over" button]
    st.write("--- ") # Add a separator
    if st.button("⬅️ Start Over"):
        st.session_state.clear()
        st.rerun()

def show_completion():
    st.markdown("#### 🎉 Application Submitted Successfully!", unsafe_allow_html=True)
    
    st.success("Your information and video responses have been successfully processed!") # Updated success message
    
    # Display submission summary
    st.write("**✅ What we received:**")
    st.write(f"- Personal information")
    st.write(f"- Technical skills assessment")
    
    # Display video responses if available (Revert to displaying list)
    # Read from st.session_state.candidate_data which was updated before saving and rerunning
    if 'video_responses' in st.session_state.candidate_data and st.session_state.candidate_data['video_responses']:
        st.write("**Your Video Responses:**")
        # Sort keys to display in order (question_1, question_2, etc.)
        sorted_video_keys = sorted(st.session_state.candidate_data['video_responses'].keys(), key=lambda x: int(x.split('_')[1]))
        for key in sorted_video_keys:
            response = st.session_state.candidate_data['video_responses'][key]
            with st.expander(f"Question {key.split('_')[1]}"):
                # Display the full generated question block if stored
                if 'generated_questions_full_text' in st.session_state.candidate_data:
                    # Find the relevant question block in the full text
                    question_block_match = re.search(r'(\*\*Question ' + key.split('_')[1] + r':.*?)(\*\*Question |\Z)', st.session_state.candidate_data['generated_questions_full_text'], re.DOTALL)
                    if question_block_match:
                        st.write(question_block_match.group(1).strip())
                    else:
                        # Fallback to just displaying the stored question text
                        st.write(f"**Q:** {response.get('question', f'Question {key.split('_')[1]}')}")
                else:
                    # Fallback if full text wasn't saved (from older data)
                    st.write(f"**Q:** {response.get('question', f'Question {key.split('_')[1]}')}")

                st.write(f"**Video:** [View Recording]({response['loom_url']})")
                st.write(f"**Submitted:** {datetime.fromisoformat(response['timestamp']).strftime('%Y-%m-%d %H:%M')}") # Format timestamp
    else:
        st.write("- No video responses provided.") # Should not happen if submission logic is correct

    st.write(f"- All data saved securely")

    # Ensure candidate_data is available (should be if reaching this step after saving)
    candidate_name = st.session_state.candidate_data.get('name', 'Candidate')
    st.write(f"Thank you **{candidate_name}** for completing the technical assessment.")
    
    st.write("**Next Steps:**")
    st.write("- Our team will review your information and video responses")
    st.write("- You'll hear back within 2-3 business days")
    st.write("- Technical interview may be scheduled based on this screening")
    
    # Auto-redirect option
    st.info("💡 You can close this window or start a new assessment below.")
    
    if st.button("🏠 Start New Assessment"): # Updated button text and icon
        # Clear session and restart
        st.session_state.clear()
        st.rerun()

if __name__ == "__main__":
    main() 