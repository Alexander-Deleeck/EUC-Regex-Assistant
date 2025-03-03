from typing import Dict, List, Tuple
from openai import AzureOpenAI
import streamlit as st
import regex  # Add this at the top of the file, alongside other imports
import docx
import io



def get_azure_client() -> AzureOpenAI:
    """Initialize Azure OpenAI client"""
    return AzureOpenAI(
        api_key=st.secrets["AZURE"]["AZURE_OPENAI_API_KEY"],
        api_version=st.secrets["AZURE"]["AZURE_OPENAI_API_VERSION"],
        azure_endpoint=st.secrets["AZURE"]["AZURE_OPENAI_ENDPOINT"]
    )
    

def unpack_example(examples: List[Tuple[str, str]]) -> str:
    return "\n".join([f"Example:{example[0]}\nDescription: {example[1]}\n\n" for example in examples])


def generate_base_prompt(description: str, examples: List[Tuple[str, str]], not_examples: List[Tuple[str, str]], 
                        example_sentence: str, prefix: str, suffix: str, case_sensitive: bool, 
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

EXAMPLE CONTEXT:
{example_sentence}

OPTIONS:
- Prefix: {prefix or 'None'}
- Suffix: {suffix or 'None'}
- Case-sensitive: {case_sensitive}
- Start of paragraph: {start_para}
- End of paragraph: {end_para}

Provide the find regex and replace pattern separated by '|||'. Use lookbehind/ahead for prefix/suffix if needed.
"""
    
    
def generate_answer(prompt: str, client: AzureOpenAI) -> str:
    response = client.chat.completions.create(
        model=st.secrets["AZURE"]["AZURE_OPENAI_DEPLOYMENT_NAME"],
        messages=[
            {"role": "system", "content": "You are a regex expert. Return find|||replace patterns."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content


def substitute_regex(find: str, replace: str, text: str) -> str:
    try:
        return regex.sub(find, replace, text)
    except:
        return "Invalid regex"

def substitute_regex_in_file(find: str, replace: str, content: str) -> str:
    return substitute_regex(find, replace, content)



def generate_explanation(base_prompt: str, answer: str, client: AzureOpenAI):# -> Dict[str, str]:
    """Generate answers for a subsection using LLM"""
    
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
    
    #print(explanation.choices[0].message.content)
    return explanation.choices[0].message.content



def test_regex(result_regex: str, test_text: str):
    """Test if the regex matches the text using the regex library for advanced pattern support"""
    try:
        # Use regex.finditer instead of re.finditer
        return list(regex.finditer(result_regex, test_text))
    except regex.error as e:
        #print(f"Regex error: {e}")  # For debugging
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
    if uploaded_file is None:
        return ""
    
    file_type = uploaded_file.type
    try:
        if file_type == "text/plain":
            return uploaded_file.getvalue().decode("utf-8")
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        else:
            return ""
    except Exception as e:
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