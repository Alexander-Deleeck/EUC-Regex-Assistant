from typing import Dict, List, Tuple
from openai import AzureOpenAI
import streamlit as st
import regex  # Add this at the top of the file, alongside other imports
import docx
import io
import re
from streamlit_extras.colored_header import colored_header

def app_header():
    with st.container():
        
        logo_col, title_col = st.columns([2, 20])
        logo_col.image(image='./logo/sparkle-orange-icon.png', width=60)
        with title_col:
            colored_header(label="REGEX-GENERATOR", color_name="blue-70", description=' ')
            
# Add to top of app.py
def check_auth():
    """Check if user is logged in, else show login form"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        
    if not st.session_state.logged_in:
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if (username == st.secrets.auth.username and 
                password == st.secrets.auth.password):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials")
        st.stop()

def get_azure_client() -> AzureOpenAI:
    """Initialize Azure OpenAI client"""
    print("Initializing Azure OpenAI client...")
    try:
        client = AzureOpenAI(
            api_key=st.secrets["AZURE"]["AZURE_OPENAI_API_KEY"],
            api_version=st.secrets["AZURE"]["AZURE_OPENAI_API_VERSION"],
            azure_endpoint=st.secrets["AZURE"]["AZURE_OPENAI_ENDPOINT"]
        )
        print("Azure OpenAI client initialized successfully")
        return client
    except Exception as e:
        print(f"Error initializing Azure OpenAI client: {str(e)}")
        raise
    

def unpack_example(examples: List[Tuple[str, str]]) -> str:
    return "\n".join([f"Example:{example[0]}\nDescription: {example[1]}\n\n" for example in examples])


def generate_base_prompt(description: str, examples: List[Tuple[str, str]], not_examples: List[Tuple[str, str]], 
                        prefix: str, suffix: str, case_sensitive: bool, 
                        start_para: bool, end_para: bool) -> str:
    def unpack(examples):
        return '\n'.join([f"Ex: {ex[0]}\nDesc: {ex[1]}" for ex in examples])
    
    return f"""
Create a regex find and replace pattern with these requirements:

DESCRIPTION:
{description}

MATCH EXAMPLES:
{unpack(examples)}

DO NOT MATCH:
{unpack(not_examples)}

OPTIONS:
- Prefix: {prefix or 'None'}
- Suffix: {suffix or 'None'}
- Case-sensitive: {case_sensitive}
- Start of paragraph: {start_para}
- End of paragraph: {end_para}

Provide the find regex and replace pattern separated by '|||'. Use lookbehind/ahead for prefix/suffix if needed.
Return EXACTLY the find and replace patterns separated by '|||' and do NOT include any other text or characters like `
"""
    
    
def generate_answer(prompt: str, client: AzureOpenAI) -> str:
    print(f"\nGenerating answer for prompt: {prompt[:100]}...")
    try:
        response = client.chat.completions.create(
            model=st.secrets["AZURE"]["AZURE_OPENAI_DEPLOYMENT_NAME"],
            messages=[
                {"role": "system", "content": "You are a regex expert. Return EXACTLY the find and replace patterns separated by '|||' and do NOT include any other text or characters like `"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        print(f"Response received: {response.choices[0].message.content}")
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating answer: {str(e)}")
        raise


def substitute_regex(find: str, replace: str, text: str) -> str:
    print(f"\nAttempting regex substitution with pattern: {find}")
    try:
        result = regex.sub(find, replace, text)
        print(f"Substitution successful. Sample result: {result[:100]}")
        return result
    except Exception as e:
        print(f"Error in regex substitution: {str(e)}")
        return "Invalid regex"

def substitute_regex_in_file(find: str, replace: str, content: str) -> str:
    return substitute_regex(find, replace, content)



