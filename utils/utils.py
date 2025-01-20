from pathlib import Path
from typing import Dict, List, Tuple
from openai import AzureOpenAI
import re
import streamlit as st
import regex  # Add this at the top of the file, alongside other imports



def get_azure_client() -> AzureOpenAI:
    """Initialize Azure OpenAI client"""
    return AzureOpenAI(
        api_key=st.secrets["AZURE"]["AZURE_OPENAI_API_KEY"],
        api_version=st.secrets["AZURE"]["AZURE_OPENAI_API_VERSION"],
        azure_endpoint=st.secrets["AZURE"]["AZURE_OPENAI_ENDPOINT"]
    )
    

def unpack_example(examples: List[Tuple[str, str]]) -> str:
    return "\n".join([f"Example:{example[0]}\nDescription: {example[1]}\n\n" for example in examples])


def generate_base_prompt(description: str, examples: str, not_examples: str, example_sentence: str) -> str:
    base_prompt = f"""Can you please help me generate a regular expression for my use-case? 
I will provide you with:
- a description of the pattern I want to match (in <description> tags), 
- some examples of the pattern I want to match (in <match_examples> tags),
- some examples of the pattern I don't want to match (in <not_match_examples> tags),
- and an example sentence that contains both the pattern I want to match and the pattern I don't want to match (in <example_sentence> tags).

Description:
<description>
{description}
</description>

Examples:
<match_examples>
{unpack_example(examples)}
</match_examples>

Not Examples:
<not_match_examples>
{unpack_example(not_examples)}
</not_match_examples>

Example Sentence:
<example_sentence>
{example_sentence}
</example_sentence>

"""
    return base_prompt
    
    
def generate_answer(base_prompt: str, client: AzureOpenAI):# -> Dict[str, str]:
    """Generate answers for a subsection using LLM"""
    
    response = client.chat.completions.create(
        model=st.secrets["AZURE"]["AZURE_OPENAI_DEPLOYMENT_NAME"],
        messages=[
                {"role": "system",
                "content": "You are an expert in Regular Expressions. Your only job is to guide me in solving my problem using Regular Expressions. Please provide me with the exact Regular Expression I need for my problem. print nothing but the Regular Expression."},
                {"role": "user", "content": base_prompt}
            ],
        temperature=0.5,
        max_tokens=256,
        top_p=1
    )
    
    return response.choices[0].message.content


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