def generate_explanation(base_prompt: str, answer: str, client: AzureOpenAI):# -> Dict[str, str]:
    """Generate answers for a subsection using LLM"""
    
    print("\nGenerating explanation...")
    try:
        explanation = client.chat.completions.create(
            model=st.secrets["AZURE"]["AZURE_OPENAI_DEPLOYMENT_NAME"],
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert in Regular Expressions. Here is my situation,\n{base_prompt}. The solution I got from you was:\n{answer}.",
                },
                {
                    "role": "user",
                    "content": "Showcase the solution and briefly explain the solution to me. Enclose any formulas in ```formula```.",
                },
            ],
            temperature=0.5,
            max_tokens=800,
            top_p=1
        )
        print(f"Explanation generated successfully: {explanation.choices[0].message.content[:100]}")
        return explanation.choices[0].message.content
    except Exception as e:
        print(f"Error generating explanation: {str(e)}")
        raise



def test_regex(result_regex: str, test_text: str):
    """Test if the regex matches the text using the regex library for advanced pattern support"""
    print(f"\nTesting regex pattern: {result_regex}")
    try:
        # Use regex.finditer instead of re.finditer
        matches = list(regex.finditer(result_regex, test_text))
        print(f"Found {len(matches)} matches")
        return matches
    except regex.error as e:
        #print(f"Regex error: {e}")  # For debugging
        print(f"Regex error: {e}")
        return []


def markdown_test_results(test_results: list) -> str:
    """Return a markdown string of the test results"""
    if not test_results:
        return "*No matches found or invalid regex pattern*"
    
    markdown_results = ""
    for idx, match in enumerate(test_results):
        markdown_results += f"""    **Match {idx+1}:**    {match.group()}
Start position: {match.start()}
End position: {match.end()}


"""
    return markdown_results

def read_file_content(uploaded_file) -> str:
    """Read content from uploaded .txt or .docx file"""
    print("\nReading file content...")
    if uploaded_file is None:
        print("No file uploaded")
        return ""
    
    file_type = uploaded_file.type
    print(f"File type: {file_type}")
    try:
        if file_type == "text/plain":
            content = uploaded_file.getvalue().decode("utf-8")
            print(f"Text file read successfully. Length: {len(content)}")
            return content
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            print(f"Word document read successfully. Length: {len(content)}")
            return content
        else:
            print("Unsupported file type")
            return ""
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        st.error(f"Error reading file: {str(e)}")
        return ""


def test_regex_on_file(regex_pattern: str, file_content: str) -> list:
    """Test regex pattern on file content and return all matches with context"""
    matches = test_regex(regex_pattern, file_content)
    
    # For each match, get surrounding context (50 chars before and after)
    detailed_matches = []
    for match in matches:
        start = max(0, match.start() - 50)
        end = min(len(file_content), match.end() + 50)
        context = file_content[start:end]
        
        # Add ... if we truncated the context
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(file_content) else ""
        
        detailed_matches.append({
            "match": match.group(),
            "start": match.start(),
            "end": match.end(),
            "context": f"{prefix}{context}{suffix}"
        })
    
    return detailed_matches

def generate_refinement_prompt(base_prompt: str, current_find: str, current_replace: str, feedback: str) -> List[Dict]:
    """Generate messages array for regex refinement"""
    return [
        {
            "role": "system",
            "content": f"""You are a regex refinement assistant. Help improve this regex based on user feedback.

Original Requirements:
{base_prompt}

Current Regex:
Find: {current_find}
Replace: {current_replace}

User Feedback:
{feedback}

Generate an improved regex. Return ONLY the new find and replace patterns separated by '|||'. No explanations or formatting."""
        },
        {"role": "user", "content": feedback}
    ]


def parse_refinement_response(response: str) -> Tuple[str, str]:
    """Parse LLM response for refined regex patterns"""
    pattern = re.compile(r'^(.*?)\|\|\|(.*)$', re.DOTALL)
    match = pattern.match(response.strip())
    
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return response.strip(), ''